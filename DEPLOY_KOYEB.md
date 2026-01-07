# 🚀 Deploy to Koyeb - Complete Guide

## 🌟 Why Koyeb?

- ✅ **Free Tier** - Perfect for 24/7 bot hosting
- ⚡ **Fast Deployment** - Deploy in minutes
- 🌍 **Global Edge Network** - Low latency
- 🔄 **Auto Restart** - Never goes offline
- 📦 **No Sleep Mode** - Unlike Heroku free tier

## 📖 Step-by-Step Deployment

### Step 1: Prepare Your Credentials

Before deploying, gather these:

1. **Telegram API Credentials**
   - Go to https://my.telegram.org
   - Create app and get `API_ID` & `API_HASH`

2. **Bot Token**
   - Message `@BotFather` on Telegram
   - Create bot with `/newbot`
   - Copy `BOT_TOKEN`

3. **Channel IDs**
   - Storage Channel ID (where you send videos)
   - Main Channel ID (where bot posts links)
   - Use `@userinfobot` to get IDs

4. **Your User ID**
   - Send message to `@userinfobot`
   - Copy your user ID

5. **LuluStream API Key**
   - Your LuluStream API key: `199514y1c4wef9n2vn39jl`

### Step 2: Deploy on Koyeb

#### Option 1: Deploy via Koyeb Dashboard (Recommended)

1. **Go to Koyeb**
   - Visit https://app.koyeb.com
   - Sign up / Login (free account)

2. **Create New Service**
   - Click "Create Service"
   - Select "GitHub" as source

3. **Connect GitHub Repository**
   - Click "Connect GitHub"
   - Authorize Koyeb
   - Select repository: `Sivaramanyt/Lulu-stream-file-upload-bot`
   - Branch: `main`

4. **Configure Build**
   - Builder: **Docker**
   - Dockerfile path: `Dockerfile`

5. **Configure Service**
   - Service name: `lulustream-bot`
   - Service type: **Worker** (not Web)
   - Instance type: **Nano** (free tier)
   - Region: **Frankfurt (fra)** - Best for India

6. **Add Environment Variables**

   Click "Add Environment Variable" for each:

   ```
   API_ID = your_api_id
   API_HASH = your_api_hash
   BOT_TOKEN = your_bot_token
   STORAGE_CHANNEL_ID = -1001234567890
   MAIN_CHANNEL_ID = -1009876543210
   ADMIN_ID = your_user_id
   LULUSTREAM_API_KEY = 199514y1c4wef9n2vn39jl
   FOLDER_ID = 25
   CATEGORY_ID = 5
   DEFAULT_TAGS = Promo, High quality
   FILE_PUBLIC = 1
   FILE_ADULT = 1
   VIDEOS_PER_BATCH = 10
   POST_INTERVAL_MINUTES = 60
   ```

   **Important:** Use "Secret" for sensitive values:
   - API_ID
   - API_HASH
   - BOT_TOKEN
   - LULUSTREAM_API_KEY

7. **Disable Health Checks**
   - Scroll to "Health Checks"
   - **Disable** health checks (bot is a worker, not web service)

8. **Deploy**
   - Click "Deploy"
   - Wait 2-3 minutes for deployment
   - Check logs for "Bot is running!"

#### Option 2: Deploy via Koyeb CLI

```bash
# Install Koyeb CLI
curl -fsSL https://cli.koyeb.com/install.sh | sh

# Login
koyeb login

# Create service
koyeb service create lulustream-bot \
  --type worker \
  --instance-type nano \
  --regions fra \
  --docker-dockerfile Dockerfile \
  --git-repository github.com/Sivaramanyt/Lulu-stream-file-upload-bot \
  --git-branch main \
  --env API_ID=your_api_id \
  --env API_HASH=your_api_hash \
  --env BOT_TOKEN=your_bot_token \
  --env STORAGE_CHANNEL_ID=-1001234567890 \
  --env MAIN_CHANNEL_ID=-1009876543210 \
  --env ADMIN_ID=your_user_id \
  --env LULUSTREAM_API_KEY=199514y1c4wef9n2vn39jl
```

### Step 3: Verify Deployment

1. **Check Logs**
   - Go to Koyeb dashboard
   - Click on your service
   - Go to "Logs" tab
   - Look for:
     ```
     🚀 Starting LuluStream Bot...
     ✅ Database initialized successfully!
     ✅ Bot is running!
     ```

2. **Test Bot**
   - Open Telegram
   - Send `/start` to your bot
   - Bot should respond immediately

3. **Start Services**
   - Send `/start_worker` - Start upload worker
   - Send `/start_scheduler` - Start auto posting
   - Send `/stats` - Check status

### Step 4: Setup Channels

1. **Storage Channel**
   - Create private channel
   - Add bot as admin
   - Send test video

2. **Main Channel**
   - Create public/private channel
   - Add bot as admin with post permission
   - Bot will post here automatically

### Step 5: Start Using!

1. Forward videos to **Storage Channel**
2. Bot uploads to LuluStream automatically
3. Scheduler posts 10 videos/hour to **Main Channel**

## 📊 Monitor Your Bot

### Koyeb Dashboard

- **Service Status** - Check if running
- **Logs** - Real-time bot logs
- **Metrics** - CPU, Memory usage
- **Deployments** - Deployment history

### Bot Commands

```
/stats - Queue statistics
/start_worker - Start upload worker
/stop_worker - Stop upload worker  
/start_scheduler - Start posting
/stop_scheduler - Stop posting
```

## 🔄 Update Your Bot

### Method 1: Auto Deploy (Recommended)

1. Push changes to GitHub
2. Koyeb auto-detects and redeploys
3. Wait 2-3 minutes

### Method 2: Manual Redeploy

1. Go to Koyeb dashboard
2. Click on service
3. Click "Redeploy"
4. Select latest commit
5. Deploy

## ⚙️ Configuration Changes

### Change Environment Variables

1. Go to Koyeb dashboard
2. Click on service → "Settings"
3. Go to "Environment Variables"
4. Edit variables
5. Click "Update"
6. Service auto-restarts

### Change Instance Type

**Free Tier (Nano):**
- 512 MB RAM
- 0.1 vCPU
- Perfect for this bot

**Upgrade if needed:**
- Micro: $5.32/month
- Small: $10.64/month

## 🐛 Troubleshooting

### Bot not starting?

1. **Check logs** in Koyeb dashboard
2. **Verify environment variables** are set correctly
3. **Check service type** is "Worker" not "Web"
4. **Verify health checks** are disabled

### Upload fails?

1. Check LuluStream API key is correct
2. Verify bot has admin rights in storage channel
3. Check file size (<2GB recommended)
4. View logs for detailed error messages

### Videos not posting?

1. Check scheduler is running: `/stats`
2. Verify bot is admin in main channel
3. Check there are uploaded videos in queue
4. Start scheduler: `/start_scheduler`

### Out of Memory?

- Nano instance has 512MB RAM
- If processing large files, upgrade to Micro
- Or reduce `VIDEOS_PER_BATCH`

## 💰 Cost Breakdown

### Free Tier
- **Cost:** $0/month
- **Instance:** Nano (512MB RAM)
- **Limitations:** 
  - No custom domain needed (bot doesn't need web)
  - Perfect for this bot!

### Paid Upgrade (Optional)
- Only if you need more power
- Micro: $5.32/month (1GB RAM)
- Small: $10.64/month (2GB RAM)

## 🔒 Security Best Practices

1. **Use Secrets**
   - Mark sensitive variables as "Secret" in Koyeb
   - Never commit `.env` to GitHub

2. **Secure Channels**
   - Make storage channel private
   - Only you and bot as admins

3. **Admin Only**
   - Only admin can control bot
   - Set correct `ADMIN_ID`

## 📝 Quick Reference

### Environment Variables

| Variable | Example | Required |
|----------|---------|----------|
| API_ID | 12345678 | Yes |
| API_HASH | abc123... | Yes |
| BOT_TOKEN | 123:ABC... | Yes |
| STORAGE_CHANNEL_ID | -1001234567890 | Yes |
| MAIN_CHANNEL_ID | -1009876543210 | Yes |
| ADMIN_ID | 123456789 | Yes |
| LULUSTREAM_API_KEY | 199514y1c4... | Yes |
| FOLDER_ID | 25 | No |
| CATEGORY_ID | 5 | No |
| VIDEOS_PER_BATCH | 10 | No |
| POST_INTERVAL_MINUTES | 60 | No |

### Bot Commands

| Command | Action |
|---------|--------|
| `/start` | Welcome message |
| `/stats` | Queue statistics |
| `/start_worker` | Start upload worker |
| `/stop_worker` | Stop worker |
| `/start_scheduler` | Start auto posting |
| `/stop_scheduler` | Stop posting |

## 🎉 Success Checklist

- [ ] Koyeb account created
- [ ] Repository connected
- [ ] All environment variables added
- [ ] Service type set to "Worker"
- [ ] Health checks disabled
- [ ] Bot deployed successfully
- [ ] Bot responds to `/start`
- [ ] Storage channel created & bot added
- [ ] Main channel created & bot added
- [ ] Worker started with `/start_worker`
- [ ] Scheduler started with `/start_scheduler`
- [ ] Test video uploaded successfully

---

**Your bot is now live on Koyeb! 🎉**

Happy uploading! 🚀
