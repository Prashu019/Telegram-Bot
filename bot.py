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
    }

    if "youtube.com" in url or "youtu.be" in url:
        options["cookiefile"] = "youtube_cookies.txt"

    elif "facebook.com" in url:
        options["cookiefile"] = "facebook_cookies.txt"

    try:
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)  # Get available formats
        
        available_formats = [f['format_id'] for f in info['formats']]
        
        selected_format = None
        for fmt in quality_formats[quality].split('/'):
            if fmt in available_formats:
                selected_format = fmt
                break

        if not selected_format:
            await update.message.reply_text("⚠️ Selected quality is not available. Downloading best available format.")
            selected_format = "best"

        options["format"] = selected_format

        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)

            safe_filename = re.sub(r'[<>:"/\\|?*]', '', os.path.basename(file_path))
            safe_filepath = os.path.join("downloads", safe_filename)

            if file_path != safe_filepath:
                os.rename(file_path, safe_filepath)

            if os.path.exists(safe_filepath):
                await context.bot.send_video(chat_id=chat_id, video=open(safe_filepath, "rb"))
                os.remove(safe_filepath)
                await update.message.reply_text("✅ Download completed! Send another link.")
            else:
                await update.message.reply_text("❌ Error: File not found!")

    except yt_dlp.DownloadError as e:
        await update.message.reply_text(f"❌ Download Error: {str(e)}")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Unexpected Error: {str(e)}")

    return ConversationHandler.END
