# 🚀 Quick Setup Guide

## Step 1: Get Your Credentials

### 1.1 Telegram API Credentials

1. Go to https://my.telegram.org
2. Login with your phone number
3. Click on "API Development Tools"
4. Create a new application
5. Copy your `API_ID` and `API_HASH`

### 1.2 Bot Token

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` command
3. Follow instructions to create bot
4. Copy the `BOT_TOKEN`

### 1.3 Channel IDs

**Method 1: Using @userinfobot**
1. Add `@userinfobot` to your channel as admin
2. Forward any message from channel to `@userinfobot`
3. It will show channel ID (with -100 prefix)

**Method 2: Using web.telegram.org**
1. Open https://web.telegram.org
2. Click on your channel
3. Check URL: `https://web.telegram.org/k/#-1001234567890`
4. The number is your channel ID

### 1.4 Your User ID

1. Send any message to `@userinfobot`
2. It will reply with your user ID

### 1.5 LuluStream API Key

1. Login to your LuluStream account
2. Go to API settings
3. Copy your API key

## Step 2: Setup Bot

### 2.1 Clone Repository

```bash
git clone https://github.com/Sivaramanyt/Lulu-stream-file-upload-bot.git
cd Lulu-stream-file-upload-bot
```

### 2.2 Install Dependencies

```bash
pip install -r requirements.txt
```

### 2.3 Configure Environment

Create `.env` file:

```bash
cp .env.example .env
nano .env
```

Fill in your credentials:

```env
# Bot Credentials
API_ID=12345678
API_HASH=abcdef1234567890abcdef1234567890
BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz

# Channels (with -100 prefix)
STORAGE_CHANNEL_ID=-1001234567890
MAIN_CHANNEL_ID=-1009876543210

# Your User ID
ADMIN_ID=123456789

# LuluStream
LULUSTREAM_API_KEY=199514y1c4wef9n2vn39jl
```

### 2.4 Run Bot

```bash
python bot.py
```

Or use startup script:

```bash
chmod +x start.sh
./start.sh
```

## Step 3: Setup Channels

### 3.1 Storage Channel

1. Create a private channel
2. Add your bot as admin
3. This is where you send videos to upload

### 3.2 Main Channel

1. Create a public/private channel
2. Add your bot as admin with post permission
3. This is where bot posts LuluStream links

## Step 4: Start Using

### 4.1 Start Bot

1. Open bot in Telegram
2. Send `/start` command
3. Bot will show available commands

### 4.2 Start Upload Worker

Send `/start_worker` command to bot

**What it does:**
- Monitors upload queue
- Downloads videos from Telegram
- Uploads to LuluStream
- Updates database status

### 4.3 Start Scheduler

Send `/start_scheduler` command to bot

**What it does:**
- Posts uploaded videos to main channel
- Posts 10 videos every 1 hour (configurable)
- Automatically stops when queue is empty

### 4.4 Upload Videos

**Method 1: Video Files**

1. Forward video file to **STORAGE_CHANNEL**
2. Add caption with title and description:
   ```
   Movie Name (2024)
   Genre: Action
   Description here...
   ```
3. Bot will add to queue automatically

**Method 2: Direct Links**

1. Send direct download link to **STORAGE_CHANNEL**:
   ```
   https://example.com/video.mp4
   Movie Title
   Movie description
   ```
2. Bot will add to queue

## Step 5: Monitor Status

### Check Statistics

Send `/stats` command:

```
📊 Queue Statistics

📦 Total: 50
⏳ Pending: 10
⬆️ Uploading: 1
✅ Uploaded: 25
📤 Posted: 14
❌ Failed: 0

🤖 Worker: Running
📅 Scheduler: Running
```

## ⚙️ Advanced Configuration

### Change Posting Schedule

Edit `.env` file:

```env
# Post 5 videos every 30 minutes
VIDEOS_PER_BATCH=5
POST_INTERVAL_MINUTES=30
```

### Change LuluStream Settings

```env
FOLDER_ID=25          # Your folder ID
CATEGORY_ID=5         # Category ID
DEFAULT_TAGS=HD, Tamil  # Default tags
FILE_PUBLIC=1         # 1=public, 0=private
FILE_ADULT=1          # 1=adult, 0=normal
```

## 🐛 Troubleshooting

### Bot not responding?

1. Check if bot is running: `ps aux | grep bot.py`
2. Check logs for errors
3. Restart bot: `python bot.py`

### Worker not uploading?

1. Check worker status: `/stats`
2. Stop and restart: `/stop_worker` then `/start_worker`
3. Check LuluStream API key is correct

### Videos not posting?

1. Check scheduler status: `/stats`
2. Verify bot has admin rights in MAIN_CHANNEL
3. Check if there are uploaded videos: `/stats`

### Upload fails?

**Common issues:**
- File too large (max 2GB recommended)
- Invalid LuluStream API key
- Network timeout (try smaller files)
- Storage channel ID wrong

## 🚀 Deployment

### Deploy on Koyeb

1. Create account on https://koyeb.com
2. Connect GitHub repository
3. Add environment variables
4. Deploy!

### Deploy on Railway

1. Create account on https://railway.app
2. New Project → Deploy from GitHub
3. Select repository
4. Add environment variables
5. Deploy!

### Deploy on VPS

```bash
# Install Python
sudo apt update
sudo apt install python3 python3-pip

# Clone repo
git clone https://github.com/Sivaramanyt/Lulu-stream-file-upload-bot.git
cd Lulu-stream-file-upload-bot

# Install dependencies
pip3 install -r requirements.txt

# Create .env
nano .env  # Add your credentials

# Run with screen
screen -S lulubot
python3 bot.py
# Press Ctrl+A then D to detach
```

## 📝 Notes

- Bot stores data in SQLite database (`lulustream_bot.db`)
- Downloaded videos are stored temporarily and deleted after upload
- Failed uploads are retried automatically
- Scheduler posts oldest uploaded videos first
- Bot can handle multiple uploads simultaneously

## ❓ FAQ

**Q: How long does upload take?**
A: Depends on file size and internet speed. Typically 5-30 minutes.

**Q: Can I upload multiple videos at once?**
A: Yes! Send all videos to storage channel. Worker processes them one by one.

**Q: What video formats are supported?**
A: MP4, MKV, AVI, and most common formats.

**Q: Can I change posting schedule?**
A: Yes, edit `POST_INTERVAL_MINUTES` in `.env` and restart bot.

**Q: Is it safe to use?**
A: Yes, all credentials are stored locally in `.env` file.

## 👤 Support

If you need help:
1. Check this guide first
2. Read README.md
3. Check GitHub Issues
4. Contact developer

---

**Happy Uploading! 🎉**
