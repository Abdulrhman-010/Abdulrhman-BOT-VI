import os
import re
import logging
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import yt_dlp
import tempfile

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ======== الرسائل السعودية الشبابية ========
MESSAGES = {
    'welcome': [
        "يلا يا وحش! 🔥 ارسلي الرابط وازهل",
        "هلا بيك يا عم! 👽 طلع لي رابط وأحمّله لك",
        "وين الرابط يا طالع؟ 💀 ارسل وخلصنا",
        "يلا يا زين! 🚀 شنو الرابط اللي بتبي أحمّله",
    ],
    'processing': [
        "اصبر شويات يا حمقة 🔄 أنا أشتغل",
        "بحمّل لك يا وحش... اصبر 🔥",
        "ركض شويات وارجع... بحمّل 💨",
        "هاي دقيقة وتستقبل الملف يا عم 🚀",
    ],
    'success': [
        "تفضل يا وحش! 🎉 استمتع",
        "هاي الحاجة اللي طلبت يا زين! 💪",
        "اتفضل يا عم! استمتع بقلبك 😎",
        "تمام التمام يا حمقة! 🔥 اطلعها",
    ],
    'error': [
        "يا إلهي! حصلت مشكلة 😅",
        "ما قدرت يا وحش... حاول رابط ثاني 💀",
        "الرابط غلط يا عم 😤 شيك الرابط",
        "مو قادر على هذا يا حمقة 😭",
    ]
}

# ======== المنصات المدعومة ========
PLATFORMS = {
    'youtube': {'emoji': '🎥', 'name': 'يوتيوب', 'pattern': r'(youtube\.com|youtu\.be|youtube-nocookie)'},
    'tiktok': {'emoji': '🎵', 'name': 'تيك توك', 'pattern': r'(tiktok\.com|vm\.tiktok\.com|vt\.tiktok\.com|m\.tiktok\.com)'},
    'instagram': {'emoji': '📸', 'name': 'انستقرام', 'pattern': r'(instagram\.com|instagr\.am|ig\.me)'},
    'twitter': {'emoji': '𝕏', 'name': 'تويتر/X', 'pattern': r'(twitter\.com|x\.com|t\.co)'},
    'facebook': {'emoji': '👍', 'name': 'فيس بوك', 'pattern': r'(facebook\.com|fb\.watch|fb\.com)'},
    'reddit': {'emoji': '🤖', 'name': 'ريديت', 'pattern': r'reddit\.com'},
    'tiktok_live': {'emoji': '🎤', 'name': 'تيك توك لايف', 'pattern': r'live\.tiktok\.com'},
    'snapchat': {'emoji': '👻', 'name': 'سناب تشات', 'pattern': r'snapchat\.com'},
    'pinterest': {'emoji': '📌', 'name': 'بينتريست', 'pattern': r'pinterest\.com'},
    'twitch': {'emoji': '🎮', 'name': 'تويتش', 'pattern': r'twitch\.tv'},
}

def get_random_message(category):
    """اختار رسالة عشوائية"""
    return random.choice(MESSAGES.get(category, MESSAGES['error']))

def detect_platform(url):
    """الكشف عن المنصة"""
    for platform, info in PLATFORMS.items():
        if re.search(info['pattern'], url, re.IGNORECASE):
            return platform, info
    return None, {'emoji': '🌐', 'name': 'موقع', 'pattern': r'https?://'}

def extract_urls(text):
    """استخراج الروابط"""
    return re.findall(r'https?://[^\s]+', text)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر البداية"""
    welcome_msg = get_random_message('welcome')
    await update.message.reply_text(welcome_msg)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر المساعدة"""
    help_text = (
        "يلا يا عم! 🔥\n\n"
        "1️⃣ ارسل الرابط\n"
        "2️⃣ اختر (صوت 🎧 | فيديو 🎬 | صور 📸)\n"
        "3️⃣ استقبل الملف\n\n"
        "بدون علامات مائية! 💯"
    )
    await update.message.reply_text(help_text)

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الروابط"""
    text = update.message.text
    urls = extract_urls(text)
    
    if not urls:
        await update.message.reply_text("🔗 شنو الحاجة يا وحش؟ ارسل رابط!")
        return
    
    url = urls[0]
    platform, platform_info = detect_platform(url)
    
    if not platform:
        platform_info = {'emoji': '🌐', 'name': 'موقع'}
    
    # حفظ البيانات
    context.user_data['url'] = url
    context.user_data['platform'] = platform
    context.user_data['platform_info'] = platform_info
    
    # عرض الخيارات
    keyboard = [
        [InlineKeyboardButton("🎧 صوت بس", callback_data='audio')],
        [InlineKeyboardButton("🎬 فيديو كامل", callback_data='video')],
        [InlineKeyboardButton("📸 صور", callback_data='image')]
    ]
    
    await update.message.reply_text(
        f"{platform_info['emoji']} **{platform_info['name']}**\n\n"
        "وش بتبي يا حمقة؟",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def download_media(url, media_type):
    """تحميل الملف"""
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
                'retries': 5,
            }
        elif media_type == 'image':
            ydl_opts = {
                'format': 'images',
                'outtmpl': os.path.join(temp_dir, 'image_%(id)s.%(ext)s'),
                'quiet': True,
                'no_warnings': True,
                'socket_timeout': 60,
                'retries': 5,
            }
        else:  # video
            ydl_opts = {
                'format': 'best[ext=mp4]/best[ext=webm]/best',
                'outtmpl': os.path.join(temp_dir, 'video_%(id)s.%(ext)s'),
                'quiet': True,
                'no_warnings': True,
                'socket_timeout': 60,
                'retries': 5,
                'merge_output_format': 'mp4',
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
    """معالج الأزرار"""
    query = update.callback_query
    await query.answer()
    
    url = context.user_data.get('url')
    platform_info = context.user_data.get('platform_info', {'emoji': '🌐', 'name': 'موقع'})
    
    if not url:
        await query.edit_message_text("❌ خطأ يا وحش")
        return
    
    media_type = query.data
    emoji_map = {'audio': '🎧', 'video': '🎬', 'image': '📸'}
    emoji = emoji_map.get(media_type, '📥')
    
    # رسالة التحميل
    processing_msg = get_random_message('processing')
    await query.edit_message_text(f"{emoji} {processing_msg}")
    
    # تحميل الملف
    filename, info = await download_media(url, media_type)
    
    if not filename:
        error_msg = get_random_message('error')
        await query.edit_message_text(f"❌ {error_msg}")
        return
    
    try:
        # رسالة الإرسال
        success_msg = get_random_message('success')
        await query.edit_message_text(f"📤 {success_msg}")
        
        title = info.get('title', 'Media')[:50] if info else 'Media'
        
        # إرسال الملف
        if media_type == 'video':
            with open(filename, 'rb') as f:
                await query.message.reply_video(
                    video=f,
                    caption=f"🎬 {title}",
                    supports_streaming=True,
                    write_timeout=600
                )
        elif media_type == 'audio':
            with open(filename, 'rb') as f:
                await query.message.reply_audio(
                    audio=f,
                    caption=f"🎧 {title}",
                    write_timeout=600
                )
        else:  # image
            with open(filename, 'rb') as f:
                await query.message.reply_photo(
                    photo=f,
                    caption=f"📸 {title}"
                )
        
        await query.edit_message_text("✅ تمام! استمتع يا وحش 💪")
        
        # حذف الملف
        if os.path.exists(filename):
            os.remove(filename)
            
    except Exception as e:
        logger.error(f"Send error: {e}")
        await query.edit_message_text("❌ خطأ في الإرسال يا عم")
        if os.path.exists(filename):
            os.remove(filename)

def main():
    """تشغيل البوت"""
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    
    if not token:
        logger.error("❌ لا يوجد توكن!")
        return
    
    app = Application.builder().token(token).build()
    
    # الأوامر
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    
    # معالجات الرسائل والأزرار
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    
    logger.info("🚀 @vD7m01_Bot يعمل! 🔥")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
