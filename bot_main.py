import os
import re
import logging
import tempfile
import asyncio
from pathlib import Path
from typing import Optional
from io import BytesIO

import yt_dlp
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher(storage=MemoryStorage())

MESSAGES = {
    'welcome': [
        "🔥 هلا يا وحش! ارسلي الرابط وازهل 💨",
        "يلا يا عم! جاهز للتحميل السريع ⚡",
        "مرحباً يا كبير! شنو الرابط اللي تبيه؟ 🚀"
    ],
    'send_link': [
        "ارسلي الرابط وازهل يا وحش! 📲",
        "يلا، حط الرابط هنا وشوف السحر 🔥",
        "الرابط جاهز؟ ارسله واستمتع 💯"
    ],
    'processing': [
        "اصبر شويات... بنحملها لك يا بطل ⏳",
        "شوي ويجيك اللي تبي، اصبر يا وحش! 🔥",
        "جاري التحميل السريع... 🚀"
    ],
    'enjoy': [
        "استمتع يا وحش! 🔥",
        "خذ واستمتع يا كبير 💯",
        "هذا اللي تبيه، يلا العب! ⚡"
    ],
    'error': [
        "عذراً يا وحش، الرابط مو صالح أو مشكلة تحميل 😔\nجرب رابط ثاني!",
        "ما قدرنا نحمل، تأكد من الرابط يا عم! 🔄",
        "مشكلة في الرابط، ارسل واحد جديد 💪"
    ]
}

class DownloadStates(StatesGroup):
    waiting_link = State()

@dp.message(CommandStart())
async def start_handler(message: Message):
    msg = random.choice(MESSAGES['welcome'])
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎧 صوت", callback_data="audio")],
        [InlineKeyboardButton(text="🎬 فيديو", callback_data="video")],
        [InlineKeyboardButton(text="📸 صور", callback_data="images")]
    ])
    await message.answer(msg, reply_markup=keyboard)

@dp.callback_query(F.data == "audio")
async def audio_callback(callback: CallbackQuery):
    await callback.message.edit_text(random.choice(MESSAGES['send_link']))
    await dp.storage.set_state(callback.from_user.id, DownloadStates.waiting_link)
    await dp.storage.update_data(callback.from_user.id, download_type="audio")

@dp.callback_query(F.data == "video")
async def video_callback(callback: CallbackQuery):
    await callback.message.edit_text(random.choice(MESSAGES['send_link']))
    await dp.storage.set_state(callback.from_user.id, DownloadStates.waiting_link)
    await dp.storage.update_data(callback.from_user.id, download_type="video")

@dp.callback_query(F.data == "images")
async def images_callback(callback: CallbackQuery):
    await callback.message.edit_text(random.choice(MESSAGES['send_link']))
    await dp.storage.set_state(callback.from_user.id, DownloadStates.waiting_link)
    await dp.storage.update_data(callback.from_user.id, download_type="images")

@dp.message(DownloadStates.waiting_link, F.text)
async def process_link(message: Message, state: FSMContext):
    link = message.text.strip()
    if not re.match(r'https?://', link):
        await message.answer("هذا مو رابط يا وحش! ارسل رابط صحيح 📎")
        return

    data = await state.get_data()
    download_type = data.get('download_type')

    await message.answer(random.choice(MESSAGES['processing']))

    try:
        files = await download_media(link, download_type)
        if files:
            enjoy_msg = random.choice(MESSAGES['enjoy'])
            if isinstance(files, list):
                for file_path in files[:10]:  # حد أقصى 10 صور
                    await message.answer_document(FSInputFile(file_path), caption=enjoy_msg)
                    os.remove(file_path)
            else:
                await message.answer_video(files if files.endswith('.mp4') else files, caption=enjoy_msg)
                os.remove(files)
        else:
            await message.answer(random.choice(MESSAGES['error']))
    except Exception as e:
        logger.error(e)
        await message.answer(random.choice(MESSAGES['error']))
    finally:
        await state.clear()

async def download_media(url: str, media_type: str) -> Optional[str | list]:
    def hook(d):
        if d['status'] == 'downloading':
            pass  # يمكن إضافة progress هنا

    ydl_opts = {
        'outtmpl': '%(title)s.%(ext)s',
        'noplaylist': True,
        'quiet': True,
        'progress_hooks': [hook],
    }

    if media_type == 'audio':
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
    elif media_type == 'video':
        ydl_opts['format'] = 'best[height<=720]'
    elif media_type == 'images':
        # yt-dlp يدعم صور من بعض المنصات، أو استخدم gallery-dl لكن هنا بسيط
        ydl_opts.update({'writethumbnail': True})

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            if media_type == 'images' and info.get('_type') == 'url_transparent':
                # للصور، حمل الـ thumbnail أو صور متعددة
                ydl.download([url])
                files = [f for f in Path('.').glob('*.jpg') or Path('.').glob('*.png')]
                return [str(f) for f in files]
            else:
                ydl.download([url])
                files = [f for f in Path('.').glob('*.mp3') + Path('.').glob('*.mp4')]
                return files[0] if files else None
        except:
            return None

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
