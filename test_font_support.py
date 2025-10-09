#!/usr/bin/env python3
"""
تست پشتیبانی فونت از کاراکترهای فارسی
"""
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

# تست با فونت Vazirmatn
font_path = "fonts/Vazirmatn-Regular.ttf"
text = "سلام دنیا"

print(f"متن اصلی: {text}")
print(f"متن اصلی (repr): {repr(text)}")

# تست 1: بدون reshape
print("\n=== تست 1: بدون reshape ===")
img1 = Image.new("RGBA", (512, 512), (0, 0, 0, 255))
draw1 = ImageDraw.Draw(img1)
font1 = ImageFont.truetype(font_path, size=64)
draw1.text((256, 256), text, font=font1, fill=(255, 255, 255, 255), anchor="mm")
img1.save("test_no_reshape.png")
print("✅ ذخیره شد: test_no_reshape.png")

# تست 2: با reshape
print("\n=== تست 2: با reshape ===")
reshaped = arabic_reshaper.reshape(text)
print(f"بعد از reshape: {reshaped}")
print(f"بعد از reshape (repr): {repr(reshaped)}")

img2 = Image.new("RGBA", (512, 512), (0, 0, 0, 255))
draw2 = ImageDraw.Draw(img2)
font2 = ImageFont.truetype(font_path, size=64)
draw2.text((256, 256), reshaped, font=font2, fill=(255, 255, 255, 255), anchor="mm")
img2.save("test_with_reshape.png")
print("✅ ذخیره شد: test_with_reshape.png")

# تست 3: با reshape + bidi
print("\n=== تست 3: با reshape + bidi ===")
bidi_text = get_display(reshaped)
print(f"بعد از bidi: {bidi_text}")
print(f"بعد از bidi (repr): {repr(bidi_text)}")

img3 = Image.new("RGBA", (512, 512), (0, 0, 0, 255))
draw3 = ImageDraw.Draw(img3)
font3 = ImageFont.truetype(font_path, size=64)
draw3.text((256, 256), bidi_text, font=font3, fill=(255, 255, 255, 255), anchor="mm")
img3.save("test_with_bidi.png")
print("✅ ذخیره شد: test_with_bidi.png")

print("\n✅ همه تست‌ها تمام شد!")