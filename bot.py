import os
import logging
import yt_dlp
import re
import ssl

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

# SSL context setup
try:
    ssl.create_default_context()
except ImportError:
    raise ImportError("SSL module is missing.")

# Logging setup
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Ensure download directory exists
if not os.path.exists("downloads"):
    os.makedirs("downloads")

# Token from environment
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN is missing from environment variables.")

# Store user URLs
user_choices = {}

# URL validation
def is_valid_url(url):
    regex = re.compile(r"^(https?://)?(www\.)?(youtube\.com|youtu\.be|facebook\.com|instagram\.com|twitter\.com|tiktok\.com)/")
    return bool(re.match(regex, url))

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome! Send me a public video URL to download.", reply_markup=None)

# Ask for quality (inline buttons only)
async def ask_quality(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    url = update.message.text.strip()

    if not is_valid_url(url):
        await update.message.reply_text("❌ Invalid URL. Try again with a proper video link.", reply_markup=None)
        return

    user_choices[chat_id] = {"url": url}

    keyboard = [
        [InlineKeyboardButton("High", callback_data='High')],
        [InlineKeyboardButton("Medium", callback_data='Medium')],
        [InlineKeyboardButton("Low", callback_data='Low')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📌 Choose video quality:", reply_markup=reply_markup)

# Download handler
async def download_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    quality = query.data
    url = user_choices.get(chat_id, {}).get("url")

    if not url:
        await query.edit_message_text("❌ No video URL found. Please send it again.")
        return

    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_VIDEO)

    quality_formats = {
        "High": "bestvideo[height<=1080]+bestaudio/best",
        "Medium": "bestvideo[height<=720]+bestaudio/best",
        "Low": "bestvideo[height<=480]+bestaudio/best"
    }

    options = {
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'noplaylist': True,
        'merge_output_format': 'mp4',
        'restrictfilenames': True,
        'format': quality_formats.get(quality, "best"),
        'sanitize_filename': True
    }

    if "youtube.com" in url or "youtu.be" in url:
        cookie_file = "youtube_cookies.txt"
        if os.path.exists(cookie_file):
            options["cookiefile"] = cookie_file
        else:
            await query.edit_message_text(
                "⚠ YouTube requires login cookies.\n"
                "Please upload a `youtube_cookies.txt` file.\n"
                "Guide: https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp"
            )
            return

    try:
        await query.edit_message_text("📥 Downloading your video...")

        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)

        safe_path = os.path.join("downloads", os.path.basename(file_path))

        try:
            await context.bot.send_video(chat_id=chat_id, video=open(safe_path, "rb"))
            await context.bot.send_message(chat_id=chat_id, text="✅ Done! Send another URL.", reply_markup=None)
        finally:
            if os.path.exists(safe_path):
                os.remove(safe_path)

    except yt_dlp.DownloadError as e:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ Error: {str(e)}", reply_markup=None)
    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"⚠ Unexpected error: {str(e)}", reply_markup=None)

# Main function
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ask_quality))
    app.add_handler(CallbackQueryHandler(download_media))

    print("🚀 Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
