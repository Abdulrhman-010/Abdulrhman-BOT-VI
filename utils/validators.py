# -*- coding: utf-8 -*-
"""
التحقق من الروابط
"""

class URLValidator:
    SUPPORTED = [
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

    @staticmethod
    def is_valid(url):
        """التحقق من صحة الرابط"""
        if not url:
            return False
        
        url = url.strip().lower()
        return any(domain in url for domain in URLValidator.SUPPORTED)

    @staticmethod
    def get_platform(url):
        """الحصول على اسم المنصة"""
        url_lower = url.lower()
        
        if 'tiktok' in url_lower:
            return 'TikTok'
        elif 'twitter' in url_lower or 'x.com' in url_lower:
            return 'Twitter/X'
        elif 'instagram' in url_lower:
            return 'Instagram'
        elif 'facebook' in url_lower or 'fb.watch' in url_lower:
            return 'Facebook'
        elif 'youtube' in url_lower or 'youtu.be' in url_lower:
            return 'YouTube'
        elif 'pinterest' in url_lower:
            return 'Pinterest'
        elif 'reddit' in url_lower:
            return 'Reddit'
        else:
            return 'Unknown'
