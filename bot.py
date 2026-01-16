import asyncio
import logging
import os
import re
from typing import Optional
import tempfile
from pathlib import Path

# استيراد مكتبات aiogram
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode, ChatAction
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

# تحميل المتغيرات البيئية (للتطوير المحلي)
load_dotenv()

# ═════════════════════════════════════════
# 🔧 إعدادات البوت
# ═════════════════════════════════════════

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    # رسالة تنبيه إذا التوكن غير موجود
    print("❌ تنبيه: لم يتم العثور على TELEGRAM_BOT_TOKEN في متغيرات البيئة.")

# إعدادات التسجيل (Logging) لمعرفة الأخطاء
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ═════════════════════════════════════════
# 🎭 حالات FSM (إدارة المحادثة)
# ═════════════════════════════════════════

class DownloadStates(StatesGroup):
    """حالات عملية التحميل"""
    waiting_for_url = State()
    processing_url = State()

# ═════════════════════════════════════════
# 🛠️ دوال مساعدة (yt-dlp)
# ═════════════════════════════════════════

def validate_url(url: str) -> bool:
    """التحقق من أن النص هو رابط صحيح"""
    url_pattern = re.compile(
        r'https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # or IP
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return bool(url_pattern.match(url))

async def extract_media_info(url: str) -> Optional[dict]:
    """استخراج معلومات الفيديو (العنوان، المدة...) بدون تحميل"""
    try:
        cmd = [
            'yt-dlp',
            '--dump-json',
            '--no-warnings',
            '--no-check-certificates', # لتجنب مشاكل شهادات SSL
            '--geo-bypass', # لتجاوز الحجب الجغرافي البسيط
            url
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            logger.error(f"Error extracting info: {stderr.decode()}")
            return None
        
        import json
        info = json.loads(stdout.decode())
        return info
        
    except Exception as e:
        logger.error(f"Exception in extraction: {str(e)}")
        return None

async def download_media(url: str, download_type: str) -> Optional[str]:
    """
    تحميل الوسائط وحفظها في مجلد مؤقت
    download_type: 'audio' | 'video' | 'images'
    """
    try:
        # إنشاء مجلد مؤقت فريد لكل عملية تحميل
        temp_dir = tempfile.mkdtemp()
        output_template = os.path.join(temp_dir, '%(title).100s.%(ext)s') # تقصير الاسم لتجنب أخطاء النظام
        
        cmd = []
        
        if download_type == 'audio':
            # تحميل صوت MP3
            cmd = [
                'yt-dlp',
                '-x', # استخراج صوت
                '--audio-format', 'mp3',
                '--audio-quality', '192',
                '--no-check-certificates',
                '-o', output_template,
                url
            ]
            
        elif download_type == 'video':
            # تحميل فيديو MP4 (أفضل جودة متوافقة)
            cmd = [
                'yt-dlp',
                '-f', 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                '--no-check-certificates',
                '-o', output_template,
                url
            ]
            
        elif download_type == 'images':
            # تحميل الصورة المصغرة (Thumbnail) كبديل للصور
            # ملاحظة: yt-dlp ليس الأفضل لسحب ألبومات الصور، لكنه جيد للصور المصغرة
            cmd = [
                'yt-dlp',
                '--write-thumbnail',
                '--skip-download', # لا تحمل الفيديو
                '--convert-thumbnail', 'jpg',
                '--no-check-certificates',
                '-o', output_template,
                url
            ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # الانتظار بحد أقصى 5 دقائق للتحميل
        try:
            _, stderr = await asyncio.wait_for(process.communicate(), timeout=300)
        except asyncio.TimeoutError:
            process.kill()
            logger.error("Download timed out")
            return None
        
        if process.returncode != 0:
            logger.error(f"Download failed: {stderr.decode()}")
            return None
        
        # البحث عن الملف الناتج في المجلد المؤقت
        files = list(Path(temp_dir).glob('*'))
        # استبعاد ملفات json أو temp إذا وجدت
        valid_files = [f for f in files if f.suffix.lower() in ['.mp3', '.mp4', '.jpg', '.png', '.m4a']]
        
        if valid_files:
            return str(valid_files[0])
        
        return None
            
    except Exception as e:
        logger.error(f"Exception in download: {str(e)}")
        return None

# ═════════════════════════════════════════
# 🤖 معالجات البوت (Handlers)
# ═════════════════════════════════════════

async def start_handler(message: Message, state: FSMContext):
    """الترحيب عند ضغط /start"""
    await state.clear()
    
    welcome_text = (
        "<b>ارحب تراحيب المطر! 🫡🌧️</b>\n\n"
        "معك بوت <b>@vD7m01_Bot</b> لتحميل أي شي بخاطرك من السوشل ميديا.\n\n"
        "⚡ <b>وش تبي تسوي؟</b>\n"
        "1️⃣ ارسلي أي رابط (تيك توك، يوتيوب، انستا...).\n"
        "2️⃣ بطلع لك خيارات (صوت 🎵، فيديو 🎬، صور 🖼️).\n"
        "3️⃣ وازهل الباقي علي!\n\n"
        "يا وحش، هات الرابط وخلنا نبدأ! 🔥"
    )
    
    await message.answer(welcome_text, parse_mode=ParseMode.HTML)

async def message_handler(message: Message, state: FSMContext):
    """استقبال الروابط"""
    text = message.text.strip()
    
    if not validate_url(text):
        await message.reply("يا غالي هذا مو رابط! 🤔\nتأكد وارسلي رابط زي الناس وابشر.")
        return

    # رسالة انتظار
    status_msg = await message.answer("⏳ <b>اصبر شويات، جالس أفحص الرابط...</b>", parse_mode=ParseMode.HTML)
    
    # استخراج المعلومات
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    info = await extract_media_info(text)
    
    if not info:
        await status_msg.edit_text("❌ <b>المعذرة يا وحش، ما قدرت أجيب الملف.</b>\nتأكد الرابط شغال أو الحساب عام.")
        return
    
    # تخزين الرابط والمعلومات مؤقتاً
    await state.update_data(url=text, title=info.get('title', 'media'))
    
    # لوحة الأزرار
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎵 صوت بس", callback_data="dl_audio"),
            InlineKeyboardButton(text="🎬 فيديو كامل", callback_data="dl_video")
        ],
        [
            InlineKeyboardButton(text="🖼️ صور/بوستر", callback_data="dl_images")
        ],
        [
            InlineKeyboardButton(text="❌ خلاص بطلت", callback_data="cancel")
        ]
    ])
    
    title = info.get('title', 'بدون عنوان')
    # تقصير العنوان للعرض
    display_title = (title[:50] + '..') if len(title) > 50 else title
    
    await status_msg.edit_text(
        f"✅ <b>لقيت المقطع!</b>\n\n"
        f"📌 <b>العنوان:</b> {display_title}\n\n"
        f"<b>آمر وتدلل، وش تبي أحمل لك؟ 👇</b>",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )

async def callback_handler(callback: CallbackQuery, state: FSMContext):
    """التعامل مع ضغطات الأزرار"""
    action = callback.data
    
    if action == "cancel":
        await callback.message.edit_text("تم الإلغاء يا ذيبان 👋")
        await state.clear()
        return

    # تحديد النوع
    dtype = ""
    action_text = ""
    if action == "dl_audio":
        dtype = "audio"
        action_text = "🎵 جاري سحب الصوت..."
    elif action == "dl_video":
        dtype = "video"
        action_text = "🎬 جاري تحميل الفيديو..."
    elif action == "dl_images":
        dtype = "images"
        action_text = "🖼️ جاري سحب الصور..."
    
    await callback.message.edit_text(f"⏳ <b>{action_text}</b>\n\nروق شوي واستمتع ☕", parse_mode=ParseMode.HTML)
    
    # جلب الرابط من الذاكرة
    data = await state.get_data()
    url = data.get("url")
    
    if not url:
        await callback.message.edit_text("❌ انتهت الجلسة، ارسل الرابط مرة ثانية.")
        return

    # بدء التحميل
    await callback.bot.send_chat_action(callback.message.chat.id, ChatAction.UPLOAD_DOCUMENT)
    
    file_path = await download_media(url, dtype)
    
    if not file_path:
        await callback.message.edit_text("❌ <b>صار خطأ وقت التحميل!</b>\nيمكن الملف حجمه كبير مرة أو السيرفر مزحوم.")
        return
    
    # إرسال الملف
    try:
        await callback.message.edit_text("🚀 <b>جاري الرفع لك...</b>", parse_mode=ParseMode.HTML)
        
        media_file = FSInputFile(file_path)
        caption = "<b>استمتع يا وحش! 🔥</b>\n🤖 @vD7m01_Bot"
        
        if dtype == "audio":
            await callback.message.answer_audio(media_file, caption=caption, parse_mode=ParseMode.HTML)
        elif dtype == "video":
            await callback.message.answer_video(media_file, caption=caption, parse_mode=ParseMode.HTML)
        elif dtype == "images":
            await callback.message.answer_photo(media_file, caption=caption, parse_mode=ParseMode.HTML)
            
        # حذف رسالة الانتظار
        await callback.message.delete()
        
    except Exception as e:
        logger.error(f"Error sending file: {e}")
        await callback.message.answer("❌ ما قدرت أرسل الملف، تأكد من حجمه.")
    finally:
        # تنظيف: حذف الملف والمجلد المؤقت
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                # محاولة حذف المجلد الأب (temp dir)
                os.rmdir(os.path.dirname(file_path))
        except Exception as e:
            logger.error(f"Error cleaning up: {e}")
        
        await state.clear()

# ═════════════════════════════════════════
# 🚀 نقطة التشغيل الرئيسية
# ═════════════════════════════════════════

async def main():
    # التأكد من التوكن
    if not TOKEN:
        logger.critical("Bot token is missing! Please set TELEGRAM_BOT_TOKEN.")
        return

    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # تسجيل الدوال
    dp.message.register(start_handler, CommandStart())
    dp.callback_query.register(callback_handler, F.data.in_({"dl_audio", "dl_video", "dl_images", "cancel"}))
    dp.message.register(message_handler) # أي رسالة نصية أخرى نعتبرها رابط

    logger.info("🚀 Bot is starting...")
    
    # حذف الـ Webhook في حال كان موجوداً سابقاً (لضمان عمل Polling)
    await bot.delete_webhook(drop_pending_updates=True)
    
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
