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
        'format': quality_formats.get(quality, "best"),  # Default to "best" if quality invalid
    }

    # Add cookie file if applicable and exists
    cookie_files = {
        "youtube.com": "youtube_cookies.txt",
        "youtu.be": "youtube_cookies.txt",
        "facebook.com": "facebook_cookies.txt"
    }
    for domain, cookie_file in cookie_files.items():
        if domain in url and os.path.exists(cookie_file):
            options["cookiefile"] = cookie_file
            break

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)

        safe_filepath = os.path.join("downloads", os.path.basename(file_path))
        if os.path.getsize(safe_filepath) > 50 * 1024 * 1024:  # 50MB limit
            await update.message.reply_text("⚠️ File too large for Telegram (>50MB)!")
        else:
            try:
                await context.bot.send_video(chat_id=chat_id, video=open(safe_filepath, "rb"))
                await update.message.reply_text("✅ Download completed! Send another link.")
            finally:
                os.remove(safe_filepath)

    except yt_dlp.DownloadError as e:
        await update.message.reply_text(f"❌ Download Error: {str(e)}")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Unexpected Error: {str(e)}")

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
