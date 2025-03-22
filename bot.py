import os
import logging
import yt_dlp
import re
import ssl
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

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

def is_valid_url(url):
    regex = re.compile(
        r"^(https?://)?(www\.)?"
        r"(youtube\.com|youtu\.be|facebook\.com|instagram\.com|twitter\.com|tiktok\.com)/"
    )
    return bool(re.match(regex, url))

# ✅ Fetch video information
async def fetch_video_info(url):
    options = {'quiet': True, 'skip_download': True}
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=False)
        return info.get('title', 'Unknown Title'), info.get('formats', [])

# ✅ Ask user for video quality with buttons
async def ask_quality(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    url = update.message.text.strip()

    if not is_valid_url(url):
        await update.message.reply_text("❌ Invalid URL! Please send a valid video link.")
        return

    title, formats = await fetch_video_info(url)
    user_choices[chat_id] = {"url": url}

    buttons = [[InlineKeyboardButton(f"{f['format_note']} ({f['ext']})", callback_data=f['format_id'])] for f in formats if 'format_note' in f]
    reply_markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text(f"🎥 *{title}*\n\n📌 Choose video quality:", reply_markup=reply_markup, parse_mode="Markdown")

async def download_media(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    format_id = query.data
    url = user_choices.get(chat_id, {}).get("url")

    if not url:
        await query.message.reply_text("❌ Error: URL not found. Please send a valid link.")
        return

    options = {
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'noplaylist': True,
        'format': format_id,
    }

    try:
        await query.message.reply_text("📥 Downloading, please wait...")
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
        safe_filepath = os.path.join("downloads", os.path.basename(file_path))
        try:
            await context.bot.send_video(chat_id=chat_id, video=open(safe_filepath, "rb"))
            await query.message.reply_text("✅ Download completed! Send another link.")
        finally:
            if os.path.exists(safe_filepath):
                os.remove(safe_filepath)
    except yt_dlp.DownloadError as e:
        await query.message.reply_text(f"❌ Download Error: {str(e)}")
    except Exception as e:
        await query.message.reply_text(f"⚠ Unexpected Error: {str(e)}")

# ✅ Start Command
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("👋 Welcome to MediaFetchBot!\nPaste a public video URL to download.")

# ✅ Main Function
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ask_quality))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_media))
    print("🚀 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
