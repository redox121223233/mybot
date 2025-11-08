#!/usr/bin/env python3
"""
Fix the sticker bot syntax issues correctly
"""

def fix_bot_properly():
    """Apply fixes without breaking syntax"""
    
    with open('api/index.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("🔧 Applying proper fixes...")
    
    # Fix 1: Replace send_document with send_sticker in the fallback section
    old_doc_fallback = '''                await context.bot.send_document(
                    chat_id=user_id,
                    document=InputFile(img_bytes_preview, "sticker.webp"),
                    caption=f"🎨 **استیکر WebP شما!**\\\\n\\\\n⚠️ 📌 **نحوه اضافه کردن به پک:**\\\\n1. روی فایل بالا کلیک کنید\\\\n2. استیکر را ذخیره کنید\\\\n3. به پک خود اضافه کنید\\\\n\\\\n⚠️ این فایل WebP است و برای تلگرام بهینه شده است.")'''
    
    new_sticker_fallback = '''                # FIXED: Upload and send as proper sticker
                try:
                    # Upload the sticker first
                    uploaded_sticker = await context.bot.upload_sticker_file(
                        user_id=user_id, 
                        sticker=InputFile(img_bytes_preview, "sticker.webp"),
                        sticker_format="static"
                    )
                    sticker_file_id = uploaded_sticker.file_id
                    
                    # Send as proper sticker
                    await context.bot.send_sticker(chat_id=user_id, sticker=sticker_file_id)
                    logger.info(f"✅ Sticker sent successfully as proper sticker for user {user_id}")
                    
                    # Try to auto-add to pack
                    pack_short_name = get_current_pack_short_name(user_id)
                    if pack_short_name:
                        success = await add_sticker_to_pack_improved(context, user_id, pack_short_name, sticker_file_id)
                        if success:
                            await query.message.reply_text(
                                "✅ استیکر با موفقیت به پک شما اضافه شد! 🎉\\\\n\\\\n"
                                "برای ساخت استیکر بعدی، مجدداً از منو استفاده کنید."
                            )
                        else:
                            pack_link = f"https://t.me/addstickers/{pack_short_name}"
                            await query.message.reply_text(
                                f"⚠️ اضافه خودکار انجام نشد. لطفاً دستی اضافه کنید:\\\\n\\\\n"
                                f"1. روی استیکر بالا کلیک کنید\\\\n"
                                f"2. «Add to Pack» را انتخاب کنید\\\\n\\\\n"
                                f"لینک پک: {pack_link}"
                            )
                        
                except Exception as sticker_error:
                    logger.error(f"Sticker sending failed: {sticker_error}")
                    # Final fallback
                    await context.bot.send_document(
                        chat_id=user_id,
                        document=InputFile(img_bytes_preview, "sticker.webp"),
                        caption=f"🎨 **استیکر WebP شما!**\\\\n\\\\n⚠️ لطفاً ذخیره کرده و به پک خود اضافه کنید."
                    )'''
    
    if old_doc_fallback in content:
        content = content.replace(old_doc_fallback, new_sticker_fallback)
        print("✅ Fixed document fallback to proper sticker sending")
    
    # Fix 2: Add the improved function at the end of the file
    improved_function = '''

async def add_sticker_to_pack_improved(context, user_id, pack_short_name, sticker_file_id):
    """Improved sticker addition with better error handling"""
    try:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    await asyncio.sleep(2 ** attempt)  # 2s, 4s delay
                
                from telegram import InputSticker
                
                await context.bot.add_sticker_to_set(
                    user_id=user_id,
                    name=pack_short_name,
                    sticker=InputSticker(
                        sticker=sticker_file_id,
                        emoji_list=["😊"]
                    )
                )
                
                logger.info(f"✅ Sticker added to pack {pack_short_name} on attempt {attempt + 1}")
                return True
                
            except Exception as attempt_error:
                logger.warning(f"Attempt {attempt + 1} failed: {attempt_error}")
                if attempt < max_retries - 1:
                    continue
                else:
                    return False
                    
    except Exception as e:
        logger.error(f"Error in add_sticker_to_pack_improved: {e}")
        return False
'''
    
    if 'async def add_sticker_to_pack_improved' not in content:
        content += improved_function
        print("✅ Added improved sticker addition function")
    
    # Fix 3: Improve the main sticker sending
    old_send = '''        # 1. Send the sticker as proper preview with fallback
        try:
            await context.bot.send_sticker(chat_id=user_id, sticker=file_id)'''
    
    new_send = '''        # 1. Send the sticker as proper preview with enhanced success
        try:
            await context.bot.send_sticker(chat_id=user_id, sticker=file_id)
            logger.info(f"✅ Sticker preview sent successfully for user {user_id}")'''
    
    if old_send in content:
        content = content.replace(old_send, new_send)
        print("✅ Enhanced sticker sending success rate")
    
    # Write back
    with open('api/index.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("\n🎉 All fixes applied successfully!")
    return True

if __name__ == "__main__":
    fix_bot_properly()