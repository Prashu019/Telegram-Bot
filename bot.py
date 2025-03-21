import os
import logging
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, CallbackContext

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ ERROR: TELEGRAM_BOT_TOKEN is not set!")

DOWNLOAD_PATH = "/tmp"  # For Railway

async def start(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("📹 YouTube", callback_data="youtube")],
        [InlineKeyboardButton("📘 Facebook", callback_data="facebook")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📥 Choose the platform:", reply_markup=reply_markup)

async def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    platform = query.data
    context.user_data["platform"] = platform
    await query.message.reply_text(f"✅ You selected *{platform.capitalize()}*.\nNow send me the video link.", parse_mode="Markdown")

async def download_media(update: Update, context: CallbackContext):
    url = update.message.text.strip()
    platform = context.user_data.get("platform")

    if not platform:
        await update.message.reply_text("❌ Please select a platform first using /start")
        return

    await update.message.reply_text(f"📥 Downloading from *{platform.capitalize()}*...\nPlease wait.", parse_mode="Markdown")

    options = {
        'outtmpl': f"{DOWNLOAD_PATH}/%(id)s.%(ext)s",  # FIX: Shorter filename
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
        'merge_output_format': 'mp4',
        'noplaylist': True,
        'quiet': True
    }

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            video_path = ydl.prepare_filename(info_dict)

        await update.message.reply_text("✅ Download complete! Uploading video...")

        with open(video_path, "rb") as video:
            await update.message.reply_video(video)

        os.remove(video_path)

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
        logger.error(f"Download Error: {e}")

    await update.message.reply_text("🔄 Do you want to download another video? Use /start")

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_media))

    logger.info("🚀 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
