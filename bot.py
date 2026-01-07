from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import config
import database
from lulustream import LuluStreamClient
import os
import tempfile
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta

# Initialize bot
bot = Client(
    "lulustream_bot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN
)

# Initialize scheduler
scheduler = AsyncIOScheduler()
lulu_client = LuluStreamClient()

# Upload worker flag
upload_worker_running = False

# ==================== START COMMAND ====================
@bot.on_message(filters.command("start") & filters.private)
async def start_command(client, message: Message):
    text = f"""🎬 **LuluStream Auto Upload Bot**

**Features:**
✅ Auto upload to LuluStream
✅ Scheduled posting to main channel
✅ Supports video files & direct links
✅ Bulk upload support

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
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Statistics", callback_data="stats")],
        [InlineKeyboardButton("🔄 Start Worker", callback_data="start_worker"),
         InlineKeyboardButton("⏸ Stop Worker", callback_data="stop_worker")]
    ])
    
    await message.reply_text(text, reply_markup=keyboard)

# ==================== STATS COMMAND ====================
@bot.on_message(filters.command("stats") & filters.user(config.ADMIN_ID))
async def stats_command(client, message: Message):
    stats = database.get_queue_stats()
    
    text = f"""📊 **Queue Statistics**

📦 Total: {stats['total']}
⏳ Pending: {stats['pending']}
⬆️ Uploading: {stats['uploading']}
✅ Uploaded: {stats['uploaded']}
📤 Posted: {stats['posted']}
❌ Failed: {stats['failed']}

🤖 Worker: {'Running' if upload_worker_running else 'Stopped'}
📅 Scheduler: {'Running' if scheduler.running else 'Stopped'}"""
    
    await message.reply_text(text)

# ==================== HANDLE FILES FROM STORAGE CHANNEL ====================
@bot.on_message(filters.chat(config.STORAGE_CHANNEL_ID) & (filters.video | filters.document))
async def handle_storage_file(client, message: Message):
    """Handle video files sent to storage channel"""
    try:
        # Get file info
        file_obj = message.video or message.document
        file_name = file_obj.file_name or f"video_{message.id}.mp4"
        file_size = file_obj.file_size
        file_id = file_obj.file_id
        
        # Get caption as title and description
        caption = message.caption or file_name
        title = caption.split('\n')[0][:200]  # First line as title
        description = caption if len(caption) > len(title) else None
        
        # Get thumbnail
        thumbnail_file_id = None
        if hasattr(file_obj, 'thumbs') and file_obj.thumbs:
            thumbnail_file_id = file_obj.thumbs[0].file_id
        
        # Add to queue
        queue_id = database.add_to_queue(
            message_id=message.id,
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
                f"🆔 Queue ID: {queue_id}"
            )
            print(f"[QUEUE] Added video: {file_name} (ID: {queue_id})")
        else:
            await message.reply_text("❌ Failed to add to queue!")
            
    except Exception as e:
        print(f"[ERROR] Handle storage file: {e}")
        await message.reply_text(f"❌ Error: {e}")

# ==================== HANDLE TEXT MESSAGES (DIRECT LINKS) ====================
@bot.on_message(filters.chat(config.STORAGE_CHANNEL_ID) & filters.text)
async def handle_storage_link(client, message: Message):
    """Handle direct download links sent to storage channel"""
    try:
        text = message.text.strip()
        
        # Check if it's a URL
        if not (text.startswith('http://') or text.startswith('https://')):
            return
        
        # Extract info from message
        lines = text.split('\n')
        video_url = lines[0]
        title = lines[1] if len(lines) > 1 else f"Video_{message.id}"
        description = '\n'.join(lines[2:]) if len(lines) > 2 else None
        
        # Add to queue
        queue_id = database.add_to_queue(
            message_id=message.id,
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
                f"🆔 Queue ID: {queue_id}"
            )
            print(f"[QUEUE] Added URL: {title} (ID: {queue_id})")
        else:
            await message.reply_text("❌ Failed to add URL to queue!")
            
    except Exception as e:
        print(f"[ERROR] Handle storage link: {e}")
        await message.reply_text(f"❌ Error: {e}")

# ==================== UPLOAD WORKER ====================
async def upload_worker():
    """Worker to process upload queue"""
    global upload_worker_running
    
    print("[WORKER] Upload worker started!")
    upload_worker_running = True
    
    while upload_worker_running:
        try:
            # Get pending uploads
            pending = database.get_pending_uploads(limit=1)
            
            if not pending:
                await asyncio.sleep(10)  # Wait 10 seconds if queue is empty
                continue
            
            item = pending[0]
            print(f"[WORKER] Processing: {item.title} (ID: {item.id})")
            
            # Update status to uploading
            database.update_upload_status(item.id, 'uploading')
            
            # Upload to LuluStream
            result = None
            
            if item.file_url:
                # Upload by URL
                print(f"[WORKER] Uploading by URL: {item.file_url}")
                result = lulu_client.upload_by_url(
                    video_url=item.file_url,
                    title=item.title,
                    description=item.description
                )
            
            elif item.file_id:
                # Download file from Telegram and upload
                print(f"[WORKER] Downloading from Telegram: {item.file_id}")
                
                # Create temp file
                temp_dir = tempfile.mkdtemp()
                temp_file = os.path.join(temp_dir, item.file_name)
                
                try:
                    # Download file
                    await bot.download_media(item.file_id, file_name=temp_file)
                    print(f"[WORKER] Downloaded to: {temp_file}")
                    
                    # Upload to LuluStream
                    result = lulu_client.upload_file(
                        file_path=temp_file,
                        title=item.title,
                        description=item.description
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
                
                database.update_upload_status(
                    item.id,
                    'uploaded',
                    lulustream_file_code=filecode,
                    lulustream_url=url
                )
                
                print(f"[WORKER] ✅ Uploaded: {item.title}")
                print(f"[WORKER] URL: {url}")
                
            else:
                error_msg = result.get('error', 'Unknown error') if result else 'Upload failed'
                database.update_upload_status(
                    item.id,
                    'failed',
                    error_message=error_msg
                )
                database.increment_retry_count(item.id)
                print(f"[WORKER] ❌ Failed: {error_msg}")
            
        except Exception as e:
            print(f"[WORKER] Error: {e}")
            await asyncio.sleep(5)
    
    print("[WORKER] Upload worker stopped!")

# ==================== POST SCHEDULER ====================
async def post_to_main_channel():
    """Post uploaded videos to main channel"""
    try:
        print("[SCHEDULER] Posting batch to main channel...")
        
        # Get uploaded videos that haven't been posted
        videos = database.get_uploaded_not_posted(limit=config.VIDEOS_PER_BATCH)
        
        if not videos:
            print("[SCHEDULER] No videos to post")
            return
        
        posted_count = 0
        
        for video in videos:
            try:
                # Create message text
                text = f"""🎬 **{video.title}**

{video.description or ''}

🔗 **Watch Online:**
{video.lulustream_url}

📥 **Download:**
{video.lulustream_url.replace('//', '//d.')}"""
                
                # Create inline keyboard
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("▶️ Watch Online", url=video.lulustream_url)],
                    [InlineKeyboardButton("📥 Download", url=video.lulustream_url.replace('//', '//d.'))]
                ])
                
                # Send to main channel
                await bot.send_message(
                    chat_id=config.MAIN_CHANNEL_ID,
                    text=text,
                    reply_markup=keyboard
                )
                
                # Update status
                database.update_upload_status(video.id, 'posted')
                posted_count += 1
                
                print(f"[SCHEDULER] Posted: {video.title}")
                
                # Small delay between posts
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"[SCHEDULER] Error posting video {video.id}: {e}")
        
        print(f"[SCHEDULER] ✅ Posted {posted_count} videos")
        
    except Exception as e:
        print(f"[SCHEDULER] Error: {e}")

# ==================== COMMAND: START WORKER ====================
@bot.on_message(filters.command("start_worker") & filters.user(config.ADMIN_ID))
async def start_worker_command(client, message: Message):
    global upload_worker_running
    
    if upload_worker_running:
        await message.reply_text("⚠️ Worker is already running!")
        return
    
    # Start worker in background
    asyncio.create_task(upload_worker())
    await message.reply_text("✅ Upload worker started!")

# ==================== COMMAND: STOP WORKER ====================
@bot.on_message(filters.command("stop_worker") & filters.user(config.ADMIN_ID))
async def stop_worker_command(client, message: Message):
    global upload_worker_running
    
    if not upload_worker_running:
        await message.reply_text("⚠️ Worker is not running!")
        return
    
    upload_worker_running = False
    await message.reply_text("✅ Upload worker will stop after current upload!")

# ==================== COMMAND: START SCHEDULER ====================
@bot.on_message(filters.command("start_scheduler") & filters.user(config.ADMIN_ID))
async def start_scheduler_command(client, message: Message):
    if scheduler.running:
        await message.reply_text("⚠️ Scheduler is already running!")
        return
    
    # Add job to scheduler
    scheduler.add_job(
        post_to_main_channel,
        'interval',
        minutes=config.POST_INTERVAL_MINUTES,
        id='post_job'
    )
    scheduler.start()
    
    await message.reply_text(
        f"✅ Scheduler started!\n\n"
        f"📅 Will post {config.VIDEOS_PER_BATCH} videos every {config.POST_INTERVAL_MINUTES} minutes"
    )

# ==================== COMMAND: STOP SCHEDULER ====================
@bot.on_message(filters.command("stop_scheduler") & filters.user(config.ADMIN_ID))
async def stop_scheduler_command(client, message: Message):
    if not scheduler.running:
        await message.reply_text("⚠️ Scheduler is not running!")
        return
    
    scheduler.shutdown()
    await message.reply_text("✅ Scheduler stopped!")

# ==================== CALLBACK QUERY HANDLER ====================
@bot.on_callback_query()
async def callback_handler(client, callback_query):
    data = callback_query.data
    
    if data == "stats":
        stats = database.get_queue_stats()
        text = f"""📊 **Queue Statistics**

📦 Total: {stats['total']}
⏳ Pending: {stats['pending']}
⬆️ Uploading: {stats['uploading']}
✅ Uploaded: {stats['uploaded']}
📤 Posted: {stats['posted']}
❌ Failed: {stats['failed']}

🤖 Worker: {'Running' if upload_worker_running else 'Stopped'}
📅 Scheduler: {'Running' if scheduler.running else 'Stopped'}"""
        
        await callback_query.answer()
        await callback_query.message.edit_text(text)
    
    elif data == "start_worker":
        global upload_worker_running
        if not upload_worker_running:
            asyncio.create_task(upload_worker())
            await callback_query.answer("✅ Worker started!", show_alert=True)
        else:
            await callback_query.answer("⚠️ Already running!", show_alert=True)
    
    elif data == "stop_worker":
        upload_worker_running = False
        await callback_query.answer("✅ Worker stopping...", show_alert=True)

# ==================== MAIN ====================
if __name__ == "__main__":
    print("🚀 Starting LuluStream Bot...")
    
    # Initialize database
    database.init_db()
    
    # Start bot
    print("✅ Bot is running!")
    bot.run()
