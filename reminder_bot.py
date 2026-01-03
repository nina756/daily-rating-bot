import os
import csv
from datetime import datetime, time
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
import pytz

# =========================
# Configuration
# =========================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "YOUR_ADMIN_CHAT_ID")  # as string
CSV_FILE = "daily_ratings.csv"
USERS_FILE = "registered_users.txt"

TIMEZONE = pytz.timezone("Europe/Berlin")

# Daily reminder (main ping) and deadline reminder (only if missing)
FIRST_REMINDER_TIME = time(18, 0)       # 18:00 Berlin time (change as you like)
DEADLINE_REMINDER_TIME = time(22, 30)   # 22:30 Berlin time (10:30pm)


# =========================
# File init / persistence
# =========================
def init_csv():
    """Create CSV with header if missing."""
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Date", "Timestamp", "Chat_ID", "Rating"])


def init_users_file():
    """Create users file if missing."""
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            f.write("")


def load_users() -> set[str]:
    """Load registered users as a set of chat_id strings."""
    if not os.path.exists(USERS_FILE):
        return set()
    with open(USERS_FILE, "r") as f:
        return {line.strip() for line in f if line.strip()}


def save_users(users: set[str]) -> None:
    """Persist registered users set back to file."""
    with open(USERS_FILE, "w") as f:
        for uid in sorted(users):
            f.write(f"{uid}\n")


def add_user(chat_id) -> bool:
    """Add chat_id to registered users if missing. Returns True if added."""
    chat_id_str = str(chat_id)
    users = load_users()
    if chat_id_str in users:
        return False
    with open(USERS_FILE, "a") as f:
        f.write(f"{chat_id_str}\n")
    return True


# =========================
# Ratings logic
# =========================
def now_berlin() -> datetime:
    return datetime.now(TIMEZONE)


def today_str() -> str:
    return now_berlin().strftime("%Y-%m-%d")


def save_rating(chat_id, rating: int) -> None:
    """Append a rating row to CSV."""
    now = now_berlin()
    with open(CSV_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                now.strftime("%Y-%m-%d"),
                now.strftime("%Y-%m-%d %H:%M:%S"),
                str(chat_id),
                str(rating),
            ]
        )


def get_users_who_rated_today() -> set[str]:
    """
    Read CSV once and return set of Chat_IDs that have at least one rating today.
    This is much faster than scanning the CSV once per user.
    """
    rated = set()
    if not os.path.exists(CSV_FILE):
        return rated

    t = today_str()
    try:
        with open(CSV_FILE, "r", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("Date") == t and row.get("Chat_ID"):
                    rated.add(row["Chat_ID"])
    except Exception as e:
        print(f"Error reading CSV in get_users_who_rated_today: {e}")

    return rated


# =========================
# Scheduled jobs
# =========================
async def send_daily_reminder(context: ContextTypes.DEFAULT_TYPE):
    users = load_users()
    for chat_id in users:
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text="🌟 Time to rate today! How would you rate today on a scale of 1–10?",
            )
        except Exception as e:
            print(f"Error sending daily reminder to {chat_id}: {e}")


async def send_deadline_reminder(context: ContextTypes.DEFAULT_TYPE):
    """
    At 22:30 Berlin time, remind ONLY users who haven't submitted a rating today.
    """
    users = load_users()
    rated_today = get_users_who_rated_today()

    for chat_id in users:
        try:
            if str(chat_id) not in rated_today:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="⏰ Reminder: you haven’t submitted today’s rating yet. Reply with a number from 1–10.",
                )
        except Exception as e:
            print(f"Error sending deadline reminder to {chat_id}: {e}")


def setup_scheduler(application: Application):
    job_queue = application.job_queue

    job_queue.run_daily(
        send_daily_reminder,
        time=FIRST_REMINDER_TIME,
        days=(0, 1, 2, 3, 4, 5, 6),
        name="daily_reminder",
    )

    job_queue.run_daily(
        send_deadline_reminder,
        time=DEADLINE_REMINDER_TIME,
        days=(0, 1, 2, 3, 4, 5, 6),
        name="deadline_reminder",
    )


# =========================
# Handlers
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    print(
        f"User started bot - Chat ID: {chat_id}, "
        f"Username: {update.effective_user.username}, "
        f"Name: {update.effective_user.first_name}"
    )

    is_new = add_user(chat_id)

    welcome_msg = "👋 Daily Rating Bot is active!\n\n"
    if is_new:
        welcome_msg += "🎉 You've been registered for daily reminders!\n\n"

    welcome_msg += (
        f"I'll remind you every day at {FIRST_REMINDER_TIME.strftime('%H:%M')} (Berlin time) to rate your day.\n"
        f"If you haven’t rated by {DEADLINE_REMINDER_TIME.strftime('%H:%M')}, I’ll send another reminder.\n\n"
        "Just reply with a number from 1 to 10.\n\n"
        "Commands:\n"
        "/download - Get your ratings data as a CSV file\n"
        "/stats - View your rating statistics\n"
        "/stop - Stop receiving daily reminders"
    )

    await update.message.reply_text(welcome_msg)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    chat_id = update.effective_chat.id
    text = update.message.text.strip()

    # Only process plain number messages as ratings
    try:
        rating = int(text)
    except ValueError:
        return

    if not (1 <= rating <= 10):
        await update.message.reply_text("❌ Please send a number between 1 and 10.")
        return

    # Auto-register on first interaction
    is_new = add_user(chat_id)
    if is_new:
        await update.message.reply_text(
            f"🎉 Welcome! You've been registered for daily reminders at {FIRST_REMINDER_TIME.strftime('%H:%M')} Berlin time."
        )

    save_rating(chat_id, rating)
    await update.message.reply_text(
        f"✅ Thanks! Your rating of {rating}/10 has been recorded for {today_str()}."
    )


async def download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)

    if not os.path.exists(CSV_FILE):
        await update.message.reply_text("📭 No data available yet. Start rating your days first!")
        return

    temp_file = f"temp_{chat_id}.csv"

    try:
        with open(CSV_FILE, "r", newline="") as infile, open(temp_file, "w", newline="") as outfile:
            reader = csv.DictReader(infile)
            fieldnames = reader.fieldnames or ["Date", "Timestamp", "Chat_ID", "Rating"]
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()

            for row in reader:
                if row.get("Chat_ID") == chat_id:
                    writer.writerow(row)

        with open(temp_file, "rb") as f:
            await update.message.reply_document(
                document=f,
                filename=f"my_daily_ratings_{now_berlin().strftime('%Y%m%d')}.csv",
                caption=f"📊 Your daily ratings data (downloaded on {now_berlin().strftime('%Y-%m-%d %H:%M')})",
            )

    except Exception as e:
        await update.message.reply_text(f"❌ Error sending file: {str(e)}")
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)

    if not os.path.exists(CSV_FILE):
        await update.message.reply_text("📭 No data available yet. Start rating your days first!")
        return

    ratings: list[int] = []

    try:
        with open(CSV_FILE, "r", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("Chat_ID") == chat_id and row.get("Rating"):
                    try:
                        ratings.append(int(row["Rating"]))
                    except ValueError:
                        continue

        if not ratings:
            await update.message.reply_text("📭 No ratings recorded yet. Send a number from 1–10 to start!")
            return

        avg_rating = sum(ratings) / len(ratings)
        max_rating = max(ratings)
        min_rating = min(ratings)

        stats_msg = (
            "📊 Your Rating Statistics:\n\n"
            f"Total ratings: {len(ratings)}\n"
            f"Average: {avg_rating:.1f}/10\n"
            f"Highest: {max_rating}/10\n"
            f"Lowest: {min_rating}/10"
        )

        await update.message.reply_text(stats_msg)

    except Exception as e:
        await update.message.reply_text(f"❌ Error calculating stats: {str(e)}")


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    users = load_users()

    if chat_id not in users:
        await update.message.reply_text("You're not currently registered for reminders.")
        return

    users.remove(chat_id)
    save_users(users)

    await update.message.reply_text(
        "👋 You've been unregistered from daily reminders.\n"
        "Your rating history is preserved. Use /start to register again."
    )


# =========================
# Admin handlers
# =========================
def is_admin(update: Update) -> bool:
    return str(update.effective_chat.id) == str(ADMIN_CHAT_ID)


async def admin_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("❌ This command is only available to the admin.")
        return

    if not os.path.exists(CSV_FILE):
        await update.message.reply_text("📭 No data available yet.")
        return

    try:
        with open(CSV_FILE, "rb") as f:
            await update.message.reply_document(
                document=f,
                filename=f"all_daily_ratings_{now_berlin().strftime('%Y%m%d')}.csv",
                caption=f"📊 Full dataset - All users (downloaded on {now_berlin().strftime('%Y-%m-%d %H:%M')})",
            )

        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, "rb") as f:
                await update.message.reply_document(
                    document=f,
                    filename=f"registered_users_{now_berlin().strftime('%Y%m%d')}.txt",
                    caption="👥 Registered users list",
                )
    except Exception as e:
        await update.message.reply_text(f"❌ Error sending files: {str(e)}")


async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("❌ This command is only available to the admin.")
        return

    users = load_users()
    if not users:
        await update.message.reply_text("📭 No registered users yet.")
        return

    user_list = "\n".join(f"• {uid}" for uid in sorted(users))
    await update.message.reply_text(f"👥 Registered Users ({len(users)} total):\n\n{user_list}")


async def admin_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("❌ This command is only available to the admin.")
        return

    if not context.args:
        await update.message.reply_text(
            "Usage: /adminadd <chat_id1> <chat_id2> ...\n\n"
            "Example: /adminadd 123456789 987654321\n\n"
            "Add one or more chat IDs to the registered users list."
        )
        return

    added, already_exists, invalid = [], [], []

    for user_id in context.args:
        try:
            int(user_id)
            if add_user(user_id):
                added.append(user_id)
            else:
                already_exists.append(user_id)
        except ValueError:
            invalid.append(user_id)

    response = "📝 Add Users Result:\n\n"
    if added:
        response += f"✅ Added ({len(added)}):\n" + "\n".join(f"  • {uid}" for uid in added) + "\n\n"
    if already_exists:
        response += f"ℹ️ Already registered ({len(already_exists)}):\n" + "\n".join(
            f"  • {uid}" for uid in already_exists
        ) + "\n\n"
    if invalid:
        response += f"❌ Invalid chat IDs ({len(invalid)}):\n" + "\n".join(f"  • {uid}" for uid in invalid) + "\n\n"

    response += f"Total registered users: {len(load_users())}"
    await update.message.reply_text(response)


async def admin_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("❌ This command is only available to the admin.")
        return

    if not context.args:
        await update.message.reply_text(
            "Usage: /adminremove <chat_id1> <chat_id2> ...\n\n"
            "Example: /adminremove 123456789 987654321\n\n"
            "Remove one or more chat IDs from the registered users list."
        )
        return

    users = load_users()
    removed, not_found = [], []

    for user_id in context.args:
        if user_id in users:
            users.remove(user_id)
            removed.append(user_id)
        else:
            not_found.append(user_id)

    if removed:
        save_users(users)

    response = "🗑️ Remove Users Result:\n\n"
    if removed:
        response += f"✅ Removed ({len(removed)}):\n" + "\n".join(f"  • {uid}" for uid in removed) + "\n\n"
    if not_found:
        response += f"ℹ️ Not found ({len(not_found)}):\n" + "\n".join(f"  • {uid}" for uid in not_found) + "\n\n"

    response += f"Total registered users: {len(load_users())}"
    await update.message.reply_text(response)


# =========================
# Main
# =========================
def main():
    init_csv()
    init_users_file()

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("download", download))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("stop", stop))

    application.add_handler(CommandHandler("admindownload", admin_download))
    application.add_handler(CommandHandler("adminusers", admin_users))
    application.add_handler(CommandHandler("adminadd", admin_add))
    application.add_handler(CommandHandler("adminremove", admin_remove))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    setup_scheduler(application)

    print(f"Bot started! Daily reminders at {FIRST_REMINDER_TIME} ({TIMEZONE})")
    print(f"Missing-rating reminders at {DEADLINE_REMINDER_TIME} ({TIMEZONE})")
    print("Users will be automatically registered when they interact with the bot")
    print(f"Current registered users: {len(load_users())}")

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

