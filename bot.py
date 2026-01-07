from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import config
import database
from lulustream import LuluStreamClient
import os
import tempfile
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
from aiohttp import web
import logging

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize scheduler and client
scheduler = AsyncIOScheduler()
lulu_client = LuluStreamClient()

# Upload worker flag
upload_worker_running = False

# Bot application (will be set in main)
bot_app = None

# ==================== WEB SERVER FOR KOYEB HEALTH CHECKS ====================
async def health_check(request):
    """Health check endpoint for Koyeb"""
    return web.Response(text='OK', status=200)

async def status_page(request):
    """Status page"""
    stats = await database.get_queue_stats()
    html = f"""
    <html>
    <head><title>LuluStream Bot Status</title></head>
    <body style="font-family: Arial; padding: 20px;">
        <h1>🎬 LuluStream Bot</h1>
        <h2>✅ Bot is Running!</h2>
        <hr>
        <h3>📊 Queue Statistics:</h3>
        <ul>
            <li>📦 Total: {stats['total']}</li>
            <li>⏳ Pending: {stats['pending']}</li>
            <li>⬆️ Uploading: {stats['uploading']}</li>
            <li>✅ Uploaded: {stats['uploaded']}</li>
            <li>📤 Posted: {stats['posted']}</li>
            <li>❌ Failed: {stats['failed']}</li>
        </ul>
        <hr>
        <p>🤖 Worker: {'Running' if upload_worker_running else 'Stopped'}</p>
        <p>📅 Scheduler: {'Running' if scheduler.running else 'Stopped'}</p>
    </body>
    </html>
    """
    return web.Response(text=html, content_type='text/html')

async def start_web_server():
    """Start web server for health checks"""
    app = web.Application()
    app.router.add_get('/health', health_check)
    app.router.add_get('/', status_page)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8000)
    await site.start()
    logger.info("✅ Web server started on port 8000")

# ==================== BOT COMMANDS ====================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    text = """🎬 **LuluStream Auto Upload Bot**

**Features:**
✅ Auto upload to LuluStream
✅ Scheduled posting to main channel
✅ Supports video files & direct links
✅ Bulk upload support
✅ MongoDB database (persistent)

**How to use:**
1. Forward videos to storage channel
2. Bot uploads to LuluStream
3. Posts 10 videos/hour to main channel

**Commands:**
/stats - Queue statistics
/start_worker - Start upload worker
/stop_worker - Stop upload worker
/start_scheduler - Start auto posting
/stop_scheduler - Stop auto posting"""
    
    keyboard = [
        [InlineKeyboardButton("📊 Statistics", callback_data="stats")],
        [InlineKeyboardButton("🔄 Start Worker", callback_data="start_worker"),
         InlineKeyboardButton("⏸ Stop Worker", callback_data="stop_worker")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stats command handler"""
    if update.effective_user.id != config.ADMIN_ID:
        return
    
    stats = await database.get_queue_stats()
    
    text = f"""📊 **Queue Statistics**

📦 Total: {stats['total']}
⏳ Pending: {stats['pending']}
⬆️ Uploading: {stats['uploading']}
✅ Uploaded: {stats['uploaded']}
📤 Posted: {stats['posted']}
❌ Failed: {stats['failed']}

🤖 Worker: {'Running' if upload_worker_running else 'Stopped'}
📅 Scheduler: {'Running' if scheduler.running else 'Stopped'}"""
    
    await update.message.reply_text(text, parse_mode='Markdown')

# ==================== HANDLE FILES FROM STORAGE CHANNEL ====================

async def handle_storage_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle video files sent to storage channel"""
    try:
        # Get message (works for both messages and channel posts)
        message = update.message or update.channel_post
        if not message:
            return
        
        # Get file info
        if message.video:
            file_obj = message.video
            file_name = file_obj.file_name or f"video_{message.message_id}.mp4"
        elif message.document:
            file_obj = message.document
            file_name = file_obj.file_name or f"video_{message.message_id}.mp4"
        else:
            return
        
        file_size = file_obj.file_size
        file_id = file_obj.file_id
        
        # Get caption as title and description
        caption = message.caption or file_name
        title = caption.split('\n')[0][:200]  # First line as title
        description = caption if len(caption) > len(title) else None
        
        # Get thumbnail
        thumbnail_file_id = None
        if hasattr(file_obj, 'thumb') and file_obj.thumb:
            thumbnail_file_id = file_obj.thumb.file_id
        
        # Add to queue
        queue_id = await database.add_to_queue(
            message_id=message.message_id,
            file_name=file_name,
            file_id=file_id,
            file_size=file_size,
            title=title,
            description=description,
            thumbnail_file_id=thumbnail_file_id
        )
        
        if queue_id:
            await message.reply_text(
                f"✅ Added to queue!\n\n"
                f"📝 Title: {title}\n"
                f"📦 Size: {file_size / (1024*1024):.2f} MB\n"
                f"🆔 Queue ID: {queue_id[:8]}..."
            )
            logger.info(f"[QUEUE] Added video: {file_name} (ID: {queue_id})")
        else:
            await message.reply_text("❌ Failed to add to queue!")
            
    except Exception as e:
        logger.error(f"[ERROR] Handle storage file: {e}")
        if message:
            await message.reply_text(f"❌ Error: {e}")

async def handle_storage_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle direct download links sent to storage channel"""
    try:
        # Get message (works for both messages and channel posts)
        message = update.message or update.channel_post
        if not message or not message.text:
            return
        
        text = message.text.strip()
        
        # Check if it's a URL
        if not (text.startswith('http://') or text.startswith('https://')):
            return
        
        # Extract info from message
        lines = text.split('\n')
        video_url = lines[0]
        title = lines[1] if len(lines) > 1 else f"Video_{message.message_id}"
        description = '\n'.join(lines[2:]) if len(lines) > 2 else None
        
        # Add to queue
        queue_id = await database.add_to_queue(
            message_id=message.message_id,
            file_name=title,
            file_url=video_url,
            title=title,
            description=description
        )
        
        if queue_id:
            await message.reply_text(
                f"✅ URL added to queue!\n\n"
                f"🔗 URL: {video_url}\n"
                f"📝 Title: {title}\n"
                f"🆔 Queue ID: {queue_id[:8]}..."
            )
            logger.info(f"[QUEUE] Added URL: {title} (ID: {queue_id})")
        else:
            await message.reply_text("❌ Failed to add URL to queue!")
            
    except Exception as e:
        logger.error(f"[ERROR] Handle storage link: {e}")
        if message:
            await message.reply_text(f"❌ Error: {e}")

# ==================== UPLOAD WORKER ====================

async def upload_worker():
    """Worker to process upload queue"""
    global upload_worker_running
    
    logger.info("[WORKER] Upload worker started!")
    upload_worker_running = True
    
    while upload_worker_running:
        try:
            # Get pending uploads
            pending = await database.get_pending_uploads(limit=1)
            
            if not pending:
                await asyncio.sleep(10)
                continue
            
            item = pending[0]
            queue_id = str(item['_id'])
            logger.info(f"[WORKER] Processing: {item['title']} (ID: {queue_id[:8]}...)")
            
            # Update status to uploading
            await database.update_upload_status(queue_id, 'uploading')
            
            # Upload to LuluStream
            result = None
            
            if item.get('file_url'):
                # Upload by URL
                logger.info(f"[WORKER] Uploading by URL: {item['file_url']}")
                result = lulu_client.upload_by_url(
                    video_url=item['file_url'],
                    title=item['title'],
                    description=item.get('description')
                )
            
            elif item.get('file_id'):
                # Download file from Telegram and upload
                logger.info(f"[WORKER] Downloading from Telegram: {item['file_id']}")
                
                # Create temp file
                temp_dir = tempfile.mkdtemp()
                temp_file = os.path.join(temp_dir, item['file_name'])
                
                try:
                    # Download file
                    file = await bot_app.bot.get_file(item['file_id'])
                    await file.download_to_drive(temp_file)
                    logger.info(f"[WORKER] Downloaded to: {temp_file}")
                    
                    # Upload to LuluStream
                    result = lulu_client.upload_file(
                        file_path=temp_file,
                        title=item['title'],
                        description=item.get('description')
                    )
                    
                finally:
                    # Clean up temp file
                    try:
                        if os.path.exists(temp_file):
                            os.remove(temp_file)
                        os.rmdir(temp_dir)
                    except:
                        pass
            
            # Handle result
            if result and result.get('success'):
                filecode = result['filecode']
                url = result['url']
                
                await database.update_upload_status(
                    queue_id,
                    'uploaded',
                    lulustream_file_code=filecode,
                    lulustream_url=url
                )
                
                logger.info(f"[WORKER] ✅ Uploaded: {item['title']}")
                logger.info(f"[WORKER] URL: {url}")
            else:
                error_msg = result.get('error', 'Unknown error') if result else 'Upload failed'
                await database.update_upload_status(
                    queue_id,
                    'failed',
                    error_message=error_msg
                )
                await database.increment_retry_count(queue_id)
                logger.error(f"[WORKER] ❌ Failed: {error_msg}")
            
        except Exception as e:
            logger.error(f"[WORKER] Error: {e}")
            await asyncio.sleep(5)
    
    logger.info("[WORKER] Upload worker stopped!")

# ==================== POST SCHEDULER ====================

async def post_to_main_channel():
    """Post uploaded videos to main channel"""
    try:
        logger.info("[SCHEDULER] Posting batch to main channel...")
        
        # Get uploaded videos that haven't been posted
        videos = await database.get_uploaded_not_posted(limit=config.VIDEOS_PER_BATCH)
        
        if not videos:
            logger.info("[SCHEDULER] No videos to post")
            return
        
        posted_count = 0
        
        for video in videos:
            try:
                queue_id = str(video['_id'])
                
                # Create message text
                text = f"""🎬 **{video['title']}**

{video.get('description') or ''}

🔗 **Watch Online:**
{video['lulustream_url']}

📥 **Download:**
{video['lulustream_url'].replace('//', '//d.')}"""
                
                # Create inline keyboard
                keyboard = [
                    [InlineKeyboardButton("▶️ Watch Online", url=video['lulustream_url'])],
                    [InlineKeyboardButton("📥 Download", url=video['lulustream_url'].replace('//', '//d.'))]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Send to main channel
                await bot_app.bot.send_message(
                    chat_id=config.MAIN_CHANNEL_ID,
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                
                # Update status
                await database.update_upload_status(queue_id, 'posted')
                posted_count += 1
                
                logger.info(f"[SCHEDULER] Posted: {video['title']}")
                
                # Small delay between posts
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"[SCHEDULER] Error posting video {queue_id}: {e}")
        
        logger.info(f"[SCHEDULER] ✅ Posted {posted_count} videos")
        
    except Exception as e:
        logger.error(f"[SCHEDULER] Error: {e}")

# ==================== ADMIN COMMANDS ====================

async def start_worker_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start worker command"""
    global upload_worker_running
    
    if update.effective_user.id != config.ADMIN_ID:
        return
    
    if upload_worker_running:
        await update.message.reply_text("⚠️ Worker is already running!")
        return
    
    asyncio.create_task(upload_worker())
    await update.message.reply_text("✅ Upload worker started!")

async def stop_worker_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stop worker command"""
    global upload_worker_running
    
    if update.effective_user.id != config.ADMIN_ID:
        return
    
    if not upload_worker_running:
        await update.message.reply_text("⚠️ Worker is not running!")
        return
    
    upload_worker_running = False
    await update.message.reply_text("✅ Upload worker will stop after current upload!")

async def start_scheduler_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start scheduler command"""
    if update.effective_user.id != config.ADMIN_ID:
        return
    
    if scheduler.running:
        await update.message.reply_text("⚠️ Scheduler is already running!")
        return
    
    scheduler.add_job(
        post_to_main_channel,
        'interval',
        minutes=config.POST_INTERVAL_MINUTES,
        id='post_job'
    )
    scheduler.start()
    
    await update.message.reply_text(
        f"✅ Scheduler started!\n\n"
        f"📅 Will post {config.VIDEOS_PER_BATCH} videos every {config.POST_INTERVAL_MINUTES} minutes"
    )

async def stop_scheduler_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stop scheduler command"""
    if update.effective_user.id != config.ADMIN_ID:
        return
    
    if not scheduler.running:
        await update.message.reply_text("⚠️ Scheduler is not running!")
        return
    
    scheduler.shutdown()
    await update.message.reply_text("✅ Scheduler stopped!")

# ==================== CALLBACK QUERY HANDLER ====================

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries"""
    global upload_worker_running
    
    query = update.callback_query
    await query.answer()
    
    if query.data == "stats":
        stats = await database.get_queue_stats()
        text = f"""📊 **Queue Statistics**

📦 Total: {stats['total']}
⏳ Pending: {stats['pending']}
⬆️ Uploading: {stats['uploading']}
✅ Uploaded: {stats['uploaded']}
📤 Posted: {stats['posted']}
❌ Failed: {stats['failed']}

🤖 Worker: {'Running' if upload_worker_running else 'Stopped'}
📅 Scheduler: {'Running' if scheduler.running else 'Stopped'}"""
        
        await query.edit_message_text(text, parse_mode='Markdown')
    
    elif query.data == "start_worker":
        if not upload_worker_running:
            asyncio.create_task(upload_worker())
            await query.answer("✅ Worker started!", show_alert=True)
        else:
            await query.answer("⚠️ Already running!", show_alert=True)
    
    elif query.data == "stop_worker":
        upload_worker_running = False
        await query.answer("✅ Worker stopping...", show_alert=True)

# ==================== MAIN ====================

async def main():
    """Main function"""
    global bot_app
    
    logger.info("🚀 Starting LuluStream Bot...")
    
    # Connect to MongoDB
    await database.connect_db()
    
    # Start web server for Koyeb health checks
    await start_web_server()
    
    # Create bot application
    bot_app = Application.builder().token(config.BOT_TOKEN).build()
    
    # Add handlers
    bot_app.add_handler(CommandHandler("start", start_command))
    bot_app.add_handler(CommandHandler("stats", stats_command))
    bot_app.add_handler(CommandHandler("start_worker", start_worker_command))
    bot_app.add_handler(CommandHandler("stop_worker", stop_worker_command))
    bot_app.add_handler(CommandHandler("start_scheduler", start_scheduler_command))
    bot_app.add_handler(CommandHandler("stop_scheduler", stop_scheduler_command))
    
    # Storage channel handlers (handles both messages and channel posts)
    bot_app.add_handler(MessageHandler(
        (filters.Chat(config.STORAGE_CHANNEL_ID) | filters.Chat(username=f"@{config.STORAGE_CHANNEL_ID}")) & 
        (filters.VIDEO | filters.Document.ALL),
        handle_storage_file
    ))
    bot_app.add_handler(MessageHandler(
        (filters.Chat(config.STORAGE_CHANNEL_ID) | filters.Chat(username=f"@{config.STORAGE_CHANNEL_ID}")) & 
        filters.TEXT & ~filters.COMMAND,
        handle_storage_link
    ))
    
    # Callback query handler
    bot_app.add_handler(CallbackQueryHandler(callback_handler))
    
    # Start bot
    logger.info("✅ Bot is running!")
    logger.info("🌐 Web server: http://0.0.0.0:8000")
    
    # Run bot
    await bot_app.initialize()
    await bot_app.start()
    await bot_app.updater.start_polling()
    
    # Keep running
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 Bot stopped by user")
