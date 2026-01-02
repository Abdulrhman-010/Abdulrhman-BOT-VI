import os
import re
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import yt_dlp
import tempfile

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_urls(text):
    return re.findall(r'https?://[^\s]+', text)

def detect_platform(url):
    patterns = {
        'youtube': r'(youtube\.com|youtu\.be)',
        'tiktok': r'(tiktok\.com|vm\.tiktok\.com|vt\.tiktok\.com)',
        'instagram': r'(instagram\.com|instagr\.am)',
        'twitter': r'(twitter\.com|x\.com)',
        'facebook': r'(facebook\.com|fb\.watch)',
    }
    for platform, pattern in patterns.items():
        if re.search(pattern, url, re.IGNORECASE):
            return platform
    return 'other'

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 أرسل رابط أي فيديو أو صورة\n\n"
        "🎬 فيديو • 🎧 صوت • 📸 صور"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 أرسل رابط → اختر النوع → استقبل الملف!"
    )

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    urls = extract_urls(text)
    
    if not urls:
        await update.message.reply_text("🔗 أرسل رابط!")
        return
    
    url = urls[0]
    platform = detect_platform(url)
    
    context.user_data['url'] = url
    
    keyboard = [
        [InlineKeyboardButton("🎬 فيديو", callback_data='video')],
        [InlineKeyboardButton("🎧 صوت", callback_data='audio')],
        [InlineKeyboardButton("📸 صور", callback_data='image')]
    ]
    
    await update.message.reply_text(
        f"✅ {platform.upper()}\n\n"
        "اختر:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def download_file(url, media_type):
    try:
        temp_dir = tempfile.gettempdir()
        
        if media_type == 'audio':
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': os.path.join(temp_dir, 'audio_%(id)s.%(ext)s'),
                'quiet': True,
                'no_warnings': True,
            }
        elif media_type == 'image':
            ydl_opts = {
                'format': 'images',
                'outtmpl': os.path.join(temp_dir, 'image_%(id)s.%(ext)s'),
                'quiet': True,
                'no_warnings': True,
            }
        else:  # video
            ydl_opts = {
                'format': 'best[ext=mp4]/best',
                'outtmpl': os.path.join(temp_dir, 'video_%(id)s.%(ext)s'),
                'quiet': True,
                'no_warnings': True,
            }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            # للصوت MP3
            if media_type == 'audio' and not filename.endswith('.mp3'):
                mp3_file = filename.rsplit('.', 1)[0] + '.mp3'
                if os.path.exists(mp3_file):
                    filename = mp3_file
            
            if os.path.exists(filename):
                return filename, info
        
        return None, None
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return None, None

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    url = context.user_data.get('url')
    if not url:
        await query.edit_message_text("❌ خطأ")
        return
    
    media_type = query.data
    
    await query.edit_message_text("⏳ جاري التحميل...")
    
    filename, info = await download_file(url, media_type)
    
    if not filename:
        await query.edit_message_text("❌ فشل التحميل")
        return
    
    try:
        await query.edit_message_text("📤 جاري الإرسال...")
        
        title = info.get('title', 'Media')[:50]
        
        if media_type == 'video':
            with open(filename, 'rb') as f:
                await query.message.reply_video(
                    video=f,
                    caption=title,
                    supports_streaming=True,
                    write_timeout=600
                )
        elif media_type == 'audio':
            with open(filename, 'rb') as f:
                await query.message.reply_audio(
                    audio=f,
                    caption=title,
                    write_timeout=600
                )
        else:  # image
            with open(filename, 'rb') as f:
                await query.message.reply_photo(
                    photo=f,
                    caption=title
                )
        
        await query.edit_message_text("✅ تم!")
        
        if os.path.exists(filename):
            os.remove(filename)
            
    except Exception as e:
        logger.error(f"Send error: {e}")
        await query.edit_message_text("❌ خطأ في الإرسال")
        if os.path.exists(filename):
            os.remove(filename)

def main():
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    
    if not token:
        logger.error("❌ No token!")
        return
    
    app = Application.builder().token(token).build()
    
    # جميع الأوامر تعمل 100%
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    
    logger.info("🚀 Bot running - All commands ready!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
