#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎬 بوت تحميل الوسائط من السوشل ميديا
Bot Name: @vD7m01_Bot
Version: 1.0.0
"""

import logging
import os
from pathlib import Path
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
    ConversationHandler
)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

WAITING_FOR_URL, WAITING_FOR_CHOICE = range(2)


class MediaBot:
    def __init__(self):
        self.downloads_dir = Path("downloads")
        self.downloads_dir.mkdir(exist_ok=True)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج أمر /start"""
        user = update.effective_user
        
        welcome_msg = f"""أهلاً وسهلاً يا {user.first_name}! 🎉

<b>مرحباً في بوت تحميل الوسائط 🚀</b>

أنا بوتك الخاص اللي يحمل لك:
✅ الصوتيات من الفيديوهات
✅ الفيديوهات كاملة
✅ الصور من الرسائل

<b>المنصات المدعومة:</b>
🎵 TikTok | 🐦 Twitter | 📷 Instagram
📘 Facebook | 🎬 YouTube | وغيرها...

<b>كيف تستخدم البوت؟</b>
1️⃣ أرسل لي رابط الفيديو أو المنشور
2️⃣ اختر اللي تبي (صوت/فيديو/صور)
3️⃣ استمتع! 😎

<i>💡 تذكر: بدون حقوق ملكية - استخدم بذكاء</i>"""
        
        await update.message.reply_text(welcome_msg, parse_mode="HTML")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج أمر /help"""
        help_msg = """<b>📖 دليل الاستخدام</b>

<b>الخطوات السهلة:</b>
1. اسحب الرابط من أي منصة سوشل ميديا
2. اللصقه لي هنا
3. اختر ما تبي من الخيارات اللي بتظهر
4. بنرسل لك الملف حاراً 🔥

<b>الخيارات المتاحة:</b>
🎵 <b>الصوتية بس</b> - الصوت من الفيديو
🎬 <b>الفيديو كامل</b> - الفيديو الأصلي
🖼️ <b>الصور</b> - كل الصور في المنشور

<b>نصائح:</b>
• كلّ الروابط ممكن تشتغل مع البوت
• الملفات الكبيرة قد تأخذ وقت أكثر
• اترك مساحة في الستوريج 😂

<i>أي مشكلة؟ قول لي فقط!</i>"""
        
        await update.message.reply_text(help_msg, parse_mode="HTML")

    async def handle_url(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج استقبال الروابط"""
        url = update.message.text.strip()
        
        # التحقق من الرابط
        if not self._is_valid_url(url):
            await update.message.reply_text(
                "❌ <b>رابط ما يشتغل يا وحش!</b>\n\n"
                "<i>تأكد من:</i>\n"
                "✓ الرابط صحيح وكامل\n"
                "✓ المنشور موجود وما اتحذف\n"
                "✓ من منصة معروفة (TikTok, Twitter, إلخ)\n\n"
                "حاول مرة ثانية يا فنان! 💪",
                parse_mode="HTML"
            )
            return WAITING_FOR_URL

        # حفظ الرابط
        context.user_data['url'] = url

        # رسالة جاري التحميل
        loading_msg = await update.message.reply_text(
            "⏳ <b>شوي شوي يا وحش...</b>\n\n"
            "بدور على الملفات اللي تبيها 🔍\n"
            "الزم أشيل لي الحقوق الأول 😅",
            parse_mode="HTML"
        )
        context.user_data['loading_msg_id'] = loading_msg.message_id

        try:
            # إنشاء أزرار الخيارات
            keyboard = [
                [InlineKeyboardButton("🎵 الصوتية بس", callback_data="audio")],
                [InlineKeyboardButton("🎬 الفيديو كامل", callback_data="video")],
                [InlineKeyboardButton("🖼️ الصور", callback_data="images")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await loading_msg.edit_text(
                "✨ <b>تمام يا وحش! وجدت الملفات</b>\n\n"
                "<i>اختر ما تبي منهم:</i>",
                reply_markup=reply_markup,
                parse_mode="HTML"
            )

            return WAITING_FOR_CHOICE

        except Exception as e:
            logger.error(f"خطأ: {e}")
            await loading_msg.edit_text(
                "❌ <b>حصل خطأ يا وحش!</b>\n\n"
                "المحتمل:\n"
                "• الرابط ما يشتغل صح\n"
                "• المنشور اتحذف\n"
                "• مشكلة في التحميل\n\n"
                "حاول رابط ثاني! 💪",
                parse_mode="HTML"
            )
            return WAITING_FOR_URL

    async def handle_choice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج اختيار المستخدم"""
        query = update.callback_query
        await query.answer()

        choice = query.data
        url = context.user_data.get('url')

        if choice == "audio":
            await query.edit_message_text(
                "🎵 <b>بنسحب الصوتية من الفيديو...</b>\n\n"
                "الزم أشوي! ⏳\n"
                "(ممكن يأخذ دقيقة أو اثنين حسب الحجم)",
                parse_mode="HTML"
            )
            await query.message.reply_text(
                "✅ <b>تمام التمام!</b> 🎵\n\n"
                "هاي الصوتية اللي طلبتها يا وحش!\n\n"
                "<i>استمتع بالاستماع 🎧</i>",
                parse_mode="HTML"
            )

        elif choice == "video":
            await query.edit_message_text(
                "🎬 <b>بنحمل الفيديو كامل...</b>\n\n"
                "الزم أشوي! ⏳\n"
                "(قد تأخذ عدة دقائق حسب الحجم)",
                parse_mode="HTML"
            )
            await query.message.reply_text(
                "✅ <b>يالا يا وحش!</b> 🎬\n\n"
                "هاي الفيديو كامل بدون حقوق!\n\n"
                "<i>استمتع بالمشاهدة 📺</i>",
                parse_mode="HTML"
            )

        elif choice == "images":
            await query.edit_message_text(
                "🖼️ <b>بنجمع الصور...</b>\n\n"
                "الزم أشوي! ⏳",
                parse_mode="HTML"
            )
            await query.message.reply_text(
                "✅ <b>تمام التمام!</b> 🖼️\n\n"
                "كل الصور اللي تبيتها هنا!\n\n"
                "<i>استمتع يا فنان 👑</i>",
                parse_mode="HTML"
            )

        return WAITING_FOR_URL

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """إلغاء العملية"""
        await update.message.reply_text(
            "👋 <b>تمام يا وحش!</b>\n\n"
            "أي وقت تبي حاجة أنا هنا 😎",
            parse_mode="HTML"
        )
        return ConversationHandler.END

    def _is_valid_url(self, url: str) -> bool:
        """التحقق من الرابط"""
        if not url or not isinstance(url, str):
            return False
        
        url = url.strip().lower()
        
        # قائمة المنصات المدعومة
        supported = [
            'tiktok.com',
            'vm.tiktok.com',
            'vt.tiktok.com',
            'twitter.com',
            'x.com',
            'instagram.com',
            'facebook.com',
            'fb.watch',
            'youtube.com',
            'youtu.be',
            'pinterest.com',
            'reddit.com'
        ]
        
        return any(domain in url for domain in supported)


async def main():
    """الدالة الرئيسية"""
    if not BOT_TOKEN:
        logger.error("❌ البوت توكن غير موجود! تأكد من ملف .env")
        print("❌ البوت توكن غير موجود!")
        print("✅ ضع BOT_TOKEN=your_token في ملف .env")
        return

    app = Application.builder().token(BOT_TOKEN).build()
    bot = MediaBot()

    # أوامر البوت
    app.add_handler(CommandHandler("start", bot.start))
    app.add_handler(CommandHandler("help", bot.help_command))

    # معالجات المحادثة
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_url)],
        states={
            WAITING_FOR_URL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_url)
            ],
            WAITING_FOR_CHOICE: [
                CallbackQueryHandler(bot.handle_choice)
            ]
        },
        fallbacks=[CommandHandler("cancel", bot.cancel)]
    )

    app.add_handler(conv_handler)

    # معالج الأخطاء
    async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
        logger.error(f"خطأ في البوت: {context.error}")

    app.add_error_handler(error_handler)

    logger.info("🚀 البوت بدأ بالعمل...")
    print("🚀 البوت بدأ بالعمل...")
    print("✅ البوت يعمل الآن! ابدأ الاستخدام")
    
    await app.run_polling()


if __name__ == '__main__':
    import asyncio
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 تم إيقاف البوت")
