import os
import logging
import yt_dlp
import re
import ssl
import aiofiles
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler

# Ensure SSL support
try:
    ssl.create_default_context()
except ImportError:
    raise ImportError("SSL module is missing! Ensure your Python installation includes SSL support.")

# Logging setup
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Create downloads directory if not exists
os.makedirs("downloads", exist_ok=True)

# Bot token setup
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN is missing! Set it in Railway environment variables.")

user_choices = {}

# Validate URL
async def is_valid_url(url):
    regex = re.compile(r"^(https?://)?(www\.)?(youtube\.com|youtu\.be|facebook\.com|instagram\.com|twitter\.com|tiktok\.com)/")
    if not re.match(regex, url):
        return False
    
    try:
        with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
            info = ydl.extract_info(url, download=False)
            return "formats" in info  # Ensure video has downloadable formats
    except yt_dlp.DownloadError:
        return False

async def ask_quality(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    url = update.message.text.strip()

    if not await is_valid_url(url):
        await update.message.reply_text("Invalid or unsupported URL! Please send a valid video link.")
        return ConversationHandler.END

    user_choices[chat_id] = {"url": url}
    keyboard = [["High", "Medium", "Low"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Choose video quality:", reply_markup=reply_markup)
    return 1

async def download_media(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    quality = update.message.text
    url = user_choices.get(chat_id, {}).get("url")

    if not url:
        await update.message.reply_text("Error: URL not found. Please send a valid link.")
        return ConversationHandler.END

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
        'format': quality_formats.get(quality, "best")
    }

    try:
        await update.message.reply_text("Downloading, please wait...")
        
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
        
        safe_filepath = os.path.join("downloads", os.path.basename(file_path))
        
        async with aiofiles.open(safe_filepath, "rb") as video:
            video_data = await video.read()
            await context.bot.send_video(chat_id=chat_id, video=video_data)
        
        await update.message.reply_text("Download completed! Send another link.")
        os.remove(safe_filepath)  # Cleanup after sending
    
    except yt_dlp.DownloadError as e:
        if "Signature extraction failed" in str(e):
            await update.message.reply_text(
                "YouTube has updated its security, and downloads may not work. Please wait for yt-dlp updates."
            )
        else:
            await update.message.reply_text(f"Download Error: {str(e)}")
    except Exception as e:
        await update.message.reply_text(f"Unexpected Error: {str(e)}")
    
    return ConversationHandler.END

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Welcome to MediaFetchBot!\nPaste a public video URL to download.")

def main():
    app = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, ask_quality)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, download_media)],
        },
        fallbacks=[],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
