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

# ✅ Ensure SSL is available
try:
    ssl.create_default_context()
except ImportError:
    raise ImportError("❌ SSL module is missing! Ensure your Python installation includes SSL support.")

# ✅ Logging Setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# ✅ Ensure 'downloads' directory exists
if not os.path.exists("downloads"):
    os.makedirs("downloads")

# ✅ Load Telegram Bot Token from Environment Variables
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ BOT_TOKEN is missing! Set it in Railway environment variables.")

# ✅ Store user links temporarily
user_choices = {}

# ✅ Validate URL
def is_valid_url(url):
    regex = re.compile(
        r"^(https?://)?(www\.)?"
        r"(youtube\.com|youtu\.be|facebook\.com|instagram\.com|twitter\.com|tiktok\.com)/"
    )
    return bool(re.match(regex, url))

# ✅ Handle /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome to MediaFetchBot!\nPaste a public video URL to download.")

# ✅ Ask user for quality using inline buttons only
async def ask_quality(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    url = update.message.text.strip()

    if not is_valid_url(url):
        await update.message.reply_text("❌ Invalid URL! Please send a valid video link.")
        return

    user_choices[chat_id] = {"url": url}

    keyboard = [
        [InlineKeyboardButton("High", callback_data='High')],
        [InlineKeyboardButton("Medium", callback_data='Medium')],
        [InlineKeyboardButton("Low", callback_data='Low')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📌 Choose video quality:", reply_markup=reply_markup)

# ✅ Handle button press and download
async def download_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    quality = query.data
    url = user_choices.get(chat_id, {}).get("url")

    if not url:
        await query.edit_message_text("❌ Error: No video URL found. Please send it again.")
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

    # YouTube cookies
    if "youtube.com" in url or "youtu.be" in url:
        cookie_file = "youtube_cookies.txt"
        if os.path.exists(cookie_file):
            options["cookiefile"] = cookie_file
        else:
            await query.edit_message_text(
                "⚠ YouTube requires authentication, but no cookie file found.\n"
                "Please upload cookies as youtube_cookies.txt.\n"
                "See: https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp"
            )
            return

    try:
        await query.edit_message_text("📥 Downloading, please wait...")

        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)

        safe_filepath = os.path.join("downloads", os.path.basename(file_path))

        try:
            await context.bot.send_video(chat_id=chat_id, video=open(safe_filepath, "rb"))
            await context.bot.send_message(chat_id=chat_id, text="✅ Download completed! Send another link.")
        finally:
            if os.path.exists(safe_filepath):
                os.remove(safe_filepath)

    except yt_dlp.DownloadError as e:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ Download Error: {str(e)}")
    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"⚠ Unexpected Error: {str(e)}")

# ✅ Main function
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ask_quality))
    app.add_handler(CallbackQueryHandler(download_media))

    print("🚀 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
