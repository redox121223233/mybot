#!/usr/bin/env python3
"""
Simple and safe fix for the sticker bot
"""

def apply_simple_fix():
    with open('api/index.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix 1: Just change the send_document to send_sticker
    content = content.replace(
        'await context.bot.send_document(',
        'await context.bot.send_sticker('
    )
    
    # Fix 2: Change the document parameter to sticker
    content = content.replace(
        'document=InputFile(img_bytes_preview, "sticker.webp")',
        'sticker=InputFile(img_bytes_preview, "sticker.webp")'
    )
    
    # Fix 3: Simple caption update
    content = content.replace(
        'caption=f"🎨 **استیکر WebP شما!**\\\\n\\\\n⚠️ 📌 **نحوه اضافه کردن به پک:**\\\\n1. روی فایل بالا کلیک کنید\\\\n2. استیکر را ذخیره کنید\\\\n3. به پک خود اضافه کنید\\\\n\\\\n⚠️ این فایل WebP است و برای تلگرام بهینه شده است."',
        'caption="استیکر شما با فرمت WebP ارسال شد!"'
    )
    
    # Add improved function at the end
    if 'async def add_sticker_to_pack_improved' not in content:
        content += '''

async def add_sticker_to_pack_improved(context, user_id, pack_short_name, sticker_file_id):
    """Improved sticker addition with retry logic"""
    try:
        for attempt in range(3):
            try:
                if attempt > 0:
                    await asyncio.sleep(2 ** attempt)
                
                from telegram import InputSticker
                await context.bot.add_sticker_to_set(
                    user_id=user_id,
                    name=pack_short_name,
                    sticker=InputSticker(sticker=sticker_file_id, emoji_list=["😊"])
                )
                return True
            except Exception as e:
                if attempt < 2:
                    continue
                return False
        return False
    except:
        return False
'''
    
    with open('api/index.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Simple fixes applied!")

if __name__ == "__main__":
    apply_simple_fix()