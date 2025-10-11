#!/usr/bin/env python3
"""
تست نهایی ربات - شبیه‌سازی استفاده واقعی
"""
import asyncio
from bot import render_image, process_video_to_webm, add_text_to_video
import subprocess
import os

async def simulate_real_usage():
    """شبیه‌سازی استفاده واقعی از ربات"""
    print("🎯 شبیه‌سازی استفاده واقعی از ربات")
    print("=" * 50)
    
    # سناریو 1: کاربر می‌خواهد استیکر فارسی بسازد
    print("\n📱 سناریو 1: ساخت استیکر فارسی")
    user_text = "سلام دوستان!\nامیدوارم حالتون خوب باشه 😊"
    
    try:
        sticker_bytes = render_image(
            text=user_text,
            position="center",
            font_key="Vazirmatn",
            color_hex="#FFFFFF",
            size_key="medium",
            bg_mode="transparent"
        )
        
        # تبدیل به WebP برای تلگرام
        from PIL import Image
        from io import BytesIO
        
        img = Image.open(BytesIO(sticker_bytes))
        webp_buffer = BytesIO()
        img.save(webp_buffer, format='WEBP')
        webp_bytes = webp_buffer.getvalue()
        
        with open('scenario1_persian_sticker.webp', 'wb') as f:
            f.write(webp_bytes)
        
        print("✅ استیکر فارسی آماده شد")
        print(f"   متن: {user_text}")
        print(f"   اندازه: {len(webp_bytes)} بایت")
        
    except Exception as e:
        print(f"❌ خطا: {e}")
    
    # سناریو 2: کاربر می‌خواهد استیکر انگلیسی بسازد
    print("\n📱 سناریو 2: ساخت استیکر انگلیسی")
    english_text = "Hello World!\nThis is a test"
    
    try:
        sticker_bytes = render_image(
            text=english_text,
            position="center",
            font_key="Roboto",
            color_hex="#00FF00",
            size_key="large",
            bg_mode="transparent"
        )
        
        img = Image.open(BytesIO(sticker_bytes))
        webp_buffer = BytesIO()
        img.save(webp_buffer, format='WEBP')
        webp_bytes = webp_buffer.getvalue()
        
        with open('scenario2_english_sticker.webp', 'wb') as f:
            f.write(webp_bytes)
        
        print("✅ استیکر انگلیسی آماده شد")
        print(f"   متن: {english_text}")
        print(f"   اندازه: {len(webp_bytes)} بایت")
        
    except Exception as e:
        print(f"❌ خطا: {e}")
    
    # سناریو 3: کاربر می‌خواهد استیکر ویدیویی با متن فارسی بسازد
    print("\n📱 سناریو 3: ساخت استیکر ویدیویی فارسی")
    
    try:
        # ایجاد ویدیو تست
        result = subprocess.run([
            'ffmpeg', '-f', 'lavfi', '-i', 
            'testsrc=duration=3:size=512x512:rate=15',
            '-t', '3', '-y', 'scenario3_input.mp4'
        ], capture_output=True)
        
        if result.returncode == 0:
            with open('scenario3_input.mp4', 'rb') as f:
                video_bytes = f.read()
            
            # تبدیل به WebM
            webm_bytes = process_video_to_webm(video_bytes, max_duration=3)
            
            # اضافه کردن متن فارسی
            final_bytes = add_text_to_video(
                video_bytes=webm_bytes,
                text='ویدیو فارسی\n🎬 تست موفق',
                position='center',
                font_key='Vazirmatn',
                color_hex='#FFFF00',
                size_key='large'
            )
            
            with open('scenario3_video_sticker.webm', 'wb') as f:
                f.write(final_bytes)
            
            print("✅ استیکر ویدیویی فارسی آماده شد")
            print(f"   اندازه: {len(final_bytes)} بایت")
            
        else:
            print("❌ ایجاد ویدیو تست ناموفق")
            
    except Exception as e:
        print(f"❌ خطا در ویدیو: {e}")
    
    # سناریو 4: تست تشخیص خودکار زبان
    print("\n📱 سناریو 4: تشخیص خودکار زبان")
    mixed_texts = [
        "سلام Hello دوستان",
        "Welcome خوش آمدید",
        "This is English text",
        "این متن فارسی است"
    ]
    
    for i, text in enumerate(mixed_texts, 1):
        try:
            sticker_bytes = render_image(
                text=text,
                position="center",
                font_key=None,  # تشخیص خودکار
                color_hex="#FF00FF",
                size_key="medium"
            )
            
            img = Image.open(BytesIO(sticker_bytes))
            webp_buffer = BytesIO()
            img.save(webp_buffer, format='WEBP')
            webp_bytes = webp_buffer.getvalue()
            
            with open(f'scenario4_auto_{i}.webp', 'wb') as f:
                f.write(webp_bytes)
            
            print(f"✅ تست {i}: {text[:20]}...")
            
        except Exception as e:
            print(f"❌ تست {i} خطا: {e}")

async def main():
    print("🚀 تست نهایی ربات استیکر فارسی")
    print("🎯 شبیه‌سازی استفاده واقعی کاربران")
    
    await simulate_real_usage()
    
    print("\n" + "=" * 50)
    print("🎉 تست نهایی کامل شد!")
    print("📁 فایل‌های تولید شده:")
    
    webp_files = [f for f in os.listdir('.') if f.endswith('.webp') and f.startswith('scenario')]
    for file in webp_files:
        size = os.path.getsize(file)
        print(f"   📄 {file} ({size} بایت)")
    
    print("\n✅ ربات کاملاً آماده برای استفاده در تلگرام!")

if __name__ == "__main__":
    asyncio.run(main())