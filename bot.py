# PART 1 - bot.py (Lines 1-500)

import asyncio
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
import config
import database
from lulustream import LuluStreamClient
import re
from urllib.parse import urlparse

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize LuluStream client
lulu_client = LuluStreamClient()  # ✅ CORRECT

# Global worker control
worker_running = False
worker_task = None
scheduler_running = False
scheduler_task = None

# ==================== HELPER FUNCTIONS ====================

def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return user_id in config.ADMIN_IDS

def format_size(size_bytes):
    """Format bytes to human readable size"""
    if not size_bytes:
        return "Unknown"
    
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"

def extract_video_url(text: str) -> str:
    """Extract video URL from message text"""
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    urls = re.findall(url_pattern, text)
    return urls[0] if urls else None

async def download_file_from_url(url: str, file_path: str) -> bool:
    """Download file from URL"""
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    with open(file_path, 'wb') as f:
                        while True:
                            chunk = await response.content.read(1024 * 1024)  # 1MB chunks
                            if not chunk:
                                break
                            f.write(chunk)
                    return True
                else:
                    logger.error(f"Failed to download file: {response.status}")
                    return False
    except Exception as e:
        logger.error(f"Download error: {e}")
        return False

# ==================== COMMAND HANDLERS ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message"""
    user = update.effective_user
    
    welcome_text = f"""
👋 Welcome {user.first_name}!

🎬 **LuluStream Auto Upload Bot**

I can automatically upload videos to LuluStream and post them to your channel.

📝 **Commands:**
/help - Show all commands
/stats - Show queue statistics
/add_url - Add video URL to queue
/add_file - Upload and add file to queue

👨‍💼 **Admin Commands:**
/start_worker - Start upload worker
/stop_worker - Stop upload worker
/start_scheduler - Start auto-posting
/stop_scheduler - Stop auto-posting
/post_now - Post one video immediately
/clear_failed - Clear failed uploads
/queue - Show upload queue

Developed with ❤️
"""
    
    await update.message.reply_text(welcome_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help message"""
    help_text = """
📚 **Available Commands:**

**User Commands:**
/start - Start the bot
/help - Show this help message
/stats - Show queue statistics
/add_url <url> - Add video URL to queue
/add_file - Upload video file directly

**Admin Commands:**
/start_worker - Start background upload worker
/stop_worker - Stop upload worker
/start_scheduler - Start automatic posting
/stop_scheduler - Stop automatic posting
/post_now - Post one video immediately
/queue - Show current upload queue
/clear_failed - Clear all failed uploads

**How It Works:**
1. Send video URL or file
2. Bot adds to upload queue
3. Worker uploads to LuluStream
4. Scheduler posts to main channel

**Support:** Contact admin if you face any issues.
"""
    
    await update.message.reply_text(help_text)

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show queue statistics"""
    try:
        stats_data = await database.get_queue_stats()
        
        stats_text = f"""
📊 **Queue Statistics**

📦 Total: {stats_data['total']}
⏳ Pending: {stats_data['pending']}
⬆️ Uploading: {stats_data['uploading']}
✅ Uploaded: {stats_data['uploaded']}
📤 Posted: {stats_data['posted']}
❌ Failed: {stats_data['failed']}

🤖 Worker: {'🟢 Running' if worker_running else '🔴 Stopped'}
⏰ Scheduler: {'🟢 Running' if scheduler_running else '🔴 Stopped'}
"""
        
        await update.message.reply_text(stats_text)
    except Exception as e:
        await update.message.reply_text(f"❌ Error getting stats: {str(e)}")

async def add_url_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add video URL to queue"""
    if not context.args:
        await update.message.reply_text("❌ Please provide a video URL\n\nUsage: /add_url <url>")
        return
    
    url = context.args[0]
    
    # Validate URL
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            await update.message.reply_text("❌ Invalid URL format")
            return
    except:
        await update.message.reply_text("❌ Invalid URL")
        return
    
    try:
        # Extract filename from URL
        filename = url.split('/')[-1] or f"video_{datetime.now().timestamp()}.mp4"
        
        # Add to queue
        queue_id = await database.add_to_queue(
            message_id=update.message.message_id,
            file_name=filename,
            file_url=url,
            title=filename
        )
        
        if queue_id:
            await update.message.reply_text(
                f"✅ Added to queue!\n\n"
                f"📝 File: {filename}\n"
                f"🔗 URL: {url}\n"
                f"🆔 Queue ID: {queue_id}\n\n"
                f"Use /start_worker to begin uploading"
            )
        else:
            await update.message.reply_text("❌ Failed to add to queue")
    
    except Exception as e:
        logger.error(f"Error adding URL: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def handle_video_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle video file uploads"""
    try:
        video = update.message.video or update.message.document
        
        if not video:
            return
        
        # Add to queue
        queue_id = await database.add_to_queue(
            message_id=update.message.message_id,
            file_name=video.file_name or f"video_{datetime.now().timestamp()}.mp4",
            file_id=video.file_id,
            file_size=video.file_size,
            title=video.file_name or "Untitled Video"
        )
        
        if queue_id:
            await update.message.reply_text(
                f"✅ Video added to queue!\n\n"
                f"📝 File: {video.file_name}\n"
                f"💾 Size: {format_size(video.file_size)}\n"
                f"🆔 Queue ID: {queue_id}\n\n"
                f"Use /start_worker to begin uploading"
            )
        else:
            await update.message.reply_text("❌ Failed to add video to queue")
    
    except Exception as e:
        logger.error(f"Error handling video: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

# ==================== WORKER FUNCTIONS ====================

async def upload_worker():
    """Background worker to upload videos to LuluStream"""
    global worker_running
    
    logger.info("[WORKER] Started")
    
    while worker_running:
        try:
            # Get pending uploads
            pending = await database.get_pending_uploads(limit=1)
            
            if not pending:
                logger.info("[WORKER] No pending uploads, waiting...")
                await asyncio.sleep(10)
                continue
            
            video = pending[0]
            queue_id = str(video['_id'])
            
            logger.info(f"[WORKER] Processing: {video['file_name']}")
            
            # Update status to uploading
            await database.update_upload_status(queue_id, "uploading")
            
            try:
                # Download file if URL provided
                if video.get('file_url'):
                    temp_file = f"temp_{queue_id}.mp4"
                    logger.info(f"[WORKER] Downloading from URL: {video['file_url']}")
                    
                    success = await download_file_from_url(video['file_url'], temp_file)
                    if not success:
                        raise Exception("Failed to download file")
                    
                    file_path = temp_file
                
                # Download from Telegram if file_id provided
                elif video.get('file_id'):
                    # This requires bot instance, will be handled in main
                    logger.error("[WORKER] Telegram file download not implemented yet")
                    raise Exception("Telegram file download not supported in worker")
                
                else:
                    raise Exception("No file URL or file ID provided")
                
                # Upload to LuluStream
                logger.info(f"[WORKER] Uploading to LuluStream...")
                result = lulu_client.upload_file(file_path, video['file_name'])
                
                if result and result.get('status') == 200:
                    result_data = result.get('result', {})
                    filecode = result_data.get('filecode')
                    url = result_data.get('url')
                    
                    if filecode and url:
                        logger.info(f"[WORKER] Upload successful! Filecode: {filecode}")
                        
                        # Get file info from LuluStream to get original title and thumbnail
                        file_info = lulu_client.get_file_info(filecode)
                        
                        original_title = None
                        thumbnail_url = None
                        
                        if file_info and file_info.get('status') == 200:
                            result_data = file_info.get('result', {})
                            if isinstance(result_data, list) and len(result_data) > 0:
                                result_data = result_data[0]
                            
                            original_title = result_data.get('file_title') or result_data.get('title')
                            thumbnail_url = result_data.get('player_img') or result_data.get('thumbnail')  # ✅ FIXED LINE
                            
                            logger.info(f"[WORKER] Original title: {original_title}")
                            logger.info(f"[WORKER] Thumbnail: {thumbnail_url}")
                        
                        # Update status to uploaded
                        await database.update_upload_status(
                            queue_id,
                            "uploaded",
                            lulustream_file_code=filecode,
                            lulustream_url=url,
                            original_title=original_title,
                            thumbnail_url=thumbnail_url
                        )
                        
                        # Clean up temp file
                        if video.get('file_url'):
                            import os
                            try:
                                os.remove(file_path)
                            except:
                                pass
                    else:
                        raise Exception("No filecode or URL in response")
                else:
                    error_msg = result.get('msg', 'Unknown error') if result else 'No response'
                    raise Exception(f"Upload failed: {error_msg}")
            
            except Exception as e:
                logger.error(f"[WORKER] Upload failed: {e}")
                
                # Increment retry count
                retry_count = await database.increment_retry_count(queue_id)
                
                if retry_count >= config.MAX_RETRIES:
                    await database.update_upload_status(
                        queue_id,
                        "failed",
                        error_message=str(e)
                    )
                    logger.error(f"[WORKER] Max retries reached, marked as failed")
                else:
                    await database.update_upload_status(
                        queue_id,
                        "pending",
                        error_message=str(e)
                    )
                    logger.info(f"[WORKER] Retry {retry_count}/{config.MAX_RETRIES}")
        
        except Exception as e:
            logger.error(f"[WORKER] Error: {e}")
            await asyncio.sleep(5)
    
    logger.info("[WORKER] Stopped")

# PART 2 - bot.py (Lines 401 onwards)

async def post_scheduler():
    """Background scheduler to post videos to main channel"""
    global scheduler_running
    
    logger.info("[SCHEDULER] Started")
    
    while scheduler_running:
        try:
            # Get uploaded but not posted videos
            ready_to_post = await database.get_uploaded_not_posted(limit=1)
            
            if not ready_to_post:
                logger.info("[SCHEDULER] No videos ready to post, waiting...")
                await asyncio.sleep(60)  # Check every minute
                continue
            
            video = ready_to_post[0]
            queue_id = str(video['_id'])
            
            logger.info(f"[SCHEDULER] Posting: {video['file_name']}")
            
            try:
                # Post to main channel
                success = await post_to_main_channel(video)
                
                if success:
                    await database.update_upload_status(queue_id, "posted")
                    logger.info(f"[SCHEDULER] Posted successfully!")
                    
                    # Wait before posting next video
                    await asyncio.sleep(config.POST_INTERVAL)
                else:
                    logger.error(f"[SCHEDULER] Failed to post")
                    await asyncio.sleep(60)
            
            except Exception as e:
                logger.error(f"[SCHEDULER] Error posting: {e}")
                await asyncio.sleep(60)
        
        except Exception as e:
            logger.error(f"[SCHEDULER] Error: {e}")
            await asyncio.sleep(60)
    
    logger.info("[SCHEDULER] Stopped")

async def post_to_main_channel(video: dict) -> bool:
    """Post video to main channel"""
    try:
        from telegram import Bot
        bot = Bot(token=config.BOT_TOKEN)
        
        # Use original title from LuluStream if available, otherwise use queue title
        title = video.get('original_title') or video['title']
        
        # Create caption
        caption = f"""
😍{config.CHANNEL_TITLE}😍

🎬 {title}

{config.CAPTION_TEXT}
"""
        
        # Create watch button (removed download button)
        watch_url = f"https://lulustream.com/{video['lulustream_file_code']}"
        
        keyboard = [
            [InlineKeyboardButton("▶️ Watch Now", url=watch_url)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Try to send with thumbnail if available
        thumbnail_url = video.get('thumbnail_url')
        
        if thumbnail_url:
            try:
                logger.info(f"[POST] Sending with thumbnail: {thumbnail_url}")
                await bot.send_photo(
                    chat_id=config.MAIN_CHANNEL_ID,
                    photo=thumbnail_url,
                    caption=caption,
                    reply_markup=reply_markup
                )
                return True
            except Exception as e:
                logger.error(f"[POST] Failed to send with thumbnail: {e}")
                # Fall back to text message
        
        # Send as text message if no thumbnail or thumbnail failed
        await bot.send_message(
            chat_id=config.MAIN_CHANNEL_ID,
            text=caption,
            reply_markup=reply_markup
        )
        
        return True
    
    except Exception as e:
        logger.error(f"[POST] Error posting to channel: {e}")
        return False

# ==================== ADMIN COMMANDS ====================

async def start_worker_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start upload worker"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin only command")
        return
    
    global worker_running, worker_task
    
    if worker_running:
        await update.message.reply_text("⚠️ Worker is already running!")
        return
    
    worker_running = True
    worker_task = asyncio.create_task(upload_worker())
    
    await update.message.reply_text("✅ Upload worker started!")
    logger.info("Upload worker started by admin")

async def stop_worker_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stop upload worker"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin only command")
        return
    
    global worker_running, worker_task
    
    if not worker_running:
        await update.message.reply_text("⚠️ Worker is not running!")
        return
    
    worker_running = False
    
    if worker_task:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass
    
    await update.message.reply_text("✅ Upload worker stopped!")
    logger.info("Upload worker stopped by admin")

async def start_scheduler_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start post scheduler"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin only command")
        return
    
    global scheduler_running, scheduler_task
    
    if scheduler_running:
        await update.message.reply_text("⚠️ Scheduler is already running!")
        return
    
    scheduler_running = True
    scheduler_task = asyncio.create_task(post_scheduler())
    
    await update.message.reply_text("✅ Post scheduler started!")
    logger.info("Post scheduler started by admin")

async def stop_scheduler_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stop post scheduler"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin only command")
        return
    
    global scheduler_running, scheduler_task
    
    if not scheduler_running:
        await update.message.reply_text("⚠️ Scheduler is not running!")
        return
    
    scheduler_running = False
    
    if scheduler_task:
        scheduler_task.cancel()
        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass
    
    await update.message.reply_text("✅ Post scheduler stopped!")
    logger.info("Post scheduler stopped by admin")

async def post_now_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Post one video immediately"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin only command")
        return
    
    try:
        # Get one uploaded video
        ready_to_post = await database.get_uploaded_not_posted(limit=1)
        
        if not ready_to_post:
            await update.message.reply_text("⚠️ No videos ready to post")
            return
        
        video = ready_to_post[0]
        queue_id = str(video['_id'])
        
        await update.message.reply_text(f"📤 Posting: {video['file_name']}...")
        
        success = await post_to_main_channel(video)
        
        if success:
            await database.update_upload_status(queue_id, "posted")
            await update.message.reply_text("✅ Posted successfully!")
        else:
            await update.message.reply_text("❌ Failed to post")
    
    except Exception as e:
        logger.error(f"Error in post_now: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def queue_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show upload queue"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin only command")
        return
    
    try:
        pending = await database.get_pending_uploads(limit=10)
        
        if not pending:
            await update.message.reply_text("📭 Queue is empty")
            return
        
        queue_text = "📋 **Upload Queue** (First 10)\n\n"
        
        for i, video in enumerate(pending, 1):
            queue_text += f"{i}. {video['file_name']}\n"
            queue_text += f"   Status: {video['status']}\n"
            queue_text += f"   Added: {video['added_at'].strftime('%Y-%m-%d %H:%M')}\n\n"
        
        await update.message.reply_text(queue_text)
    
    except Exception as e:
        logger.error(f"Error showing queue: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def clear_failed_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear all failed uploads"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin only command")
        return
    
    try:
        count = await database.clear_failed_uploads()
        await update.message.reply_text(f"✅ Cleared {count} failed uploads")
    except Exception as e:
        logger.error(f"Error clearing failed: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

# ==================== MAIN ====================

async def post_init(application: Application):
    """Post initialization"""
    # Connect to database
    await database.connect_db()
    logger.info("✅ Database connected")

async def post_shutdown(application: Application):
    """Cleanup before shutdown"""
    global worker_running, scheduler_running, worker_task, scheduler_task
    
    # Stop worker
    if worker_running:
        worker_running = False
        if worker_task:
            worker_task.cancel()
            try:
                await worker_task
            except asyncio.CancelledError:
                pass
    
    # Stop scheduler
    if scheduler_running:
        scheduler_running = False
        if scheduler_task:
            scheduler_task.cancel()
            try:
                await scheduler_task
            except asyncio.CancelledError:
                pass
    
    # Close database
    await database.close_db()
    logger.info("✅ Cleanup completed")

# ==================== HEALTH CHECK SERVER ====================

from aiohttp import web

async def health_check(request):
    """Health check endpoint for Koyeb"""
    return web.Response(text="OK", status=200)

async def start_health_server():
    """Start health check web server"""
    app = web.Application()
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8000)
    await site.start()
    logger.info("✅ Health check server started on port 8000")

def main():
    """Start the bot"""
    
    # Start health check server in background
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(start_health_server())
    
    # Create application
    application = Application.builder().token(config.BOT_TOKEN).build()
    
    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("add_url", add_url_command))
    
    # Admin commands
    application.add_handler(CommandHandler("start_worker", start_worker_command))
    application.add_handler(CommandHandler("stop_worker", stop_worker_command))
    application.add_handler(CommandHandler("start_scheduler", start_scheduler_command))
    application.add_handler(CommandHandler("stop_scheduler", stop_scheduler_command))
    application.add_handler(CommandHandler("post_now", post_now_command))
    application.add_handler(CommandHandler("queue", queue_command))
    application.add_handler(CommandHandler("clear_failed", clear_failed_command))
    
    # Message handlers
    application.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video_message))
    
    # Post init and shutdown
    application.post_init = post_init
    application.post_shutdown = post_shutdown
    
    # Start bot
    logger.info("🚀 Bot started!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
                
