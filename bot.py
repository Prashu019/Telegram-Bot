import os
import logging
import yt_dlp
import re
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler

# ✅ Logging Setup
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ✅ Ensure 'downloads' directory exists
if not os.path.exists("downloads"):
    os.makedirs("downloads")

# ✅ Load Telegram Bot Token from Environment Variables
TOKEN = "BOT_TOKEN"
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

def is_downloadable(url):
    """Returns True if the video is downloadable, False otherwise."""
    options = {
        "quiet": False,  # Show errors in logs
        "noplaylist": True,  # Ignore playlists
        "extract_flat": True,  # Extract metadata only
    }

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
            logger.info(f"🔍 Extracted Info: {info}")  # ✅ Debugging: Log extracted data

            if info and "entries" not in info:  # Ensure it's a valid single video
                return True
            else:
                logger.warning("⚠️ Video info not valid. It may be private or age-restricted.")
    except yt_dlp.DownloadError as e:
        logger.error(f"❌ yt-dlp DownloadError: {str(e)}")
    except Exception as e:
        logger.error(f"⚠️ Unexpected Error in is_downloadable: {str(e)}")

    return False


# ✅ Ask user for video quality
async def ask_quality(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    url = update.message.text.strip()

    # First, check if it's a valid URL
    if not is_valid_url(url):
        await update.message.reply_text("❌ Invalid URL! Please send a correct video link.")
        return ConversationHandler.END

    # Second, check if the URL is downloadable
    if not is_downloadable(url):
        await update.message.reply_text("❌ Could not verify the video. Ensure it's public and try again!")
        return ConversationHandler.END

    user_choices[chat_id] = {"url": url}

    keyboard = [["High", "Medium", "Low"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("📌 Choose video quality:", reply_markup=reply_markup)

    return 1  # Move to next step in conversation

# ✅ Download and send video
async def download_media(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
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

    # Handle YouTube authentication with cookies
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
        await update.message.reply_text("📥 Downloading, please wait...")

        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)

        safe_filepath = os.path.join("downloads", os.path.basename(file_path))

        # ✅ Ensure file isn't too large for Telegram (50MB limit)
        if os.path.getsize(safe_filepath) > 50 * 1024 * 1024:
            await update.message.reply_text("❌ File too large! Try selecting a lower quality.")
            return ConversationHandler.END

        try:
            with open(safe_filepath, "rb") as video_file:
                await context.bot.send_video(chat_id=chat_id, video=video_file)
            await update.message.reply_text("✅ Download completed! Send another link.")
        finally:
            if os.path.exists(safe_filepath):
                os.remove(safe_filepath)

    except yt_dlp.DownloadError as e:
        await update.message.reply_text(f"❌ Download Error: {str(e)}")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Unexpected Error: {str(e)}")

    return ConversationHandler.END

# ✅ Start Command
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("👋 Welcome to MediaFetchBot!\nPaste a public video URL to download.")

# ✅ Main Function
def main():
    def main():
    if not TOKEN:
        raise ValueError("❌ BOT_TOKEN is missing! Set it in Railway environment variables.")
    
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
