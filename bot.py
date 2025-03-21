import re
from urllib.parse import urlparse
import os
import yt_dlp
import logging
from telegram import Update
from telegram.ext import Application, CallbackContext, ConversationHandler, CommandHandler

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Use environment variable for BOT_TOKEN (set in Railway)
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Assuming user_choices is a global dictionary defined elsewhere
user_choices = {}

async def start(update: Update, context: CallbackContext):
    """Simple start command to verify the bot is responsive."""
    logger.info(f"Received /start command from chat_id: {update.message.chat_id}")
    await update.message.reply_text("Hello! I'm your download bot. Use /download <url> to start.")
    return ConversationHandler.END

async def download_media(update: Update, context: CallbackContext):
    """Downloads media from a URL provided by the user."""
    chat_id = update.message.chat_id
    logger.info(f"Received message in download_media: {update.message.text} from chat_id: {chat_id}")

    # For testing, assume the URL is in the message text (e.g., "/download <url>")
    url = update.message.text.split(maxsplit=1)[1] if len(update.message.text.split()) > 1 else None
    quality = "Medium"  # Default quality for testing; adjust as needed

    if not url:
        logger.warning(f"No URL provided by chat_id: {chat_id}")
        await update.message.reply_text("❌ Error: URL not found. Please send a valid link with /download <url>.")
        return ConversationHandler.END

    logger.info(f"Processing URL: {url} for chat_id: {chat_id}")

    # Step 1: Validate URL format
    url_pattern = re.compile(r'^https?://[^\s/$.?#].[^\s]*$')
    if not url_pattern.match(url):
        logger.warning(f"Invalid URL format: {url}")
        await update.message.reply_text("❌ Error: Invalid URL format. Please send a valid link (e.g., https://example.com).")
        return ConversationHandler.END

    # Step 2: Check supported platforms
    supported_domains = ["youtube.com", "youtu.be", "facebook.com"]
    parsed_url = urlparse(url)
    if not any(domain in parsed_url.netloc for domain in supported_domains):
        logger.info(f"URL {url} not from supported platform, proceeding anyway")
        await update.message.reply_text(
            "⚠️ Warning: URL is not from a supported platform (YouTube or Facebook). Trying anyway..."
        )

    # Step 3: Verify URL with yt-dlp
    validate_options = {'quiet': True, 'simulate': True}
    try:
        with yt_dlp.YoutubeDL(validate_options) as ydl:
            ydl.extract_info(url, download=False)
        logger.info(f"URL {url} validated successfully")
    except yt_dlp.DownloadError as e:
        logger.error(f"URL validation failed: {str(e)}")
        await update.message.reply_text(f"❌ Error: Invalid or unsupported URL: {str(e)}")
        return ConversationHandler.END

    # Step 4: Configure download options
    quality_formats = {
        "High": "bestvideo[height<=1080]+bestaudio/best",
        "Medium": "bestvideo[height<=720]+bestaudio/best",
        "Low": "bestvideo[height<=480]+bestaudio/best"
    }
    download_options = {
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'noplaylist': True,
        'merge_output_format': 'mp4',
        'restrictfilenames': True,
        'format': quality_formats.get(quality, "best"),
    }

    # Step 5: Handle cookies
    cookie_files = {
        "youtube.com": "youtube_cookies.txt",
        "youtu.be": "youtube_cookies.txt",
        "facebook.com": "facebook_cookies.txt"
    }
    for domain, cookie_file in cookie_files.items():
        if domain in parsed_url.netloc and os.path.exists(cookie_file):
            download_options["cookiefile"] = cookie_file
            logger.info(f"Using cookie file: {cookie_file}")
            break
    else:
        if "youtube.com" in parsed_url.netloc or "youtu.be" in parsed_url.netloc:
            logger.warning("YouTube URL detected but no cookie file found")
            await update.message.reply_text(
                "⚠️ YouTube requires authentication, but no cookie file found. "
                "Please provide cookies via youtube_cookies.txt. See: "
                "https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp"
            )
            return ConversationHandler.END

    # Step 6: Download and send
    try:
        with yt_dlp.YoutubeDL(download_options) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
        safe_filepath = os.path.join("downloads", os.path.basename(file_path))
        logger.info(f"Downloaded file to: {safe_filepath}")

        if os.path.getsize(safe_filepath) > 50 * 1024 * 1024:
            logger.warning(f"File too large: {os.path.getsize(safe_filepath)} bytes")
            await update.message.reply_text("⚠️ File too large for Telegram (>50MB)!")
            if os.path.exists(safe_filepath):
                os.remove(safe_filepath)
            return ConversationHandler.END

        try:
            await context.bot.send_video(chat_id=chat_id, video=open(safe_filepath, "rb"))
            logger.info(f"Video sent successfully to chat_id: {chat_id}")
            await update.message.reply_text("✅ Download completed! Send another link.")
        finally:
            if os.path.exists(safe_filepath):
                os.remove(safe_filepath)
                logger.info(f"Cleaned up file: {safe_filepath}")

    except yt_dlp.DownloadError as e:
        logger.error(f"Download error: {str(e)}")
        await update.message.reply_text(f"❌ Download Error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        await update.message.reply_text(f"⚠️ Unexpected Error: {str(e)}")

    return ConversationHandler.END

if __name__ == "__main__":
    # Check if BOT_TOKEN is set
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN environment variable is not set")
        raise ValueError("BOT_TOKEN environment variable is not set. Please set it in Railway variables.")

    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("download", download_media))

    # Run the bot
    logger.info("Bot is starting...")
    print("Bot is running...")  # Kept for Railway logs
    application.run_polling()
