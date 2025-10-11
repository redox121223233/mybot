#!/usr/bin/env python3
"""
تست کامل عملکرد ربات استیکر فارسی
"""
import os
import sys
from bot import render_image, process_video_to_webm, add_text_to_video, _check_ffmpeg
import subprocess

def test_persian_stickers():
    """تست استیکرهای فارسی"""
    print("🎨 تست استیکرهای فارسی...")
    
    test_cases = [
        {"text": "سلام دنیا", "desc": "متن ساده فارسی"},
        {"text": "خوش آمدید\nبه ربات ما", "desc": "متن چند خطی فارسی"},
        {"text": "Hello سلام", "desc": "متن ترکیبی"},
        {"text": "تست فونت\nVazirmatn", "desc": "تست فونت مخصوص"}
    ]
    
    for i, case in enumerate(test_cases, 1):
        try:
            print(f"\n📝 تست {i}: {case['desc']}")
            print(f"   متن: {case['text']}")
            
            sticker_bytes = render_image(
                text=case['text'],
                position='center',
                font_key='Vazirmatn',
                color_hex='#FFFFFF',
                size_key='medium'
            )
            
            filename = f"final_test_sticker_{i}.png"
            with open(filename, 'wb') as f:
                f.write(sticker_bytes)
            
            print(f"   ✅ موفق: {filename}")
            
        except Exception as e:
            print(f"   ❌ خطا: {e}")

def test_video_stickers():
    """تست استیکرهای ویدیویی"""
    print("\n🎬 تست استیکرهای ویدیویی...")
    
    if not _check_ffmpeg():
        print("❌ FFmpeg موجود نیست")
        return
    
    # ایجاد ویدیو تست
    print("📹 ایجاد ویدیو تست...")
    result = subprocess.run([
        'ffmpeg', '-f', 'lavfi', '-i', 
        'testsrc=duration=3:size=512x512:rate=15',
        '-t', '3', '-y', 'video_test_input.mp4'
    ], capture_output=True)
    
    if result.returncode != 0:
        print("❌ ایجاد ویدیو تست ناموفق")
        return
    
    try:
        # تبدیل به WebM
        print("🔄 تبدیل به WebM...")
        with open('video_test_input.mp4', 'rb') as f:
            video_bytes = f.read()
        
        webm_bytes = process_video_to_webm(video_bytes, max_duration=3)
        
        # اضافه کردن متن فارسی
        print("✍️ اضافه کردن متن فارسی...")
        final_bytes = add_text_to_video(
            video_bytes=webm_bytes,
            text='استیکر ویدیویی\nفارسی',
            position='center',
            font_key='Vazirmatn',
            color_hex='#FFFFFF',
            size_key='large'
        )
        
        with open('final_video_sticker.webm', 'wb') as f:
            f.write(final_bytes)
        
        print("✅ استیکر ویدیویی فارسی آماده شد")
        print(f"   اندازه: {len(final_bytes)} بایت")
        
    except Exception as e:
        print(f"❌ خطا در ویدیو: {e}")

def test_font_loading():
    """تست بارگذاری فونت‌ها"""
    print("\n🔤 تست بارگذاری فونت‌ها...")
    
    from bot import _load_local_fonts, available_font_options
    
    fonts = _load_local_fonts()
    print("فونت‌های موجود:")
    for name, path in fonts.items():
        print(f"   ✅ {name}: {os.path.basename(path)}")
    
    options = available_font_options()
    print(f"\nگزینه‌های فونت: {len(options)} عدد")

def main():
    print("=" * 50)
    print("🚀 تست کامل ربات استیکر فارسی")
    print("=" * 50)
    
    # تست فونت‌ها
    test_font_loading()
    
    # تست استیکرهای عادی
    test_persian_stickers()
    
    # تست استیکرهای ویدیویی
    test_video_stickers()
    
    print("\n" + "=" * 50)
    print("🎉 تست کامل پایان یافت")
    print("=" * 50)

if __name__ == "__main__":
    main()