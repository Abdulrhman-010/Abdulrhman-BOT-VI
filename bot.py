import os
import re
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import yt_dlp
import tempfile

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_INFO = {
    'name': 'Abdulrhman-BOT-VI',
    'version': 'v2.2',
    'developer': 'عبدالرحمن العنزي',
    'email': 'aalanzi@azmx.sa',
}

SUPPORTED_SITES = {
    'youtube': r'(youtube\.com|youtu\.be)',
    'tiktok': r'(tiktok\.com|vm\.tiktok\.com)',
    'instagram': r'(instagram\.com|instagr\.am)',
    'twitter': r'(twitter\.com|x\.com)',
    'facebook': r'(facebook\.com|fb\.watch)',
    'reddit': r'reddit\.com',
}

def detect_platform(url):
    for platform, pattern in SUPPORTED_SITES.items():
        if re.search(pattern, url, re.IGNORECASE):
            return platform
    return None

def extract_urls(text):
    return re.findall(r'https?://[^\s]+', text)

def format_filesize(bytes_size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.1f} TB"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome = f"""🎬 مرحباً في {BOT_INFO['name']}!

✨ بوت تحميل الفيديوهات والصور والصوتيات

📱 المواقع المدعومة:
🎥 YouTube • 🎵 TikTok • 📸 Instagram
🐦 Twitter • 📘 Facebook • Reddit وأكثر!

🚀 الاستخدام:
1️⃣ أرسل رابط الفيديو
2️⃣ اختر نوع التحميل
3️⃣ سأحمّله لك فوراً! ⚡

✅ بدون حد حجم
✅ جودة عالية
✅ تحميل الصوت مباشرة"""
    
    keyboard = [[InlineKeyboardButton("📖 المساعدة", callback_data='help')]]
    await update.message.reply_text(welcome, reply_markup=InlineKeyboardMarkup(keyboard))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """📖 **دليل الاستخدام:**

1️⃣ انسخ رابط الفيديو من أي موقع
2️⃣ أرسله لي
3️⃣ اختر نوع التحميل:
   🎬 فيديو بأفضل جودة
   🎧 صوت فقط (MP3)
4️⃣ استلم الملف! ⚡

💡 الملفات الضخمة مدعومة بدون حد!"""
    
    await update.message.reply_text(help_text)

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    urls = extract_urls(text)
    
    if not urls:
        await update.message.reply_text("🔗 أرسل لي رابط صحيح!")
        return
    
    url = urls[0]
    platform = detect_platform(url)
    
    if not platform:
        await update.message.reply_text("🤔 هذا الموقع غير مدعوم حالياً")
        return
    
    context.user_data['url'] = url
    context.user_data['platform'] = platform
    
    keyboard = [
        [InlineKeyboardButton("🎬 فيديو", callback_data='video')],
        [InlineKeyboardButton("🎧 صوت (MP3)", callback_data='audio')]
    ]
    
    await update.message.reply_text(
        f"✨ تم الكشف: {platform.upper()}\n\n👇 اختر نوع التحميل:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def download_file(url, format_type='video'):
    """تحميل الملف"""
    try:
        temp_dir = tempfile.gettempdir()
        
        if format_type == 'audio':
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
        else:  # video
            ydl_opts = {
                'format': 'best[ext=mp4]/best',
                'outtmpl': os.path.join(temp_dir, 'video_%(id)s.%(ext)s'),
                'quiet': True,
                'no_warnings': True,
                'socket_timeout': 60,
                'retries': 3,
                'fragment_retries': 3,
            }
        
        logger.info(f"📥 Downloading {format_type}: {url}")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            if format_type == 'audio' and not filename.endswith('.mp3'):
                mp3_file = filename.rsplit('.', 1)[0] + '.mp3'
                if os.path.exists(mp3_file):
                    filename = mp3_file
            
            if os.path.exists(filename):
                logger.info(f"✅ Downloaded: {filename}")
                return filename, info
        
        return None, None
        
    except Exception as e:
        logger.error(f"❌ Download error: {str(e)}")
        return None, None

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'help':
        help_text = """📖 **الاستخدام:**
1️⃣ أرسل رابط
2️⃣ اختر النوع
3️⃣ استلم الملف!"""
        await query.edit_message_text(help_text)
        return
    
    url = context.user_data.get('url')
    format_type = query.data
    
    if not url:
        await query.edit_message_text("❌ حدث خطأ!")
        return
    
    await query.edit_message_text("⏳ جاري التحميل... انتظر قليلاً")
    
    filename, info = await download_file(url, format_type)
    
    if not filename:
        await query.edit_message_text("❌ فشل التحميل! جرب رابط آخر")
        return
    
    try:
        file_size = os.path.getsize(filename)
        title = info.get('title', 'Unknown')[:60]
        
        caption = f"""✅ تفضل! الملف جاهز

📁 الحجم: {format_filesize(file_size)}
📝 {title}

🤖 @Abdulrhman_VI_bot"""
        
        await query.edit_message_text("📤 جاري إرسال الملف...")
        
        if format_type == 'video':
            with open(filename, 'rb') as f:
                await query.message.reply_video(
                    video=f,
                    caption=caption,
                    supports_streaming=True,
                    write_timeout=600
                )
        else:  # audio
            with open(filename, 'rb') as f:
                await query.message.reply_audio(
                    audio=f,
                    caption=caption,
                    write_timeout=600
                )
        
        await query.edit_message_text("✅ تم الإرسال! 🎉")
        
        if os.path.exists(filename):
            os.remove(filename)
            
    except Exception as e:
        logger.error(f"Send error: {e}")
        await query.edit_message_text(f"❌ خطأ في الإرسال")
        if os.path.exists(filename):
            os.remove(filename)

def main():
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    
    if not token:
        logger.error("❌ TELEGRAM_BOT_TOKEN not found!")
        return
    
    app = Application.builder().token(token).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    
    logger.info("🚀 Bot is running!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
