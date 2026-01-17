# -*- coding: utf-8 -*-
"""
رسائل البوت
"""

class Messages:
    @staticmethod
    def welcome(name):
        return f"""أهلاً وسهلاً يا {name}! 🎉"""

    @staticmethod
    def start_msg():
        return """يالا يا وحش! 😎 
ارسل لي رابط وأحمله لك حاراً! 🔥"""

    @staticmethod
    def error():
        return """❌ حصل خطأ يا وحش!
حاول مرة ثانية 💪"""
