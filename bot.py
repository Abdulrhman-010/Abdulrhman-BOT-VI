import os
import re
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import yt_dlp
import tempfile

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

SUPPORTED_SITES = {
    'youtube': r'(youtube\.com|youtu\.be)',
    'tiktok': r'(tiktok\.com|vm\.tiktok\.com|vt\.tiktok\.com)',
    'instagram': r'(instagram\.com|instagr\.am)',
    'twitter': r'(twitter\.com|x\.com)',
    'facebook': r'(facebook\.com|fb\.watch)',
    'reddit': r'reddit\.com',
    'pinterest': r'pinterest\.com',
    'twitch': r'twitch\.tv',
}

def detect_platform(url):
    for platform, pattern in SUPPORTED_SITES.items():
        if re.search(pattern, url, re.IGNORECASE):
            return platform
    return None

def extract_urls(text):
    return re.findall(r'https?://[^\s]+', text)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 أهلا وسهلا!\n\n"
        "أرسل لي أي رابط وأحمّله لك\n\n"
        "🎬 فيديو • 🎧 صوت • 📸 صور"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 الطريقة:\n"
        "1️⃣ أرسل رابط\n"
        "2️⃣ اختر نوع التحميل\n"
        "3️⃣ استقبل الملف!"
    )

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    urls = extract_urls(text)
    
    if not urls:
        await update.message.reply_text("🔗 أرسل رابط!")
        return
    
    url = urls[0]
    platform = detect_platform(url)
    
    if not platform:
        await update.message.reply_text("❌ رابط غير مدعوم")
        return
    
    context.user_data['url'] = url
    
    keyboard = [
        [InlineKeyboardButton("🎬 فيديو", callback_data='video')],
        [InlineKeyboardButton("🎧 صوت", callback_data='audio')]
    ]
    
    await update.message.reply_text(
        f"✅ تم الكشف\n\n"
        f"اختر نوع التحميل:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def download_file(url, media_type='video'):
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
                'socket_timeout': 60,
                'retries': 3,
            }
        else:
            ydl_opts = {
                'format': 'best[ext=mp4]/best',
                'outtmpl': os.path.join(temp_dir, 'video_%(id)s.%(ext)s'),
                'quiet': True,
                'no_warnings': True,
                'socket_timeout': 60,
                'retries': 3,
            }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
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
    
    media_type = 'audio' if query.data == 'audio' else 'video'
    
    await query.edit_message_text("⏳ جاري التحميل...")
    
    filename, info = await download_file(url, media_type)
    
    if not filename:
        await query.edit_message_text("❌ فشل التحميل")
        return
    
    try:
        await query.edit_message_text("📤 جاري الإرسال...")
        
        if media_type == 'video':
            with open(filename, 'rb') as f:
                await query.message.reply_video(
                    video=f,
                    supports_streaming=True,
                    write_timeout=600
                )
        else:
            with open(filename, 'rb') as f:
                await query.message.reply_audio(
                    audio=f,
                    write_timeout=600
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
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    
    logger.info("🚀 Bot running!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
