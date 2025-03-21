import os
import logging
import yt_dlp
import re
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# ✅ Logging Setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# ✅ Ensure 'downloads' directory exists
if not os.path.exists("downloads"):
    os.makedirs("downloads")

# ✅ Function to ask user which platform they want
async def ask_platform(update: Update, context: CallbackContext):
    keyboard = [["YouTube", "Facebook"], ["Instagram", "Twitter"], ["TikTok"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("📌 Choose the platform:", reply_markup=reply_markup)

# ✅ Start Command
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("👋 Welcome to MediaFetchBot!\nPaste a public video URL to download.")
    await ask_platform(update, context)

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
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'noplaylist': True,
        'merge_output_format': 'mp4',
        'restrictfilenames': True,
        'format': quality_formats.get(quality, "best"),
    }

    # Handle YouTube cookies
    if "youtube.com" in url or "youtu.be" in url:
        cookie_file = "youtube_cookies.txt"
        if os.path.exists(cookie_file):
            options["cookiefile"] = cookie_file
        else:
            await update.message.reply_text(
                "⚠️ YouTube requires authentication, but no cookie file found. "
                "Please provide cookies via youtube_cookies.txt. See: "
                "https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp"
            )
            return ConversationHandler.END

    try:
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
        await update.message.reply_text(f"⚠️ Unexpected Error: {str(e)}")

    return ConversationHandler.END
# ✅ Handle User Messages (URL Input)
async def handle_message(update: Update, context: CallbackContext):
    url = update.message.text
    chat_id = update.message.chat_id
    await context.bot.send_message(chat_id=chat_id, text="📥 Downloading, please wait...")
    await download_media(url, chat_id, context)

# ✅ Main Function
def main():
    TOKEN = "BOT_TOKEN"  # ⬅️ Replace with your Telegram Bot Token

    app = Application.builder().token(TOKEN).build()

    # ✅ Command Handlers
    app.add_handler(CommandHandler("start", start))

    # ✅ Message Handler (URLs)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # ✅ Start Bot
    print("🚀 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
