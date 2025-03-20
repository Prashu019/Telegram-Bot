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

# ✅ Download Function
async def download_media(url, chat_id, context):
    options = {  
        'outtmpl': 'downloads/%(title)s.%(ext)s',  # Save in 'downloads' folder
        'noplaylist': True,
        'restrictfilenames': True,  # ✅ Prevents special characters in filenames
    }

    # Detect Platform
    if "youtube.com" in url or "youtu.be" in url:
        platform = "YouTube"
        options["format"] = "bestvideo[ext=mp4]/best[ext=mp4]/best"
        options["cookiefile"] = "youtube_cookies.txt"  # ✅ Use YouTube cookies for authentication
    elif "facebook.com" in url:
        platform = "Facebook"
        options["format"] = "best[ext=mp4]/best"
        options["cookiefile"] = "facebook_cookies.txt"  # ✅ Use Facebook cookies for authentication
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

                # ✅ Ask for another download
                await context.bot.send_message(chat_id=chat_id, text="✅ Download completed! Want to download another video?")
                await ask_platform(update=Update(chat_id, {}), context=context)

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
    TOKEN = os.getenv("BOT_TOKEN")  # ⬅️ Load from environment variable

    if not TOKEN:
        print("❌ BOT_TOKEN not found! Set it in Railway Environment Variables.")
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
