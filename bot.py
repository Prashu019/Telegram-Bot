import os
import logging
import yt_dlp
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# ✅ Logging Setup
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ✅ Ensure 'downloads' directory exists
if not os.path.exists("downloads"):
    os.makedirs("downloads")

# ✅ Start Command
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("👋 Welcome to MediaFetchBot!\nPaste a public video URL to download.")

# ✅ Download Function
async def download_media(url, chat_id, context):
    options = {  
        'outtmpl': 'downloads/%(title)s.%(ext)s',  
        'noplaylist': True,
        'merge_output_format': 'mp4',  # ✅ Merge video + audio
        'restrictfilenames': True,
        'format': 'bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]',  # ✅ Best video + audio
    }

    # ✅ Detect platform and apply necessary cookies
    if "youtube.com" in url or "youtu.be" in url:
        options["cookiefile"] = "youtube_cookies.txt"  # ✅ YouTube cookies
    elif "facebook.com" in url:
        options["cookiefile"] = "facebook_cookies.txt"  # ✅ Facebook cookies

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)

            # ✅ Sanitize filename (remove special characters)
            safe_filename = re.sub(r'[<>:"/\\|?*]', '', os.path.basename(file_path))
            safe_filepath = os.path.join("downloads", safe_filename)

            if file_path != safe_filepath:
                os.rename(file_path, safe_filepath)

            # ✅ Send the downloaded file
            if os.path.exists(safe_filepath):
                if safe_filepath.endswith((".mp4", ".mkv", ".webm")):
                    await context.bot.send_video(chat_id=chat_id, video=open(safe_filepath, "rb"))
                elif safe_filepath.endswith((".jpg", ".jpeg", ".png")):
                    await context.bot.send_photo(chat_id=chat_id, photo=open(safe_filepath, "rb"))

                os.remove(safe_filepath)  # ✅ Cleanup after sending

                await context.bot.send_message(chat_id=chat_id, text="✅ Download completed! Send another link.")
            else:
                await context.bot.send_message(chat_id=chat_id, text="❌ Error: File not found!")

    except yt_dlp.DownloadError as e:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ Download Error: {str(e)}")
    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"⚠️ Unexpected Error: {str(e)}")

# ✅ Handle User Messages (URL Input)
async def handle_message(update: Update, context: CallbackContext):
    url = update.message.text
    chat_id = update.message.chat_id
    await context.bot.send_message(chat_id=chat_id, text="📥 Downloading, please wait...")
    await download_media(url, chat_id, context)

# ✅ Main Function
def main():
    TOKEN = os.getenv("BOT_TOKEN")  # ⬅️ Load token from environment variable

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
