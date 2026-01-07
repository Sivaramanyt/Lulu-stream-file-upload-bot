# 🎬 LuluStream Auto Upload Bot

A powerful Telegram bot that automatically uploads videos to LuluStream and posts them to your channel with scheduled batching.

## 🌟 Features

- ✅ **Auto Upload to LuluStream** - Upload video files and direct download links
- 📅 **Scheduled Posting** - Post 10 videos every hour automatically
- 📦 **Bulk Upload Support** - Upload multiple videos at once
- 📊 **Queue Management** - Track upload status with SQLite database
- ⚡ **URL Upload Support** - Upload videos from direct links
- 🖼️ **Thumbnail Support** - Automatically extracts and uploads thumbnails
- ⏱️ **Background Worker** - Uploads run in background without blocking

## 🛠️ How It Works

```
1. Forward videos to STORAGE CHANNEL
   ↓
2. Bot downloads and uploads to LuluStream
   ↓
3. Videos added to queue as "uploaded"
   ↓
4. Scheduler posts 10 videos/hour to MAIN CHANNEL
   ↓
5. Users get watch & download links
```

## 🚀 Setup Instructions

### 1. Clone Repository

```bash
git clone https://github.com/Sivaramanyt/Lulu-stream-file-upload-bot.git
cd Lulu-stream-file-upload-bot
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
cp .env.example .env
nano .env  # Edit with your credentials
```

**Required Settings:**

- `API_ID` & `API_HASH` - Get from https://my.telegram.org
- `BOT_TOKEN` - Get from @BotFather
- `STORAGE_CHANNEL_ID` - Channel where you send videos
- `MAIN_CHANNEL_ID` - Channel where bot posts links
- `ADMIN_ID` - Your Telegram user ID
- `LULUSTREAM_API_KEY` - Your LuluStream API key

### 4. Run Bot

```bash
python bot.py
```

## 📝 Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Show bot info and buttons |
| `/stats` | Show queue statistics |
| `/start_worker` | Start upload worker |
| `/stop_worker` | Stop upload worker |
| `/start_scheduler` | Start auto posting |
| `/stop_scheduler` | Stop auto posting |

## 📸 Usage

### Upload Video Files

1. Forward video to **STORAGE_CHANNEL**
2. Bot adds to queue automatically
3. Worker uploads to LuluStream
4. Scheduler posts to MAIN_CHANNEL

### Upload from URL

Send direct download link to **STORAGE_CHANNEL**:

```
https://example.com/video.mp4
Movie Title
Movie description here
```

Format:
- Line 1: URL
- Line 2: Title
- Line 3+: Description

## ⚙️ Configuration

### Scheduler Settings

```env
VIDEOS_PER_BATCH=10          # Videos per post batch
POST_INTERVAL_MINUTES=60     # Minutes between batches
```

**Examples:**
- Post 10 videos/hour: `VIDEOS_PER_BATCH=10`, `POST_INTERVAL_MINUTES=60`
- Post 5 videos every 30 min: `VIDEOS_PER_BATCH=5`, `POST_INTERVAL_MINUTES=30`

### LuluStream Settings

```env
FOLDER_ID=25                 # Your LuluStream folder
CATEGORY_ID=5                # Video category
DEFAULT_TAGS=Promo, HD       # Default tags
FILE_PUBLIC=1                # 1=public, 0=private
FILE_ADULT=1                 # 1=adult, 0=normal
```

## 📊 Database Schema

### Upload Queue Table

```sql
CREATE TABLE upload_queue (
    id INTEGER PRIMARY KEY,
    message_id INTEGER,
    file_id VARCHAR(255),
    file_url TEXT,
    file_name VARCHAR(500),
    title VARCHAR(500),
    description TEXT,
    status VARCHAR(50),          -- pending, uploading, uploaded, posted, failed
    lulustream_file_code VARCHAR(100),
    lulustream_url TEXT,
    added_at DATETIME,
    uploaded_at DATETIME,
    posted_at DATETIME
);
```

## 🔧 Deployment

### Deploy on Koyeb

1. Fork this repository
2. Connect to Koyeb
3. Add environment variables
4. Deploy!

### Deploy on Railway

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template)

### Deploy on Heroku

```bash
heroku create your-app-name
heroku config:set API_ID=your_api_id
heroku config:set API_HASH=your_api_hash
# ... set all environment variables
git push heroku main
```

## 🐛 Troubleshooting

### Bot not uploading?

1. Check worker status: `/stats`
2. Start worker: `/start_worker`
3. Check logs for errors

### Videos not posting?

1. Check scheduler status: `/stats`
2. Start scheduler: `/start_scheduler`
3. Verify MAIN_CHANNEL_ID is correct

### Upload fails?

- Check LuluStream API key
- Verify video file size (<2GB recommended)
- Check internet connection

## 📝 License

MIT License - Feel free to use and modify!

## 👤 Author

**Sivaraman**
- GitHub: [@Sivaramanyt](https://github.com/Sivaramanyt)
- Telegram: Your Channel

## ⭐ Support

If you find this bot useful, please give it a star ⭐

## 📦 Updates

Check [Releases](https://github.com/Sivaramanyt/Lulu-stream-file-upload-bot/releases) for updates!
