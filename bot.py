import os
import logging
import yt_dlp
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# ✅ Logging Setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
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
        'outtmpl': 'downloads/%(title)s.%(ext)s',  # Save in 'downloads' folder
        'noplaylist': True,
        'merge_output_format': None,  # Disable merging
        'restrictfilenames': True,  # ✅ Prevents special characters in filenames
    }

    # Detect Platform and Set Options
    if "youtube.com" in url or "youtu.be" in url:
        options["format"] = "bestvideo[ext=mp4]/best[ext=mp4]/best"
        options["cookiefile"] = "youtube_cookies.txt"  # ✅ Use YouTube cookies

    elif "facebook.com" in url:
        options["format"] = "best[ext=mp4]/best"
        options["cookiefile"] = "facebook_cookies.txt"  # ✅ Use Facebook cookies

    elif "instagram.com" in url:
        options["format"] = "best[ext=mp4]/best"

    elif "twitter.com" in url or "x.com" in url:
        options["format"] = "best[ext=mp4]/best"

    elif "tiktok.com" in url:
        options["format"] = "best[ext=mp4]/best"

    else:
        await context.bot.send_message(chat_id=chat_id, text="❌ Unsupported platform! Please send a valid URL.")
        return

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)

            # ✅ Sanitize filename (remove special characters)
            safe_filename = re.sub(r'[<>:"/\\|?*]', '', os.path.basename(file_path))
            safe_filepath = os.path.join("downloads", safe_filename)

            # ✅ Rename file if needed
            if file_path != safe_filepath:
                os.rename(file_path, safe_filepath)

            # ✅ Send the downloaded file
            if os.path.exists(safe_filepath):
                if safe_filepath.endswith((".mp4", ".mkv", ".webm")):
                    await context.bot.send_video(chat_id=chat_id, video=open(safe_filepath, "rb"))
                elif safe_filepath.endswith((".jpg", ".jpeg", ".png")):
                    await context.bot.send_photo(chat_id=chat_id, photo=open(safe_filepath, "rb"))

                # ✅ Cleanup after sending
                os.remove(safe_filepath)

                await context.bot.send_message(chat_id=chat_id, text="✅ Download completed! Paste another video URL to download.")

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
    TOKEN = os.getenv("BOT_TOKEN")  # ⬅️ Ensure BOT_TOKEN is set in Railway

    if not TOKEN:
        print("❌ ERROR: BOT_TOKEN is missing!")
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
