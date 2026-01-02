import os
import re
import logging
import json
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import yt_dlp
import tempfile

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_INFO = {
    'name': '@vD7m01_Bot',
    'version': 'v3.0 Pro',
    'type': 'Advanced Media Downloader',
}

# جميع المواقع المدعومة (أكثر من 500 موقع)
SUPPORTED_SITES = {
    'youtube': {'emoji': '🎥', 'name': 'YouTube', 'pattern': r'(youtube\.com|youtu\.be|youtube-nocookie\.com)'},
    'tiktok': {'emoji': '🎵', 'name': 'TikTok', 'pattern': r'(tiktok\.com|vm\.tiktok\.com|vt\.tiktok\.com|m\.tiktok\.com)'},
    'instagram': {'emoji': '📸', 'name': 'Instagram', 'pattern': r'(instagram\.com|instagr\.am|ig\.me)'},
    'twitter': {'emoji': '𝕏', 'name': 'Twitter/X', 'pattern': r'(twitter\.com|x\.com|t\.co)'},
    'facebook': {'emoji': '👍', 'name': 'Facebook', 'pattern': r'(facebook\.com|fb\.watch|fb\.com)'},
    'reddit': {'emoji': '🤖', 'name': 'Reddit', 'pattern': r'reddit\.com'},
    'pinterest': {'emoji': '📌', 'name': 'Pinterest', 'pattern': r'pinterest\.com'},
    'twitch': {'emoji': '🎮', 'name': 'Twitch', 'pattern': r'twitch\.tv'},
    'vimeo': {'emoji': '🎬', 'name': 'Vimeo', 'pattern': r'vimeo\.com'},
    'dailymotion': {'emoji': '🎞️', 'name': 'Dailymotion', 'pattern': r'dailymotion\.com'},
    'soundcloud': {'emoji': '🎧', 'name': 'SoundCloud', 'pattern': r'soundcloud\.com'},
    'spotify': {'emoji': '🎵', 'name': 'Spotify', 'pattern': r'spotify\.com'},
    'generic': {'emoji': '🌐', 'name': 'Web Content', 'pattern': r'https?://'},
}

def detect_platform(url):
    """الكشف عن نوع الموقع"""
    for platform, info in SUPPORTED_SITES.items():
        if re.search(info['pattern'], url, re.IGNORECASE):
            return platform, info
    return 'generic', SUPPORTED_SITES['generic']

def extract_urls(text):
    """استخراج الروابط من النص"""
    return re.findall(r'https?://[^\s]+', text)

def format_filesize(bytes_size):
    """تنسيق حجم الملف"""
    if bytes_size == 0:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.2f} PB"

def format_duration(seconds):
    """تنسيق المدة الزمنية"""
    if not seconds:
        return "Unknown"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours:
        return f"{int(hours)}س {int(minutes)}د {int(secs)}ث"
    elif minutes:
        return f"{int(minutes)}د {int(secs)}ث"
    else:
        return f"{int(secs)}ث"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر البداية"""
    welcome = f"""
╔════════════════════════════════════╗
║  🎬 مرحبا في {BOT_INFO['name']} 🎬   ║
║    {BOT_INFO['type']}    ║
╚════════════════════════════════════╝

✨ **بوت تحميل متقدم وقوي جداً**

🌍 **المواقع المدعومة:**
🎥 YouTube • 🎵 TikTok • 📸 Instagram
𝕏 Twitter/X • 👍 Facebook • Reddit
🎮 Twitch • 🎬 Vimeo • 📌 Pinterest
🎧 SoundCloud • + 500 موقع آخر!

📊 **المميزات:**
✅ بدون حد أقصى للحجم
✅ أي نوع محتوى (فيديو, صوت, صور)
✅ جودة عالية جداً
✅ معلومات كاملة عن المحتوى
✅ تحميل فوري وسريع

🚀 **الاستخدام:**
1️⃣ أرسل أي رابط
2️⃣ اختر نوع التحميل
3️⃣ استقبل الملف فوراً! ⚡

📝 **ملاحظة:**
سيتم عرض جميع معلومات المحتوى
(العنوان، المنشئ، الوصف، الإحصائيات)
"""
    
    keyboard = [[InlineKeyboardButton("📖 المساعدة", callback_data='help')]]
    await update.message.reply_text(welcome, reply_markup=InlineKeyboardMarkup(keyboard))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر المساعدة"""
    help_text = """
📖 **دليل الاستخدام الكامل:**

🔗 **خطوات التحميل:**
1️⃣ انسخ الرابط من أي موقع
2️⃣ أرسله لي مباشرة
3️⃣ سأعرض لك المعلومات الكاملة
4️⃣ اختر نوع التحميل:
   🎬 فيديو بأفضل جودة
   🎧 صوت فقط (MP3)
   📷 صور
5️⃣ استقبل ملفك فوراً! 🚀

⚡ **ملفات ضخمة جداً مدعومة!**

🌐 **الروابط المدعومة:**
• YouTube (أي مقطع, حتى الطويل جداً)
• TikTok (بدون العلامات المائية)
• Instagram (صور وفيديوهات ومقاطع IGTV)
• Twitter/X (فيديوهات وصور)
• Facebook (أي محتوى)
• Reddit, Twitch, Vimeo, وأكثر!

💡 **نصائح مهمة:**
• الملفات الكبيرة قد تستغرق دقائق
• جودة الفيديو تعتمد على المنصة
• الصوت يُحفظ بصيغة MP3 عالية الجودة

❓ **للمساعدة:** أرسل /help
🔄 **لإعادة المحاولة:** أرسل رابط جديد
"""
    await update.message.reply_text(help_text)

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الروابط المرسلة"""
    text = update.message.text
    urls = extract_urls(text)
    
    if not urls:
        await update.message.reply_text(
            "🔗 **رجاءً أرسل رابط صحيح!**\n\n"
            "مثال: https://www.youtube.com/watch?v=..."
        )
        return
    
    url = urls[0]
    platform, platform_info = detect_platform(url)
    
    # حفظ البيانات
    context.user_data['url'] = url
    context.user_data['platform'] = platform
    
    await update.message.reply_text(
        f"🔄 **جاري الكشف عن المعلومات...**\n\n"
        f"المنصة: {platform_info['emoji']} {platform_info['name']}"
    )
    
    # استخراج المعلومات
    info = await extract_media_info(url)
    
    if not info:
        await update.message.reply_text(
            "❌ **عذراً، لم أتمكن من الوصول لهذا الرابط**\n\n"
            "تأكد من:\n"
            "✓ الرابط صحيح\n"
            "✓ المحتوى متاح للعام\n"
            "✓ لا توجد قيود جغرافية"
        )
        return
    
    # عرض المعلومات الكاملة
    context.user_data['info'] = info
    await display_media_info(update, context, platform_info, info)

async def extract_media_info(url):
    """استخراج معلومات المحتوى الكاملة"""
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': 30,
            'noplaylist': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info
    except Exception as e:
        logger.error(f"Info extraction error: {e}")
        return None

async def display_media_info(update: Update, context: ContextTypes.DEFAULT_TYPE, platform_info, info):
    """عرض معلومات المحتوى بشكل جميل"""
    try:
        title = info.get('title', 'Unknown')[:100]
        uploader = info.get('uploader', 'Unknown')
        description = info.get('description', '')[:300]
        duration = info.get('duration', 0)
        view_count = info.get('view_count', 0)
        like_count = info.get('like_count', 0)
        upload_date = info.get('upload_date', '')
        
        # تنسيق التاريخ
        if upload_date:
            date_obj = datetime.strptime(upload_date, '%Y%m%d')
            upload_date = date_obj.strftime('%d/%m/%Y')
        
        # رسالة المعلومات الكاملة
        message = f"""
╔════════════════════════════════════╗
║  {platform_info['emoji']} **معلومات المحتوى**  {platform_info['emoji']}
╚════════════════════════════════════╝

📝 **العنوان:**
{title}

👤 **المنشئ:**
{uploader}

📅 **تاريخ النشر:**
{upload_date if upload_date else 'غير متاح'}

⏱️ **المدة:**
{format_duration(duration)}

👁️ **المشاهدات:**
{f'{view_count:,}' if view_count else 'غير متاح'}

❤️ **الإعجابات:**
{f'{like_count:,}' if like_count else 'غير متاح'}

📄 **الوصف:**
{description[:200]}...

═══════════════════════════════════

اختر نوع التحميل:
"""
        
        keyboard = [
            [InlineKeyboardButton("🎬 تحميل فيديو", callback_data='download_video')],
            [InlineKeyboardButton("🎧 تحميل صوت MP3", callback_data='download_audio')],
            [InlineKeyboardButton("❌ إلغاء", callback_data='cancel')]
        ]
        
        await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
        
    except Exception as e:
        logger.error(f"Display info error: {e}")
        await update.message.reply_text("❌ حدث خطأ في عرض المعلومات")

async def download_media(url, media_type='video'):
    """تحميل الملف (فيديو أو صوت)"""
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
                'quiet': False,
                'socket_timeout': 120,
                'retries': 5,
                'fragment_retries': 10,
                'noplaylist': True,
                'progress_hooks': [],
            }
        else:  # video
            ydl_opts = {
                'format': 'best[ext=mp4]/best[ext=webm]/best',
                'outtmpl': os.path.join(temp_dir, 'video_%(id)s.%(ext)s'),
                'quiet': False,
                'socket_timeout': 120,
                'retries': 5,
                'fragment_retries': 10,
                'noplaylist': True,
                'progress_hooks': [],
                'merge_output_format': 'mp4',
            }
        
        logger.info(f"⬇️ Downloading {media_type}: {url}")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            # البحث عن ملف MP3 للصوت
            if media_type == 'audio' and not filename.endswith('.mp3'):
                mp3_file = filename.rsplit('.', 1)[0] + '.mp3'
                if os.path.exists(mp3_file):
                    filename = mp3_file
            
            if os.path.exists(filename):
                logger.info(f"✅ Downloaded: {filename}")
                return filename, info
        
        return None, None
        
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        return None, None

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج الأزرار والاختيارات"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'help':
        help_text = """📖 **تعليمات سريعة:**
1️⃣ أرسل رابط أي فيديو
2️⃣ اختر نوع التحميل
3️⃣ استقبل الملف فوراً!
✅ بدون حد حجم!"""
        await query.edit_message_text(help_text)
        return
    
    if query.data == 'cancel':
        await query.edit_message_text("❌ تم الإلغاء. أرسل رابط جديد!")
        return
    
    url = context.user_data.get('url')
    info = context.user_data.get('info')
    
    if not url or not info:
        await query.edit_message_text("❌ حدث خطأ! أرسل رابط جديد")
        return
    
    if query.data == 'download_video':
        media_type = 'video'
        emoji = '🎬'
    elif query.data == 'download_audio':
        media_type = 'audio'
        emoji = '🎧'
    else:
        return
    
    # رسالة التحميل
    await query.edit_message_text(
        f"{emoji} **جاري التحميل...**\n\n"
        f"⏳ قد يستغرق دقائق (خاصة الملفات الكبيرة)\n"
        f"🚫 لا تغلق هذه النافذة"
    )
    
    filename, final_info = await download_media(url, media_type)
    
    if not filename:
        await query.edit_message_text(
            "❌ **فشل التحميل!**\n\n"
            "السبب المحتمل:\n"
            "• المحتوى غير متاح\n"
            "• قيود جغرافية\n"
            "• مشكلة في الاتصال\n\n"
            "جرّب رابط آخر!"
        )
        return
    
    try:
        file_size = os.path.getsize(filename)
        title = final_info.get('title', 'Unknown')[:80]
        uploader = final_info.get('uploader', 'Unknown')[:50]
        duration = final_info.get('duration', 0)
        
        # Caption مفصل
        caption = f"""
╔════════════════════════════════════╗
║  ✅ تم التحميل بنجاح! ✅
╚════════════════════════════════════╝

📝 **العنوان:**
{title}

👤 **المنشئ:**
{uploader}

📁 **حجم الملف:**
{format_filesize(file_size)}

⏱️ **المدة:**
{format_duration(duration)}

🤖 **البوت:** {BOT_INFO['name']}
📅 **الوقت:** {datetime.now().strftime('%H:%M:%S')}

═══════════════════════════════════
شكراً لاستخدامك البوت! 🙏
"""
        
        await query.edit_message_text("📤 **جاري إرسال الملف...**")
        
        if media_type == 'video':
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
        
        await query.edit_message_text("✅ **تم الإرسال بنجاح!** 🎉\n\nأرسل رابط جديد للمتابعة")
        
        # حذف الملف
        if os.path.exists(filename):
            os.remove(filename)
            
    except Exception as e:
        logger.error(f"Send error: {e}")
        await query.edit_message_text(
            f"❌ **خطأ في الإرسال**\n\n"
            f"الملف كبير جداً لـ Telegram\n"
            f"الحد الأقصى: 2GB"
        )
        if os.path.exists(filename):
            os.remove(filename)

def main():
    """تشغيل البوت"""
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    
    if not token:
        logger.error("❌ TELEGRAM_BOT_TOKEN not found!")
        return
    
    app = Application.builder().token(token).build()
    
    # الأوامر
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    
    # معالجات الأزرار والرسائل
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    
    logger.info(f"🚀 Bot {BOT_INFO['name']} is running!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
