import os
from os import getenv
from dotenv import load_dotenv

load_dotenv()

# ==================== BOT CONFIGURATION ====================
API_ID = int(getenv("API_ID", "0"))
API_HASH = getenv("API_HASH", "")
BOT_TOKEN = getenv("BOT_TOKEN", "")

# ==================== CHANNEL IDS ====================
# Channel where you send files to be uploaded
STORAGE_CHANNEL_ID = int(getenv("STORAGE_CHANNEL_ID", "0"))

# Main channel where bot will post LuluStream links
MAIN_CHANNEL_ID = int(getenv("MAIN_CHANNEL_ID", "0"))

# Admin user ID (your Telegram ID)
ADMIN_ID = int(getenv("ADMIN_ID", "1206988513"))

# ==================== LULUSTREAM API ====================
LULUSTREAM_API_KEY = getenv("LULUSTREAM_API_KEY", "")
LULUSTREAM_UPLOAD_SERVER = "https://s1.myvideo.com/upload/01"
LULUSTREAM_API_BASE = "https://lulustream.com/api"

# ==================== UPLOAD SETTINGS ====================
# LuluStream folder ID (where videos will be uploaded)
FOLDER_ID = int(getenv("FOLDER_ID", "25"))

# LuluStream category ID
CATEGORY_ID = int(getenv("CATEGORY_ID", "5"))

# Tags for uploaded videos
DEFAULT_TAGS = getenv("DEFAULT_TAGS", "Promo, High quality")

# Public flag (1 = public, 0 = private)
FILE_PUBLIC = int(getenv("FILE_PUBLIC", "1"))

# Adult flag (1 = adult content, 0 = normal)
FILE_ADULT = int(getenv("FILE_ADULT", "1"))

# ==================== SCHEDULER SETTINGS ====================
# How many videos to post per batch
VIDEOS_PER_BATCH = int(getenv("VIDEOS_PER_BATCH", "10"))

# Interval between batches (in minutes)
POST_INTERVAL_MINUTES = int(getenv("POST_INTERVAL_MINUTES", "60"))

# ==================== MONGODB DATABASE ====================
MONGO_URI = getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = getenv("MONGO_DB", "lulustream_bot")

# ==================== LOGGING ====================
LOG_LEVEL = getenv("LOG_LEVEL", "INFO")
