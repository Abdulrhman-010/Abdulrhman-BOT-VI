#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
سكريبت تشغيل البوت
"""

import subprocess
import sys
import os

print("""
╔═══════════════════════════════════════════════════╗
║         🎬 بوت تحميل الوسائط من السوشل ميديا        ║
║                @vD7m01_Bot v1.0.0                ║
╚═══════════════════════════════════════════════════╝
""")

# التحقق من Python
if sys.version_info < (3, 9):
    print("❌ Python 3.9+ مطلوب!")
    sys.exit(1)

print(f"✅ Python {sys.version.split()[0]}")

# التحقق من المتطلبات
try:
    import telegram
    print("✅ python-telegram-bot مثبت")
except ImportError:
    print("❌ python-telegram-bot غير مثبت")
    print("   شغل: pip install -r requirements.txt")
    sys.exit(1)

try:
    import dotenv
    print("✅ python-dotenv مثبت")
except ImportError:
    print("❌ python-dotenv غير مثبت")
    print("   شغل: pip install -r requirements.txt")
    sys.exit(1)

# التحقق من .env
if not os.path.exists('.env'):
    print("❌ ملف .env غير موجود!")
    print("   انسخ .env.example إلى .env")
    print("   وضع التوكن فيه")
    sys.exit(1)

from dotenv import load_dotenv
load_dotenv()

token = os.getenv('BOT_TOKEN')
if not token or token == 'YOUR_BOT_TOKEN_HERE':
    print("❌ البوت توكن غير موجود أو فارغ!")
    print("   عدّل .env وضع التوكن الحقيقي")
    sys.exit(1)

print(f"✅ البوت توكن موجود")

# إنشاء مجلد التحميلات
os.makedirs('downloads', exist_ok=True)
print("✅ مجلد التحميلات جاهز")

print("\n" + "="*50)
print("✅ كل الإعدادات جاهزة!")
print("="*50)
print("\n🚀 شغل: python main.py\n")

# تشغيل البوت
print("⏳ جاري تشغيل البوت...\n")
subprocess.run([sys.executable, "main.py"])
