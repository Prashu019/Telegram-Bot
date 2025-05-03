import os
import logging
import yt_dlp
import re
import ssl
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatAction
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
    raise ValueError("❌ BOT_TOKEN is missing! Set it in your environment variables.")

# ✅ Dictionary to store user choices
user_choices = {}

# ✅ Function to validate a URL
def is_valid_url(url):
    regex = re.compile(
        r"^(https?://)?(www\.)?"
        r"(youtube\.com|youtu\.be|facebook\.com|instagram\.com|twitter\.com|tiktok\.com)/"
    )
    return bool(re.match(regex, url))


# ✅ Start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("ℹ️ Help", callback_data="help")],
        [InlineKeyboardButton("📋 Supported Sites", callback_data="sites")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👋 Welcome to MediaFetchBot!\nPaste a public video URL to begin.",
        reply_markup=reply_markup,
    )


# ✅ Handle plain video URLs
async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    url = update.message.text.strip()

    if not is_valid_url(url):
        await update.message.reply_text("❌ Invalid URL! Please send a valid video link.")
        return

    user_choices[chat_id] = {"url": url}

    keyboard = [
        [InlineKeyboardButton("High", callback_data="quality_High")],
        [InlineKeyboardButton("Medium", callback_data="quality_Medium")],
        [InlineKeyboardButton("Low", callback_data="quality_Low")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📌 Choose video quality:", reply_markup=reply_markup)


# ✅ Handle quality button clicks
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id

    if query.data.startswith("quality_"):
        quality = query.data.split("_")[1]
        url = user_choices.get(chat_id, {}).get("url")

        if not url:
            await query.edit_message_text("❌ Error: No URL found. Please send a new link.")
            return

        quality_formats = {
            "High": "bestvideo[height<=1080]+bestaudio/best",
            "Medium": "bestvideo[height<=720]+bestaudio/best",
            "Low": "bestvideo[height<=480]+bestaudio/best",
        }

        options = {
            'outtmpl': 'downloads/%(id)s.%(ext)s',
            'noplaylist': True,
            'merge_output_format': 'mp4',
            'restrictfilenames': True,
            'format': quality_formats.get(quality, "best"),
            'sanitize_filename': True,
        }

        if "youtube.com" in url or "youtu.be" in url:
            cookie_file = "youtube_cookies.txt"
            if os.path.exists(cookie_file):
                options["cookiefile"] = cookie_file
            else:
                await query.edit_message_text(
                    "⚠ YouTube requires authentication, but no cookie file found.\n"
                    "Upload `youtube_cookies.txt` for private or age-restricted content."
                )
                return

        try:
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_VIDEO)
            await query.edit_message_text("📥 Downloading, please wait...")

            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=True)
                file_path = ydl.prepare_filename(info)

            safe_filepath = os.path.join("downloads", os.path.basename(file_path))

            await context.bot.send_video(chat_id=chat_id, video=open(safe_filepath, "rb"))
            await context.bot.send_message(chat_id=chat_id, text="✅ Download completed! Send another link.")

            if os.path.exists(safe_filepath):
                os.remove(safe_filepath)

        except yt_dlp.DownloadError as e:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ Download Error: {str(e)}")
        except Exception as e:
            await context.bot.send_message(chat_id=chat_id, text=f"⚠ Unexpected Error: {str(e)}")

    elif query.data == "help":
        await query.edit_message_text(
            "ℹ️ Just paste a video link (YouTube, Facebook, Instagram, etc.), choose quality, and I'll download it!"
        )
    elif query.data == "sites":
        await query.edit_message_text(
            "✅ Supported platforms:\nYouTube, Facebook, Instagram, Twitter, TikTok (public videos only)."
        )


# ✅ Main Function
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))

    print("🚀 Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
