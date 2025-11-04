import os
import csv
from datetime import datetime, time
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import pytz

# Configuration
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN', 'YOUR_BOT_TOKEN_HERE')
CHAT_ID = os.environ.get('CHAT_ID', 'YOUR_CHAT_ID_HERE')
CSV_FILE = 'daily_ratings.csv'
REMINDER_TIME = time(22, 23)  # 5 PM
TIMEZONE = pytz.timezone('Europe/Berlin')  # Adjust to your timezone

# Initialize CSV file
def init_csv():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Date', 'Timestamp', 'Rating'])

# Save rating to CSV
def save_rating(rating):
    now = datetime.now(TIMEZONE)
    with open(CSV_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([now.strftime('%Y-%m-%d'), now.strftime('%Y-%m-%d %H:%M:%S'), rating])

# Send daily reminder
async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=CHAT_ID,
        text="🌟 Time to rate today! How would you rate today on a scale of 1-10?"
    )

# Handle incoming messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Only respond to messages from the specific chat
    if str(update.effective_chat.id) != CHAT_ID:
        return
    
    text = update.message.text.strip()
    
    # Check if it's a valid rating (1-10)
    try:
        rating = int(text)
        if 1 <= rating <= 10:
            save_rating(rating)
            await update.message.reply_text(
                f"✅ Thanks! Your rating of {rating}/10 has been recorded for {datetime.now(TIMEZONE).strftime('%Y-%m-%d')}."
            )
        else:
            await update.message.reply_text(
                "❌ Please send a number between 1 and 10."
            )
    except ValueError:
        # Not a number, ignore or send help message
        pass

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Daily Rating Bot is active!\n\n"
        "I'll remind you every day at 5 PM to rate your day.\n"
        "Just reply with a number from 1 to 10.\n\n"
        "Commands:\n"
        "/download - Get your ratings data as a CSV file"
    )

# Download command - sends the CSV file
async def download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Only respond to the specific chat
    if str(update.effective_chat.id) != CHAT_ID:
        return
    
    # Check if CSV file exists
    if not os.path.exists(CSV_FILE):
        await update.message.reply_text("📭 No data available yet. Start rating your days first!")
        return
    
    # Send the CSV file
    try:
        with open(CSV_FILE, 'rb') as f:
            await update.message.reply_document(
                document=f,
                filename=f'daily_ratings_{datetime.now(TIMEZONE).strftime("%Y%m%d")}.csv',
                caption=f"📊 Your daily ratings data (downloaded on {datetime.now(TIMEZONE).strftime('%Y-%m-%d %H:%M')})"
            )
    except Exception as e:
        await update.message.reply_text(f"❌ Error sending file: {str(e)}")

# Setup scheduled job
def setup_scheduler(application):
    job_queue = application.job_queue
    # Schedule daily reminder at 5 PM
    job_queue.run_daily(
        send_reminder,
        time=REMINDER_TIME,
        days=(0, 1, 2, 3, 4, 5, 6),  # All days of the week
        chat_id=CHAT_ID,
        name='daily_reminder',
        data=None
    )

def main():
    # Initialize CSV
    init_csv()
    
    # Create application
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("download", download))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Setup scheduler
    setup_scheduler(application)
    
    print(f"Bot started! Daily reminders will be sent at {REMINDER_TIME} {TIMEZONE}")
    print(f"Monitoring chat ID: {CHAT_ID}")
    
    # Run the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
