#!/usr/bin/env python3
"""
تست سایز فونت
"""
from PIL import Image, ImageDraw, ImageFont
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from bot import fit_font_size, wrap_text_to_width

# تنظیمات
persian_text = "سلام دنیا"
english_text = "Hello World"
persian_font = "fonts/Vazirmatn-Regular.ttf"
english_font = "fonts/Roboto-Regular.ttf"

padding = 28
canvas_w, canvas_h = 512, 512
box_w, box_h = canvas_w - 2 * padding, canvas_h - 2 * padding
base_size = 128  # large

print(f"Canvas: {canvas_w}x{canvas_h}")
print(f"Box: {box_w}x{box_h}")
print(f"Base size: {base_size}\n")

# تست فارسی
print("=== تست فارسی ===")
img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)
final_size = fit_font_size(draw, persian_text, persian_font, base_size, box_w, box_h)
print(f"متن: {persian_text}")
print(f"سایز نهایی: {final_size}")

font = ImageFont.truetype(persian_font, size=final_size)
lines = wrap_text_to_width(draw, persian_text, font, box_w)
print(f"تعداد خطوط: {len(lines)}")
print(f"خطوط: {lines}")

# تست انگلیسی
print("\n=== تست انگلیسی ===")
img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)
final_size = fit_font_size(draw, english_text, english_font, base_size, box_w, box_h)
print(f"متن: {english_text}")
print(f"سایز نهایی: {final_size}")

font = ImageFont.truetype(english_font, size=final_size)
lines = wrap_text_to_width(draw, english_text, font, box_w)
print(f"تعداد خطوط: {len(lines)}")
print(f"خطوط: {lines}")