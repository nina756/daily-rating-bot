import os
import csv
from datetime import datetime, time
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import pytz

# Configuration
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN', 'YOUR_BOT_TOKEN_HERE')
ADMIN_CHAT_ID = os.environ.get('ADMIN_CHAT_ID', 'YOUR_ADMIN_CHAT_ID')  # Your personal chat ID
CSV_FILE = 'daily_ratings.csv'
USERS_FILE = 'registered_users.txt'
REMINDER_TIME = time(17, 00)  # 10:17 PM
TIMEZONE = pytz.timezone('Europe/Berlin')  # Adjust to your timezone

# Initialize CSV file with chat_id column
def init_csv():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Date', 'Timestamp', 'Chat_ID', 'Rating'])

# Initialize users file
def init_users_file():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w') as f:
            pass  # Create empty file

# Load registered users
def load_users():
    if not os.path.exists(USERS_FILE):
        return set()
    with open(USERS_FILE, 'r') as f:
        return set(line.strip() for line in f if line.strip())

# Add new user
def add_user(chat_id):
    users = load_users()
    chat_id_str = str(chat_id)
    if chat_id_str not in users:
        with open(USERS_FILE, 'a') as f:
            f.write(f"{chat_id_str}\n")
        return True
    return False

# Save rating to CSV
def save_rating(chat_id, rating):
    now = datetime.now(TIMEZONE)
    with open(CSV_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            now.strftime('%Y-%m-%d'), 
            now.strftime('%Y-%m-%d %H:%M:%S'), 
            chat_id,
            rating
        ])

# Send daily reminder to all registered users
async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    users = load_users()
    for chat_id in users:
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text="🌟 Time to rate today! How would you rate today on a scale of 1-10?"
            )
        except Exception as e:
            print(f"Error sending reminder to {chat_id}: {e}")

# Handle incoming messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text.strip()
    
    # Check if it's a valid rating (1-10)
    try:
        rating = int(text)
        if 1 <= rating <= 10:
            # Register user if not already registered
            if add_user(chat_id):
                await update.message.reply_text(
                    "🎉 Welcome! You've been registered for daily reminders at 18:00 PM Berlin time."
                )
            
            save_rating(chat_id, rating)
            await update.message.reply_text(
                f"✅ Thanks! Your rating of {rating}/10 has been recorded for {datetime.now(TIMEZONE).strftime('%Y-%m-%d')}."
            )
        else:
            await update.message.reply_text(
                "❌ Please send a number between 1 and 10."
            )
    except ValueError:
        # Not a number, ignore
        pass

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    # Log the chat ID
    print(f"User started bot - Chat ID: {chat_id}, Username: {update.effective_user.username}, Name: {update.effective_user.first_name}")
    
    # Register the user
    is_new = add_user(chat_id)
    
    welcome_msg = "👋 Daily Rating Bot is active!\n\n"
    if is_new:
        welcome_msg += "🎉 You've been registered for daily reminders!\n\n"
    
    welcome_msg += (
        f"I'll remind you every day at {REMINDER_TIME.strftime('%I:%M %p')} (Berlin time) to rate your day.\n"
        "Just reply with a number from 1 to 10.\n\n"
        "Commands:\n"
        "/download - Get your ratings data as a CSV file\n"
        "/stats - View your rating statistics\n"
        "/stop - Stop receiving daily reminders"
    )
    
    await update.message.reply_text(welcome_msg)

# Download command - sends the CSV file with user's data
async def download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    # Check if CSV file exists
    if not os.path.exists(CSV_FILE):
        await update.message.reply_text("📭 No data available yet. Start rating your days first!")
        return
    
    # Create a filtered CSV with only this user's data
    try:
        temp_file = f'temp_{chat_id}.csv'
        with open(CSV_FILE, 'r', newline='') as infile, open(temp_file, 'w', newline='') as outfile:
            reader = csv.reader(infile)
            writer = csv.writer(outfile)
            
            # Write header
            header = next(reader)
            writer.writerow(header)
            
            # Write only rows for this user
            for row in reader:
                if len(row) >= 3 and row[2] == str(chat_id):
                    writer.writerow(row)
        
        # Send the filtered CSV file
        with open(temp_file, 'rb') as f:
            await update.message.reply_document(
                document=f,
                filename=f'my_daily_ratings_{datetime.now(TIMEZONE).strftime("%Y%m%d")}.csv',
                caption=f"📊 Your daily ratings data (downloaded on {datetime.now(TIMEZONE).strftime('%Y-%m-%d %H:%M')})"
            )
        
        # Clean up temp file
        os.remove(temp_file)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error sending file: {str(e)}")

# Stats command - show user statistics
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    if not os.path.exists(CSV_FILE):
        await update.message.reply_text("📭 No data available yet. Start rating your days first!")
        return
    
    try:
        ratings = []
        with open(CSV_FILE, 'r', newline='') as f:
            reader = csv.reader(f)
            next(reader)  # Skip header
            for row in reader:
                if len(row) >= 4 and row[2] == str(chat_id):
                    ratings.append(int(row[3]))
        
        if not ratings:
            await update.message.reply_text("📭 No ratings recorded yet. Send a number from 1-10 to start!")
            return
        
        avg_rating = sum(ratings) / len(ratings)
        max_rating = max(ratings)
        min_rating = min(ratings)
        
        stats_msg = (
            f"📊 Your Rating Statistics:\n\n"
            f"Total ratings: {len(ratings)}\n"
            f"Average: {avg_rating:.1f}/10\n"
            f"Highest: {max_rating}/10\n"
            f"Lowest: {min_rating}/10"
        )
        
        await update.message.reply_text(stats_msg)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error calculating stats: {str(e)}")

# Stop command - unregister user
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    users = load_users()
    
    if chat_id in users:
        users.remove(chat_id)
        with open(USERS_FILE, 'w') as f:
            for user in users:
                f.write(f"{user}\n")
        await update.message.reply_text(
            "👋 You've been unregistered from daily reminders.\n"
            "Your rating history is preserved. Use /start to register again."
        )
    else:
        await update.message.reply_text("You're not currently registered for reminders.")

# Admin command - download full dataset (admin only)
async def admin_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    
    # Check if user is admin
    if chat_id != ADMIN_CHAT_ID:
        await update.message.reply_text("❌ This command is only available to the admin.")
        return
    
    # Check if CSV file exists
    if not os.path.exists(CSV_FILE):
        await update.message.reply_text("📭 No data available yet.")
        return
    
    try:
        # Send the full CSV file
        with open(CSV_FILE, 'rb') as f:
            await update.message.reply_document(
                document=f,
                filename=f'all_daily_ratings_{datetime.now(TIMEZONE).strftime("%Y%m%d")}.csv',
                caption=f"📊 Full dataset - All users (downloaded on {datetime.now(TIMEZONE).strftime('%Y-%m-%d %H:%M')})"
            )
        
        # Also send the users file
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    filename=f'registered_users_{datetime.now(TIMEZONE).strftime("%Y%m%d")}.txt',
                    caption=f"👥 Registered users list"
                )
    except Exception as e:
        await update.message.reply_text(f"❌ Error sending files: {str(e)}")

# Admin command - view registered users (admin only)
async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    
    # Check if user is admin
    if chat_id != ADMIN_CHAT_ID:
        await update.message.reply_text("❌ This command is only available to the admin.")
        return
    
    users = load_users()
    
    if not users:
        await update.message.reply_text("📭 No registered users yet.")
        return
    
    user_list = "\n".join(f"• {user}" for user in sorted(users))
    await update.message.reply_text(
        f"👥 Registered Users ({len(users)} total):\n\n{user_list}"
    )

# Admin command - manually add user(s) (admin only)
async def admin_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    
    # Check if user is admin
    if chat_id != ADMIN_CHAT_ID:
        await update.message.reply_text("❌ This command is only available to the admin.")
        return
    
    # Check if chat IDs were provided
    if not context.args:
        await update.message.reply_text(
            "Usage: /adminadd <chat_id1> <chat_id2> ...\n\n"
            "Example: /adminadd 123456789 987654321\n\n"
            "Add one or more chat IDs to the registered users list."
        )
        return
    
    added = []
    already_exists = []
    invalid = []
    
    for user_id in context.args:
        # Validate that it's a number
        try:
            int(user_id)  # Just check if it's a valid number
            if add_user(user_id):
                added.append(user_id)
            else:
                already_exists.append(user_id)
        except ValueError:
            invalid.append(user_id)
    
    # Build response message
    response = "📝 Add Users Result:\n\n"
    
    if added:
        response += f"✅ Added ({len(added)}):\n"
        response += "\n".join(f"  • {uid}" for uid in added) + "\n\n"
    
    if already_exists:
        response += f"ℹ️ Already registered ({len(already_exists)}):\n"
        response += "\n".join(f"  • {uid}" for uid in already_exists) + "\n\n"
    
    if invalid:
        response += f"❌ Invalid chat IDs ({len(invalid)}):\n"
        response += "\n".join(f"  • {uid}" for uid in invalid) + "\n\n"
    
    response += f"Total registered users: {len(load_users())}"
    
    await update.message.reply_text(response)

# Admin command - remove user(s) (admin only)
async def admin_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    
    # Check if user is admin
    if chat_id != ADMIN_CHAT_ID:
        await update.message.reply_text("❌ This command is only available to the admin.")
        return
    
    # Check if chat IDs were provided
    if not context.args:
        await update.message.reply_text(
            "Usage: /adminremove <chat_id1> <chat_id2> ...\n\n"
            "Example: /adminremove 123456789 987654321\n\n"
            "Remove one or more chat IDs from the registered users list."
        )
        return
    
    users = load_users()
    removed = []
    not_found = []
    
    for user_id in context.args:
        if user_id in users:
            users.remove(user_id)
            removed.append(user_id)
        else:
            not_found.append(user_id)
    
    # Save updated users list
    if removed:
        with open(USERS_FILE, 'w') as f:
            for user in users:
                f.write(f"{user}\n")
    
    # Build response message
    response = "🗑️ Remove Users Result:\n\n"
    
    if removed:
        response += f"✅ Removed ({len(removed)}):\n"
        response += "\n".join(f"  • {uid}" for uid in removed) + "\n\n"
    
    if not_found:
        response += f"ℹ️ Not found ({len(not_found)}):\n"
        response += "\n".join(f"  • {uid}" for uid in not_found) + "\n\n"
    
    response += f"Total registered users: {len(load_users())}"
    
    await update.message.reply_text(response)

# Setup scheduled job
def setup_scheduler(application):
    job_queue = application.job_queue
    # Schedule daily reminder at specified time
    job_queue.run_daily(
        send_reminder,
        time=REMINDER_TIME,
        days=(0, 1, 2, 3, 4, 5, 6),  # All days of the week
        name='daily_reminder',
        data=None
    )

def main():
    # Initialize files
    init_csv()
    init_users_file()
    
    # Create application
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("download", download))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("admindownload", admin_download))
    application.add_handler(CommandHandler("adminusers", admin_users))
    application.add_handler(CommandHandler("adminadd", admin_add))
    application.add_handler(CommandHandler("adminremove", admin_remove))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Setup scheduler
    setup_scheduler(application)
    
    print(f"Bot started! Daily reminders will be sent at {REMINDER_TIME} {TIMEZONE}")
    print(f"Users will be automatically registered when they interact with the bot")
    print(f"Current registered users: {len(load_users())}")
    
    # Run the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
