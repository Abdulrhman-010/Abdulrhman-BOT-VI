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
    'version': 'v1.0',
    'developer': 'عبدالرحمن العنزي',
    'email': 'aalanzi@azmx.sa',
    'date': 'ديسمبر 2025'
}

SUPPORTED_PATTERNS = {
    'tiktok': r'(tiktok\.com|vm\.tiktok\.com)',
    'instagram': r'(instagram\.com|instagr\.am)',
    'youtube': r'(youtube\.com|youtu\.be)',
    'twitter': r'(twitter\.com|x\.com)',
    'facebook': r'(facebook\.com|fb\.watch)',
}

MESSAGES = {
    'welcome': ["🎬 أهلاً وسهلاً! أنا بوت تحميل الفيديوهات ✨"],
    'processing': ["⏳ جاري التحميل... انتظر شوي 🔄"],
    'success': ["✅ تفضل! المقطع جاهز بدون علامة مائية 🎉"],
    'error': ["😅 معذرة، ما قدرت أحمّل هذا الرابط"],
}

import random
def get_random_message(category):
    return random.choice(MESSAGES.get(category, ['🤔']))

def detect_platform(url):
    for platform, pattern in SUPPORTED_PATTERNS.items():
        if re.search(pattern, url, re.IGNORECASE):
            return platform
    return None

def extract_urls(text):
    return re.findall(r'https?://[^\s]+', text)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = f"""
🎬 **مرحباً بك في {BOT_INFO['name']}!**

✨ أنا بوت تحميل الفيديوهات الاحترافي

📱 **المنصات:**
• TikTok 🎵 • Instagram 📸 • YouTube 🎥
• Twitter 🐦 • Facebook 📘

🚀 **كيف تستخدمني:**
فقط أرسل رابط الفيديو وأنا بحمّله!

━━━━━━━━━━━━━━━━━━
👨‍💻 {BOT_INFO['developer']}
📧 {BOT_INFO['email']}
🔢 {BOT_INFO['version']}
━━━━━━━━━━━━━━━━━━
    """
    keyboard = [[InlineKeyboardButton("📖 المساعدة", callback_data='help')]]
    await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
📖 **دليل الاستخدام:**
1️⃣ انسخ رابط الفيديو
2️⃣ أرسله هنا
3️⃣ انتظر ثواني
4️⃣ استلم الفيديو! 🎉
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    urls = extract_urls(text)
    
    if not urls:
        await update.message.reply_text("🔗 أرسل لي رابط فيديو!")
        return
    
    for url in urls:
        platform = detect_platform(url)
        if not platform:
            await update.message.reply_text("🤔 هذا الرابط مو مدعوم")
            continue
        
        msg = await update.message.reply_text(f"⏳ جاري تحميل من {platform.upper()}...")
        
        try:
            ydl_opts = {
                'format': 'best[ext=mp4]/best',
                'outtmpl': f'{tempfile.gettempdir()}/%(id)s.%(ext)s',
                'quiet': True,
                'no_warnings': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                
                if os.path.exists(filename):
                    file_size = os.path.getsize(filename)
                    
                    if file_size > 50 * 1024 * 1024:
                        await msg.edit_text("⚠️ حجم الفيديو كبير جداً (أكثر من 50MB)")
                        os.remove(filename)
                        continue
                    
                    await msg.edit_text("📤 جاري الإرسال...")
                    
                    caption = f"""✅ {get_random_message('success')}
📱 المنصة: {platform.upper()}
📁 الحجم: {file_size / (1024*1024):.1f} MB
🤖 @Abdulrhman_VI_bot"""
                    
                    with open(filename, 'rb') as f:
                        await update.message.reply_video(video=f, caption=caption, supports_streaming=True)
                    
                    await msg.delete()
                    os.remove(filename)
                else:
                    await msg.edit_text("❌ ما قدرت أحمّل الفيديو")
                    
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            await msg.edit_text(f"❌ خطأ: {str(e)[:50]}")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'help':
        await query.edit_message_text("📖 **الاستخدام:** أرسل رابط الفيديو وأنا بحمّله لك!", parse_mode='Markdown')

def main():
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("❌ TELEGRAM_BOT_TOKEN not found")
        return
    
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("🚀 Bot is running!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
