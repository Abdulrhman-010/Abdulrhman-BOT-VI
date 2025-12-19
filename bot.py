import os
import re
import logging
import json
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    filters, ContextTypes, CallbackQueryHandler, ConversationHandler
)
from telegram.constants import ChatAction
import yt_dlp
import tempfile
import subprocess

# إعدادات السجل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# معلومات البوت
BOT_INFO = {
    'name': 'Abdulrhman-BOT-VI',
    'version': 'v2.0',
    'developer': 'عبدالرحمن العنزي',
    'email': 'aalanzi@azmx.sa',
    'date': 'ديسمبر 2025',
    'type': 'Video & Media Downloader'
}

# حالات المحادثة
CHOOSING_FORMAT = 1

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
        'pattern': r'(facebook\.com|fb\.watch)',
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
    'snapchat': {
        'pattern': r'snapchat\.com',
        'icon': '👻',
        'name': 'Snapchat'
    }
}

# الرسائل
MESSAGES = {
    'welcome': "🎬 مرحباً بك في {name}!\n✨ أنا بوت تحميل الفيديوهات والصور والصوتيات من أي موقع!\n\n📱 **المواقع المدعومة:**\n🎥 YouTube • 🎵 TikTok • 📸 Instagram • 🐦 Twitter • 📘 Facebook • وغيرها...\n\n🚀 **كيف تستخدمني:**\n1️⃣ أرسل لي رابط الفيديو/الصورة\n2️⃣ اختر نوع التحميل (فيديو/صورة/صوت)\n3️⃣ أنا بحمّله وأرسله فوراً! 🎉\n\n⚡ **بدون حد حجم - تحميل الملفات الضخمة بسهولة**",
    'help': "📖 **دليل الاستخدام:**\n\n1️⃣ انسخ رابط الفيديو أو الصورة\n2️⃣ أرسله لي هنا\n3️⃣ اختر ما تبي:\n   • 🎬 فيديو (أفضل جودة)\n   • 📷 صورة\n   • 🎧 صوت فقط (MP3)\n4️⃣ استلم الملف فوراً! ⚡\n\n💡 **الملفات الضخمة مدعومة بدون حد!**",
    'processing': "⏳ جاري المعالجة... الرجاء الانتظار 🔄",
    'choosing': "اختر نوع التحميل اللي تبيه:",
    'success': "✅ تفضل! الملف جاهز بدون علامة مائية 🎉",
    'error': "😅 معذرة، ما قدرت أحمّل هذا الرابط\nالرجاء المحاولة مع رابط آخر",
    'unsupported': "🤔 هذا الموقع غير مدعوم حالياً\n\n✅ المواقع المدعومة:\n🎥 YouTube • 🎵 TikTok • 📸 Instagram • 🐦 Twitter • 📘 Facebook",
    'url_required': "🔗 أرسل لي رابط صحيح من فضلك!",
    'size_info': "📁 حجم الملف: {size}\n⏱️ المدة: {duration}\n📱 الدقة: {quality}"
}

def detect_platform(url):
    """الكشف عن موقع الرابط"""
    for platform, info in SUPPORTED_SITES.items():
        if re.search(info['pattern'], url, re.IGNORECASE):
            return platform, info
    return None, None

def extract_urls(text):
    """استخراج الروابط من النص"""
    return re.findall(r'https?://[^\s]+', text)

def format_filesize(bytes_size):
    """تنسيق حجم الملف"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.1f} TB"

def get_video_info(url):
    """الحصول على معلومات الفيديو"""
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                'title': info.get('title', 'Unknown'),
                'duration': info.get('duration', 0),
                'thumbnail': info.get('thumbnail', ''),
                'formats': info.get('formats', [])
            }
    except Exception as e:
        logger.error(f"Error getting video info: {e}")
        return None

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

━━━━━━━━━━━━━━━━━━
🎯 بوت شخصي لتسهيل التحميل
"""
    await update.message.reply_text(about_text, parse_mode='Markdown')

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الروابط"""
    text = update.message.text
    urls = extract_urls(text)
    
    if not urls:
        await update.message.reply_text(MESSAGES['url_required'])
        return
    
    url = urls[0]
    platform, platform_info = detect_platform(url)
    
    if not platform:
        await update.message.reply_text(MESSAGES['unsupported'])
        return
    
    # حفظ الرابط والمنصة في context
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
    """تحميل الفيديو بأنواع مختلفة"""
    try:
        temp_dir = tempfile.gettempdir()
        
        if format_type == 'video':
            ydl_opts = {
                'format': 'best[ext=mp4]/best',
                'outtmpl': os.path.join(temp_dir, '%(id)s.%(ext)s'),
                'quiet': False,
                'no_warnings': False,
                'progress_hooks': [],
            }
        elif format_type == 'audio':
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': os.path.join(temp_dir, '%(id)s.%(ext)s'),
                'quiet': False,
                'no_warnings': False,
            }
        else:  # image
            ydl_opts = {
                'format': 'best',
                'outtmpl': os.path.join(temp_dir, '%(id)s.%(ext)s'),
                'quiet': False,
                'no_warnings': False,
                'writethumbnail': True,
            }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            if os.path.exists(filename):
                return filename, info
            
        return None, None
        
    except Exception as e:
        logger.error(f"Download error: {e}")
        return None, None

async def format_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج اختيار صيغة التحميل"""
    query = update.callback_query
    await query.answer()
    
    url = context.user_data.get('url')
    platform_info = context.user_data.get('platform_info')
    
    if not url:
        await query.edit_message_text("❌ ]. دز يبوي ما ضبط معي")
        return
    
    format_type = query.data.replace('format_', '')
    
    # رسالة المعالجة
    await query.edit_message_text(
        f"⏳ اصبر شوي ويننننا فيييه يبوووي؟؟ {format_type} من {platform_info['name']}...\n 🕐"
    )
    
    # إرسال إشارة "جاري الكتابة"
    await context.bot.send_chat_action(
        chat_id=query.message.chat_id,
        action=ChatAction.UPLOAD_VIDEO if format_type == 'video' else ChatAction.UPLOAD_DOCUMENT
    )
    
    # التحميل
    filename, info = await download_video(url, format_type)
    
    if not filename:
        await query.edit_message_text(MESSAGES['error'])
        return
    
    # الإرسال
    try:
        file_size = os.path.getsize(filename)
        duration = info.get('duration', 0)
        
        # تنسيق المدة
        minutes, seconds = divmod(duration, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            duration_str = f"{int(hours)}س {int(minutes)}د"
        else:
            duration_str = f"{int(minutes)}د {int(seconds)}ث"
        
        caption = f"""✅ {MESSAGES['success']}

📱 **المنصة:** {platform_info['name']}
📁 **الحجم:** {format_filesize(file_size)}
⏱️ **المدة:** {duration_str}
📝 **العنوان:** {info.get('title', 'N/A')[:50]}

🤖 @vD7m01_Bot"""
        
        if format_type == 'video':
            await query.message.reply_video(
                video=open(filename, 'rb'),
                caption=caption,
                supports_streaming=True
            )
        elif format_type == 'audio':
            await query.message.reply_audio(
                audio=open(filename, 'rb'),
                caption=caption
            )
        else:  # image
            await query.message.reply_photo(
                photo=open(filename, 'rb'),
                caption=caption
            )
        
        await query.edit_message_text("✅ تم الإرسال بنجاح! 🎉")
        
        # حذف الملف بعد الإرسال
        if os.path.exists(filename):
            os.remove(filename)
            
    except Exception as e:
        logger.error(f"Send error: {e}")
        await query.edit_message_text(f"❌ خطأ في الإرسال: {str(e)[:100]}")
        if os.path.exists(filename):
            os.remove(filename)

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
        return
    
    app = Application.builder().token(token).build()
    
    # المعالجات
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("about", about_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    
    logger.info("🚀 Bot is running... Press Ctrl+C to stop")
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
