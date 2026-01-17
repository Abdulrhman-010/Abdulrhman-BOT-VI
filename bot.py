import os
import re
import logging
import json
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    filters, ContextTypes, CallbackQueryHandler
)
from telegram.constants import ChatAction
import yt_dlp
import tempfile
import shutil

# إعدادات السجل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# معلومات البوت
BOT_INFO = {
    'name': 'Abdulrhman-BOT-VI',
    'version': 'v2.1',
    'developer': 'عبدالرحمن العنزي',
    'email': 'aalanzi@azmx.sa',
    'date': 'يناير 2026',
    'type': 'Video & Media Downloader'
}

# أنماط المواقع المدعومة
SUPPORTED_SITES = {
    'youtube': {
        'pattern': r'(youtube\.com|youtu\.be)',
        'icon': '🎥',
        'name': 'YouTube'
    },
    'tiktok': {
        'pattern': r'(tiktok\.com|vm\.tiktok\.com|vt\.tiktok\.com)',
        'icon': '🎵',
        'name': 'TikTok'
    },
    'instagram': {
        'pattern': r'(instagram\.com|instagr\.am)',
        'icon': '📸',
        'name': 'Instagram'
    },
    'twitter': {
        'pattern': r'(twitter\.com|x\.com)',
        'icon': '🐦',
        'name': 'Twitter (X)'
    },
    'facebook': {
        'pattern': r'(facebook\.com|fb\.watch|fb\.com)',
        'icon': '📘',
        'name': 'Facebook'
    },
    'reddit': {
        'pattern': r'reddit\.com',
        'icon': '🤖',
        'name': 'Reddit'
    },
    'pinterest': {
        'pattern': r'pinterest\.com',
        'icon': '📌',
        'name': 'Pinterest'
    },
    'twitch': {
        'pattern': r'twitch\.tv',
        'icon': '🎮',
        'name': 'Twitch'
    },
    'soundcloud': {
        'pattern': r'soundcloud\.com',
        'icon': '🎙️',
        'name': 'SoundCloud'
    }
}

# الرسائل
MESSAGES = {
    'welcome': "🎬 مرحباً بك في {name}!\n✨ أنا بوت تحميل الفيديوهات والصور والصوتيات من أي موقع!\n\n📱 **المواقع المدعومة:**\n🎥 YouTube • 🎵 TikTok • 📸 Instagram • 🐦 Twitter • 📘 Facebook • وغيرها...\n\n🚀 **كيف تستخدمني:**\n1️⃣ أرسل لي رابط الفيديو/الصورة\n2️⃣ اختر نوع التحميل (فيديو/صورة/صوت)\n3️⃣ أنا بحمّله وأرسله فوراً! 🎉\n\n⚡ **بدون حد حجم - تحميل الملفات الضخمة بسهولة**",
    'help': "📖 **دليل الاستخدام:**\n\n1️⃣ انسخ رابط الفيديو أو الصورة\n2️⃣ أرسله لي هنا\n3️⃣ اختر ما تبي:\n   • 🎬 فيديو (أفضل جودة)\n   • 📷 صورة/صور\n   • 🎧 صوت فقط (MP3)\n4️⃣ استلم الملف فوراً! ⚡\n\n💡 **الملفات الضخمة مدعومة بدون حد!**\n🚀 يدعم مئات المواقع",
    'processing': "⏳ جاري المعالجة... الرجاء الانتظار 🔄",
    'choosing': "اختر نوع التحميل اللي تبيه:",
    'success': "✅ تفضل! الملف جاهز 🎉",
    'error': "😅 معذرة، ما قدرت أحمّل هذا الرابط\nالرجاء المحاولة مع رابط آخر",
    'unsupported': "🤔 هذا الموقع غير مدعوم حالياً\n\n✅ المواقع المدعومة:\n🎥 YouTube • 🎵 TikTok • 📸 Instagram • 🐦 Twitter • 📘 Facebook • وغيرها",
    'url_required': "🔗 أرسل لي رابط صحيح من فضلك!",
    'invalid_url': "❌ الرابط غير صحيح. تأكد من نسخ الرابط كاملاً",
    'file_too_large': "⚠️ الملف كبير جداً (أكثر من 2GB). قد يأخذ وقتاً طويلاً",
}

def detect_platform(url):
    """الكشف عن موقع الرابط"""
    for platform, info in SUPPORTED_SITES.items():
        if re.search(info['pattern'], url, re.IGNORECASE):
            return platform, info
    return None, None

def extract_urls(text):
    """استخراج الروابط من النص"""
    urls = re.findall(r'https?://[^\s\)]+', text)
    return [url.rstrip('.,:;') for url in urls]  # إزالة الترقيم الزائد

def format_filesize(bytes_size):
    """تنسيق حجم الملف"""
    try:
        bytes_size = int(bytes_size)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_size < 1024:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024
        return f"{bytes_size:.1f} TB"
    except:
        return "N/A"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر البداية"""
    welcome_text = MESSAGES['welcome'].format(name=BOT_INFO['name'])
    
    keyboard = [
        [InlineKeyboardButton("📖 المساعدة", callback_data='help'),
         InlineKeyboardButton("ℹ️ عن البوت", callback_data='about')]
    ]
    
    await update.message.reply_text(
        welcome_text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر المساعدة"""
    await update.message.reply_text(
        MESSAGES['help'],
        parse_mode='Markdown'
    )

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معلومات عن البوت"""
    about_text = f"""
🤖 **معلومات البوت:**

📛 **الاسم:** {BOT_INFO['name']}
🔢 **الإصدار:** {BOT_INFO['version']}
📝 **النوع:** {BOT_INFO['type']}

👨💻 **المطور:** {BOT_INFO['developer']}
📧 **البريد:** {BOT_INFO['email']}
📅 **التاريخ:** {BOT_INFO['date']}

⚡ **المميزات:**
✅ تحميل من مئات المواقع
✅ بدون حد حجم للملفات
✅ جودة عالية تلقائياً
✅ دعم الصوت والصور والفيديو
✅ تحويل تلقائي للصيغ
✅ سرعة عالية جداً

━━━━━━━━━━━━━━━━━━
🎯 بوت احترافي لتسهيل التحميل
"""
    await update.message.reply_text(about_text, parse_mode='Markdown')

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الروابط"""
    text = update.message.text.strip()
    urls = extract_urls(text)
    
    if not urls:
        await update.message.reply_text(MESSAGES['url_required'])
        return
    
    url = urls[0]
    
    # التحقق من صحة الرابط
    if not url.startswith(('http://', 'https://')):
        await update.message.reply_text(MESSAGES['invalid_url'])
        return
    
    platform, platform_info = detect_platform(url)
    
    if not platform:
        await update.message.reply_text(MESSAGES['unsupported'])
        return
    
    # حفظ البيانات
    context.user_data['url'] = url
    context.user_data['platform'] = platform
    context.user_data['platform_info'] = platform_info
    
    # عرض خيارات التحميل
    keyboard = [
        [InlineKeyboardButton("🎬 فيديو (أفضل جودة)", callback_data='format_video')],
        [InlineKeyboardButton("📷 صورة/صور", callback_data='format_image')],
        [InlineKeyboardButton("🎧 صوت فقط (MP3)", callback_data='format_audio')]
    ]
    
    msg_text = f"✨ تم الكشف عن المنصة: {platform_info['icon']} {platform_info['name']}\n\n{MESSAGES['choosing']}"
    
    await update.message.reply_text(
        msg_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def download_video(url, format_type='best'):
    """تحميل الفيديو بأنواع مختلفة - محسّن!"""
    try:
        temp_dir = tempfile.gettempdir()
        
        if format_type == 'video':
            # أفضل صيغة فيديو
            ydl_opts = {
                'format': 'best[ext=mp4]/best[height<=720]/best',
                'outtmpl': os.path.join(temp_dir, '%(id)s_video.%(ext)s'),
                'quiet': False,
                'no_warnings': False,
                'socket_timeout': 60,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                },
                'extract_audio': False,
            }
        
        elif format_type == 'audio':
            # استخراج الصوت بدون ffmpeg
            ydl_opts = {
                'format': 'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best',
                'outtmpl': os.path.join(temp_dir, '%(id)s_audio.%(ext)s'),
                'quiet': False,
                'no_warnings': False,
                'socket_timeout': 60,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                },
                'extract_audio': False,
                'prefer_ffmpeg': False,
                'postprocessors': [
                    {
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '128',
                    }
                ] if shutil.which('ffmpeg') else []  # تشغيل ffmpeg فقط إذا كان مثبتاً
            }
        
        else:  # image
            ydl_opts = {
                'format': 'best',
                'outtmpl': os.path.join(temp_dir, '%(id)s_image.%(ext)s'),
                'quiet': False,
                'no_warnings': False,
                'socket_timeout': 60,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                },
                'writethumbnail': False,
            }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.info(f"Downloading {format_type} from {url}")
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            if os.path.exists(filename):
                logger.info(f"Download successful: {filename}")
                return filename, info
            
            # البحث عن الملف إذا كان الاسم مختلفاً
            base_name = info.get('id', '')
            temp_files = os.listdir(temp_dir)
            for f in temp_files:
                if base_name in f and (f.endswith('.mp4') or f.endswith('.m4a') or f.endswith('.webm') or f.endswith('.mp3')):
                    full_path = os.path.join(temp_dir, f)
                    logger.info(f"Found file: {full_path}")
                    return full_path, info
        
        return None, None
        
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        return None, None

async def format_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج اختيار صيغة التحميل"""
    query = update.callback_query
    await query.answer()
    
    url = context.user_data.get('url')
    platform_info = context.user_data.get('platform_info')
    
    if not url:
        await query.edit_message_text("❌ حدث خطأ، الرجاء المحاولة مرة أخرى")
        return
    
    format_type = query.data.replace('format_', '')
    
    # رسالة المعالجة
    await query.edit_message_text(
        f"⏳ جاري تحميل {format_type} من {platform_info['name']}...\nقد يستغرق عدة دقائق 🕐"
    )
    
    # إرسال إشارة الكتابة
    try:
        await context.bot.send_chat_action(
            chat_id=query.message.chat_id,
            action=ChatAction.UPLOAD_DOCUMENT
        )
    except:
        pass
    
    # التحميل
    filename, info = await download_video(url, format_type)
    
    if not filename:
        await query.edit_message_text(MESSAGES['error'])
        logger.error(f"Failed to download: {url}")
        return
    
    # الإرسال
    try:
        file_size = os.path.getsize(filename)
        duration = info.get('duration', 0)
        
        # تنسيق المدة
        if duration:
            minutes, seconds = divmod(int(duration), 60)
            hours, minutes = divmod(minutes, 60)
            if hours:
                duration_str = f"{hours}س {minutes}د"
            else:
                duration_str = f"{minutes}د {seconds}ث"
        else:
            duration_str = "N/A"
        
        caption = f"""✅ {MESSAGES['success']}

📱 **المنصة:** {platform_info['name']}
📁 **الحجم:** {format_filesize(file_size)}
⏱️ **المدة:** {duration_str}
📝 **العنوان:** {info.get('title', 'N/A')[:50]}

🤖 @Abdulrhman_VI_bot"""
        
        with open(filename, 'rb') as file:
            if format_type == 'video':
                await query.message.reply_video(
                    video=file,
                    caption=caption,
                    supports_streaming=True
                )
            elif format_type == 'audio':
                await query.message.reply_audio(
                    audio=file,
                    caption=caption
                )
            else:  # image
                await query.message.reply_photo(
                    photo=file,
                    caption=caption
                )
        
        await query.edit_message_text("✅ تم الإرسال بنجاح! 🎉")
        logger.info(f"Successfully sent {format_type} file")
        
    except Exception as e:
        logger.error(f"Send error: {str(e)}")
        await query.edit_message_text(f"❌ خطأ في الإرسال: {str(e)[:100]}")
    
    finally:
        # حذف الملف
        try:
            if os.path.exists(filename):
                os.remove(filename)
                logger.info(f"Deleted temp file: {filename}")
        except:
            pass

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج الأزرار"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'help':
        await query.edit_message_text(MESSAGES['help'], parse_mode='Markdown')
    elif query.data == 'about':
        about_text = f"""
🤖 **معلومات البوت:**
📛 **الاسم:** {BOT_INFO['name']}
🔢 **الإصدار:** {BOT_INFO['version']}
👨💻 **المطور:** {BOT_INFO['developer']}
        """
        await query.edit_message_text(about_text, parse_mode='Markdown')
    elif 'format_' in query.data:
        await format_callback(update, context)

def main():
    """تشغيل البوت"""
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    
    if not token:
        logger.error("❌ TELEGRAM_BOT_TOKEN not found in environment variables")
        print("❌ اضبط متغير TELEGRAM_BOT_TOKEN")
        return
    
    app = Application.builder().token(token).build()
    
    # المعالجات
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("about", about_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    
    logger.info("🚀 Bot is running...")
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
