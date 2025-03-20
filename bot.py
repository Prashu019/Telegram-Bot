import os
import logging
import yt_dlp
import re
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from dotenv import load_dotenv

# ✅ Load environment variables
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

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
    await update.message.reply_text("\U0001F4CC Choose the platform:", reply_markup=reply_markup)

# ✅ Start Command
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("\U0001F44B Welcome to MediaFetchBot!\nPaste a public video URL to download.")
    await ask_platform(update, context)

# ✅ Download Function
async def download_media(url, chat_id, context):
    options = {  
        'outtmpl': 'downloads/%(title)s.%(ext)s',  # Save in 'downloads' folder
        'noplaylist': True,
        'restrictfilenames': True,  # ✅ Prevents special characters in filenames
    }

    # Detect Platform
    platform = None
    if "youtube.com" in url or "youtu.be" in url:
        platform = "YouTube"
        options["format"] = "bestvideo[ext=mp4]/best[ext=mp4]/best"
    elif "facebook.com" in url:
        platform = "Facebook"
        options["format"] = "best[ext=mp4]/best"
        options["cookiefile"] = "all_cookies.txt"
    elif "instagram.com" in url:
        platform = "Instagram"
        options["format"] = "best[ext=mp4]/best"
    elif "twitter.com" in url or "x.com" in url:
        platform = "Twitter"
        options["format"] = "best[ext=mp4]/best"
    elif "tiktok.com" in url:
        platform = "TikTok"
        options["format"] = "best[ext=mp4]/best"
    else:
        await context.bot.send_message(chat_id=chat_id, text="❌ Unsupported platform! Please send a valid URL.")
        return
    
    await context.bot.send_message(chat_id=chat_id, text=f"📡 Fetching {platform} media...")

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)

            # ✅ Sanitize filename
            safe_filename = re.sub(r'[<>:"/\\|?*]', '', os.path.basename(file_path))
            safe_filepath = os.path.join("downloads", safe_filename)

            if file_path != safe_filepath:
                os.rename(file_path, safe_filepath)

            if os.path.exists(safe_filepath):
                file_size = os.path.getsize(safe_filepath) / (1024 * 1024)  # MB
                if file_size > 50:
                    await context.bot.send_document(chat_id=chat_id, document=open(safe_filepath, "rb"))
                else:
                    await context.bot.send_video(chat_id=chat_id, video=open(safe_filepath, "rb"))
                os.remove(safe_filepath)
                await context.bot.send_message(chat_id=chat_id, text="✅ Download completed!")
            else:
                await context.bot.send_message(chat_id=chat_id, text="❌ Error: File not found!")

    except yt_dlp.DownloadError as e:
        logger.error(str(e))
        await context.bot.send_message(chat_id=chat_id, text=f"❌ Download Error: {str(e)}")
    except Exception as e:
        logger.error(str(e))
        await context.bot.send_message(chat_id=chat_id, text=f"⚠️ Unexpected Error: {str(e)}")

# ✅ Handle User Messages (URL Input)
async def handle_message(update: Update, context: CallbackContext):
    url = update.message.text
    chat_id = update.message.chat_id
    await context.bot.send_message(chat_id=chat_id, text="📥 Downloading, please wait...")
    await download_media(url, chat_id, context)

# ✅ Main Function
def main():
    if not TOKEN:
        logger.error("BOT_TOKEN is missing in environment variables!")
        return
    
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
