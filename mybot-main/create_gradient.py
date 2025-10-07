#!/usr/bin/env python3
"""
اسکریپت ساخت تصویر گرادیانت پیش‌فرض برای پس‌زمینه استیکرها
"""

from PIL import Image, ImageDraw, ImageFilter
import os

def create_gradient(size=(512, 512), output_path="templates/gradient.png"):
    """ساخت یک تصویر گرادیانت آبی-بنفش"""
    w, h = size
    img = Image.new("RGBA", size, (20, 20, 35, 255))

    # رنگ‌های گرادیانت
    top = (56, 189, 248)      # آبی روشن
    bottom = (99, 102, 241)   # بنفش

    dr = ImageDraw.Draw(img)

    # ساخت گرادیانت خط به خط
    for y in range(h):
        t = y / (h - 1)
        r = int(top[0] * (1 - t) + bottom[0] * t)
        g = int(top[1] * (1 - t) + bottom[1] * t)
        b = int(top[2] * (1 - t) + bottom[2] * t)
        dr.line([(0, y), (w, y)], fill=(r, g, b, 255))

    # اعمال محو خفیف برای نرم‌تر شدن
    img = img.filter(ImageFilter.GaussianBlur(0.5))

    # ذخیره تصویر
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, format="PNG", optimize=True)
    print(f"✅ فایل {output_path} با موفقیت ساخته شد")

if __name__ == "__main__":
    create_gradient()
