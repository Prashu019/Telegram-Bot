import os
import logging
import yt_dlp
import re
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

if not os.path.exists("downloads"):
    os.makedirs("downloads")

QUALITY_SELECTION = 1
user_choices = {}

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Welcome to MediaFetchBot! Paste a public video URL to download.")

async def ask_quality(update: Update, context: CallbackContext):
    url = update.message.text
    chat_id = update.message.chat_id
    user_choices[chat_id] = {"url": url}
    keyboard = [["High", "Medium", "Low"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Choose the video quality:", reply_markup=reply_markup)
    return QUALITY_SELECTION

async def download_media(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    quality = update.message.text
    url = user_choices.get(chat_id, {}).get("url")

    if not url:
        await update.message.reply_text("Error: URL not found. Please send a valid link.")
        return ConversationHandler.END

    quality_formats = {
        "High": "bestvideo+bestaudio/best",
        "Medium": "bv[height<=720]+ba/best[height<=720]",
        "Low": "bv[height<=480]+ba/best[height<=480]"
    }

    options = {  
        'outtmpl': 'downloads/%(title)s.%(ext)s',  
        'noplaylist': True,
        'merge_output_format': 'mp4',
        'restrictfilenames': True,
        'format': quality_formats.get(quality, "best"),
    }

    if "youtube.com" in url or "youtu.be" in url:
        options["cookiefile"] = "youtube_cookies.txt"
    elif "facebook.com" in url:
        options["cookiefile"] = "facebook_cookies.txt"

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            safe_filename = re.sub(r'[<>:"/\\|?*]', '', os.path.basename(file_path))
            safe_filepath = os.path.join("downloads", safe_filename)
            if file_path != safe_filepath:
                os.rename(file_path, safe_filepath)
            if os.path.exists(safe_filepath):
                if safe_filepath.endswith((".mp4", ".mkv", ".webm")):
                    await context.bot.send_video(chat_id=chat_id, video=open(safe_filepath, "rb"))
                elif safe_filepath.endswith((".jpg", ".jpeg", ".png")):
                    await context.bot.send_photo(chat_id=chat_id, photo=open(safe_filepath, "rb"))
                os.remove(safe_filepath)
                await update.message.reply_text("Download completed! Send another link.")
            else:
                await update.message.reply_text("Error: File not found!")
    except yt_dlp.DownloadError as e:
        await update.message.reply_text(f"Download Error: {str(e)}")
    except Exception as e:
        await update.message.reply_text(f"Unexpected Error: {str(e)}")
    return ConversationHandler.END

def main():
    TOKEN = os.getenv("BOT_TOKEN")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, ask_quality)],
        states={QUALITY_SELECTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, download_media)]},
        fallbacks=[],
    )
    app.add_handler(conv_handler)
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
