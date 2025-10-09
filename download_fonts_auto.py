#!/usr/bin/env python3
"""
اسکریپت دانلود خودکار فونت‌های فارسی و انگلیسی
"""
import os
import urllib.request
import zipfile
import shutil

FONTS_DIR = "fonts"

# فونت‌های فارسی
PERSIAN_FONTS = {
    "Vazirmatn-Regular.ttf": "https://github.com/rastikerdar/vazirmatn/releases/download/v33.003/Vazirmatn-font-v33.003.zip",
    "IRANSans.ttf": "https://github.com/rastikerdar/iran-sans/releases/download/v5.0/iran-sans-v5.0.zip",
}

# فونت‌های انگلیسی
ENGLISH_FONTS = {
    "Roboto-Regular.ttf": "https://github.com/google/roboto/releases/download/v2.138/roboto-unhinted.zip",
    "OpenSans-Regular.ttf": "https://github.com/googlefonts/opensans/archive/refs/heads/main.zip",
}

def download_and_extract(url, target_font_name):
    """دانلود و استخراج فونت"""
    print(f"در حال دانلود {target_font_name}...")
    
    # دانلود فایل
    zip_path = f"/tmp/{target_font_name}.zip"
    urllib.request.urlretrieve(url, zip_path)
    
    # استخراج
    extract_dir = f"/tmp/{target_font_name}_extract"
    os.makedirs(extract_dir, exist_ok=True)
    
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    
    # جستجوی فایل ttf
    for root, dirs, files in os.walk(extract_dir):
        for file in files:
            if file.endswith('.ttf'):
                src = os.path.join(root, file)
                dst = os.path.join(FONTS_DIR, target_font_name)
                shutil.copy2(src, dst)
                print(f"✓ {target_font_name} کپی شد")
                return True
    
    print(f"✗ فایل ttf برای {target_font_name} پیدا نشد")
    return False

def main():
    # ایجاد پوشه fonts
    os.makedirs(FONTS_DIR, exist_ok=True)
    
    print("=== دانلود فونت‌های فارسی ===")
    for font_name, url in PERSIAN_FONTS.items():
        if not os.path.exists(os.path.join(FONTS_DIR, font_name)):
            download_and_extract(url, font_name)
        else:
            print(f"✓ {font_name} از قبل موجود است")
    
    print("\n=== دانلود فونت‌های انگلیسی ===")
    for font_name, url in ENGLISH_FONTS.items():
        if not os.path.exists(os.path.join(FONTS_DIR, font_name)):
            download_and_extract(url, font_name)
        else:
            print(f"✓ {font_name} از قبل موجود است")
    
    print("\n✓ همه فونت‌ها آماده هستند!")

if __name__ == "__main__":
    main()