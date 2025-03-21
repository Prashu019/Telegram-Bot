import re
from urllib.parse import urlparse
import os
import yt_dlp
from telegram import Update  # Import Update class
from telegram.ext import Application, CallbackContext, ConversationHandler  # Import required classes

# Assuming user_choices is a global dictionary defined elsewhere
user_choices = {}  # Replace with your actual implementation if different

async def download_media(update: Update, context: CallbackContext):
    """
    Downloads media from a URL provided by the user and sends it via Telegram.
    Validates the URL before proceeding with the download.
    """
    chat_id = update.message.chat_id
    quality = update.message.text
    url = user_choices.get(chat_id, {}).get("url")

    # Step 1: Check if URL exists
    if not url:
        await update.message.reply_text("❌ Error: URL not found. Please send a valid link.")
        return ConversationHandler.END

    # Step 2: Validate URL format
    url_pattern = re.compile(r'^https?://[^\s/$.?#].[^\s]*$')
    if not url_pattern.match(url):
        await update.message.reply_text("❌ Error: Invalid URL format. Please send a valid link (e.g., https://example.com).")
        return ConversationHandler.END

    # Step 3: Check if URL is from a supported platform (optional)
    supported_domains = ["youtube.com", "youtu.be", "facebook.com"]
    parsed_url = urlparse(url)
    if not any(domain in parsed_url.netloc for domain in supported_domains):
        await update.message.reply_text(
            "⚠️ Warning: URL is not from a supported platform (YouTube or Facebook). Trying anyway..."
        )

    # Step 4: Verify URL is valid for yt-dlp
    validate_options = {
        'quiet': True,  # Suppress output for this initial check
        'simulate': True,  # Don’t download, just extract info
    }
    try:
        with yt_dlp.YoutubeDL(validate_options) as ydl:
            ydl.extract_info(url, download=False)  # Test if URL is valid
    except yt_dlp.DownloadError as e:
        await update.message.reply_text(f"❌ Error: Invalid or unsupported URL: {str(e)}")
        return ConversationHandler.END

    # Step 5: Configure download options
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

    # Step 6: Handle cookies for YouTube or Facebook
    cookie_files = {
        "youtube.com": "youtube_cookies.txt",
        "youtu.be": "youtube_cookies.txt",
        "facebook.com": "facebook_cookies.txt"
    }
    for domain, cookie_file in cookie_files.items():
        if domain in parsed_url.netloc and os.path.exists(cookie_file):
            download_options["cookiefile"] = cookie_file
            break
    else:  # If no cookie file is found for YouTube
        if "youtube.com" in parsed_url.netloc or "youtu.be" in parsed_url.netloc:
            await update.message.reply_text(
                "⚠️ YouTube requires authentication, but no cookie file found. "
                "Please provide cookies via youtube_cookies.txt. See: "
                "https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp"
            )
            return ConversationHandler.END

    # Step 7: Perform the download
    try:
        with yt_dlp.YoutubeDL(download_options) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)

        safe_filepath = os.path.join("downloads", os.path.basename(file_path))
        # Optional: Check file size (Telegram limit: 50MB for bots)
        if os.path.getsize(safe_filepath) > 50 * 1024 * 1024:
            await update.message.reply_text("⚠️ File too large for Telegram (>50MB)!")
            if os.path.exists(safe_filepath):
                os.remove(safe_filepath)
            return ConversationHandler.END

        try:
            await context.bot.send_video(chat_id=chat_id, video=open(safe_filepath, "rb"))
            await update.message.reply_text("✅ Download completed! Send another link.")
        finally:
            if os.path.exists(safe_filepath):
                os.remove(safe_filepath)

    except yt_dlp.DownloadError as e:
        await update.message.reply_text(f"❌ Download Error: {str(e)}")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Unexpected Error: {str(e)}")

    return ConversationHandler.END

if __name__ == "__main__":
    # Example bot setup for testing
    import asyncio

    # Replace 'YOUR_TOKEN' with your actual Telegram bot token
    TOKEN = "YOUR_TOKEN"

    # Create the Application
    application = Application.builder().token(TOKEN).build()

    # For testing purposes, you might want to add a basic handler
    # Normally, this would be part of a larger ConversationHandler setup
    async def test_handler(update: Update, context: CallbackContext):
        user_choices[update.message.chat_id] = {"url": update.message.text}
        await download_media(update, context)

    application.add_handler(
        telegram.ext.CommandHandler("download", test_handler)
    )

    # Run the bot
    print("Bot is running...")
    application.run_polling()
