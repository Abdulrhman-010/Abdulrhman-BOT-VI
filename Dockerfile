# استخدام صورة Python الرسمية
FROM python:3.11-slim

# تعيين مجلد العمل
WORKDIR /app

# تثبيت ffmpeg (مهم جداً لـ yt-dlp)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# نسخ ملفات المتطلبات
COPY requirements.txt .

# تثبيت المتطلبات
RUN pip install --no-cache-dir -r requirements.txt

# نسخ ملفات البوت
COPY bot_main.py .

# تشغيل البوت
CMD ["python", "bot_main.py"]
