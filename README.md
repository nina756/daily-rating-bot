# Daily Rating Telegram Bot

A Telegram bot that sends daily reminders at 5 PM to rate your day (1-10 scale) and stores the responses in a CSV file.

## Features
- ✅ Sends daily reminders at 5 PM
- ✅ Validates ratings (only accepts 1-10)
- ✅ Stores data with date and timestamp
- ✅ Runs 24/7 (when deployed to a server)

## Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Your Bot

Edit the script or set environment variables:

**Option A: Edit the script directly**
- Replace `YOUR_BOT_TOKEN_HERE` with your Telegram bot token
- Replace `YOUR_CHAT_ID_HERE` with your friend's chat ID

**Option B: Use environment variables (recommended)**
```bash
export TELEGRAM_TOKEN="your_bot_token_here"
export CHAT_ID="your_chat_id_here"
```

### 3. Adjust Timezone (Optional)

In the script, change this line to your timezone:
```python
TIMEZONE = pytz.timezone('Europe/Berlin')  # Change to your timezone
```

Common timezones:
- `'America/New_York'` - Eastern Time
- `'America/Los_Angeles'` - Pacific Time
- `'Europe/London'` - UK
- `'Asia/Tokyo'` - Japan
- `'Australia/Sydney'` - Sydney

Find your timezone: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones

### 4. Run Locally (Testing)
```bash
python reminder_bot.py
```

## Deploying to Run 24/7

Since you need it to run even when your laptop is off, here are free hosting options:

### Option 1: Render.com (Recommended - Free)

1. Create account at https://render.com
2. Create a new "Background Worker"
3. Connect your GitHub repo (or upload files)
4. Set environment variables:
   - `TELEGRAM_TOKEN`: your bot token
   - `CHAT_ID`: your chat ID
5. Build command: `pip install -r requirements.txt`
6. Start command: `python reminder_bot.py`

### Option 2: Railway.app (Free tier available)

1. Create account at https://railway.app
2. Create new project from GitHub or upload
3. Add environment variables
4. Deploy

### Option 3: PythonAnywhere (Free tier)

1. Create account at https://www.pythonanywhere.com
2. Upload files
3. Set up an "Always-on task"

### Option 4: Fly.io (Free tier)

1. Install flyctl: https://fly.io/docs/hands-on/install-flyctl/
2. Run: `fly launch`
3. Deploy: `fly deploy`

## Data Storage

Ratings are stored in `daily_ratings.csv` with format:
```
Date,Timestamp,Rating
2025-11-04,2025-11-04 17:30:45,8
2025-11-05,2025-11-05 17:15:22,7
```

## Usage

1. Bot sends reminder at 5 PM daily
2. Friend replies with a number 1-10
3. Bot confirms and saves the rating
4. Data accumulates in CSV file for analysis

## Troubleshooting

**Bot doesn't respond:**
- Check that CHAT_ID is correct
- Make sure your friend started a chat with the bot first

**Wrong timezone:**
- Update the TIMEZONE variable in the script

**Need to test immediately:**
Add this line in the main() function to send a test message:
```python
asyncio.run(application.bot.send_message(chat_id=CHAT_ID, text="Test message"))
```
