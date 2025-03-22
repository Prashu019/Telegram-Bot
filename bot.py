import os
import logging
import yt_dlp
import re
import ssl
import hashlib
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler

# ✅ Ensure SSL is available
try:
    ssl.create_default_context()
except ImportError:
    raise ImportError("❌ SSL module is missing! Ensure your Python installation includes SSL support.")

# ✅ Logging Setup
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ✅ Ensure 'downloads' directory exists
if not os.path.exists("downloads"):
    os.makedirs("downloads")

# ✅ Load Telegram Bot Token from Environment Variables
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ BOT_TOKEN is missing! Set it in Railway environment variables.")

# ✅ Dictionary to store user choices
user_choices = {}

# ✅ Function to validate a URL
def is_valid_url(url):
    regex = re.compile(
        r"^(https?://)?(www\.)?"
        r"(youtube\.com|youtu\.be|facebook\.com|instagram\.com|twitter\.com|tiktok\.com)/"
    )
    return bool(re.match(regex, url))

# ✅ Ask user for video quality
async def ask_quality(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    url = update.message.text.strip()

    if not is_valid_url(url):
        await update.message.reply_text("❌ Invalid URL! Please send a valid video link.")
        return ConversationHandler.END

    user_choices[chat_id] = {"url": url}

    keyboard = [["High", "Medium", "Low"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("📌 Choose video quality:", reply_markup=reply_markup)

    return 1  # Move to next step in conversation

# ✅ Download and send video
async def download_media(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    quality = update.message.text
    url = user_choices.get(chat_id, {}).get("url")

    if not url:
        await update.message.reply_text("❌ Error: URL not found. Please send a valid link.")
        return ConversationHandler.END

    quality_formats = {
        "High": "bestvideo[height<=1080]+bestaudio/best",
        "Medium": "bestvideo[height<=720]+bestaudio/best",
        "Low": "bestvideo[height<=480]+bestaudio/best"
    }

    options = {
        'outtmpl': 'downloads/%(id)s.%(ext)s',  # Shorter filename using video ID
        'noplaylist': True,
        'merge_output_format': 'mp4',
        'restrictfilenames': True,
        'format': quality_formats.get(quality, "best"),
        'sanitize_filename': True  # Ensure safe filenames
    }

    # Handle YouTube authentication with cookies
    if "youtube.com" in url or "youtu.be" in url:
        cookie_file = "youtube_cookies.txt"
        if os.path.exists(cookie_file):
            options["cookiefile"] = cookie_file
        else:
            await update.message.reply_text(
                "⚠ YouTube requires authentication, but no cookie file found. "
                "Please provide cookies via youtube_cookies.txt. See: "
                "https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp"
            )
            return ConversationHandler.END

    try:
        await update.message.reply_text("📥 Downloading, please wait...")

        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)

        safe_filepath = os.path.join("downloads", os.path.basename(file_path))

        try:
            await context.bot.send_video(chat_id=chat_id, video=open(safe_filepath, "rb"))
            await update.message.reply_text("✅ Download completed! Send another link.")
        finally:
            if os.path.exists(safe_filepath):
                os.remove(safe_filepath)

    except yt_dlp.DownloadError as e:
        await update.message.reply_text(f"❌ Download Error: {str(e)}")
    except Exception as e:
        await update.message.reply_text(f"⚠ Unexpected Error: {str(e)}")

    return ConversationHandler.END

# ✅ Start Command
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("👋 Welcome to MediaFetchBot!\nPaste a public video URL to download.")

# ✅ Main Function
def main():
    app = Application.builder().token(TOKEN).build()

    # ✅ Conversation Handler for Step-by-Step Process
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, ask_quality)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, download_media)],
        },
        fallbacks=[],
    )

    # ✅ Command Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)

    # ✅ Start Bot
    print("🚀 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
