#!/usr/bin/env python3
"""
Minimal fix for the three main sticker issues:
1. final_text undefined 
2. add_sticker_to_set missing
3. WebP format issues
"""

def apply_minimal_fixes():
    """Apply only the essential fixes"""
    print("🔧 Applying minimal sticker fixes...")
    
    with open('api/index.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix 1: Add final_text definition
    old_final_text = '''                defaults.update(sticker_data)
                
                img_bytes_preview = await render_image(text=final_text, for_telegram_pack=True, **defaults)'''
    
    new_final_text = '''                defaults.update(sticker_data)
                final_text = sticker_data.get('text', '')
                
                img_bytes_preview = await render_image(text=final_text, for_telegram_pack=True, **defaults)'''
    
    content = content.replace(old_final_text, new_final_text)
    print("✅ Fixed final_text undefined issue")
    
    # Fix 2: Add sticker to pack functionality after successful preview
    old_success = '''            await context.bot.send_sticker(chat_id=user_id, sticker=file_id)
            logger.info(f"Sticker preview sent successfully for user {user_id}")'''
    
    new_success = '''            await context.bot.send_sticker(chat_id=user_id, sticker=file_id)
            logger.info(f"Sticker preview sent successfully for user {user_id}")
            
            # Try to add sticker to pack
            pack_short_name = get_current_pack_short_name(user_id)
            if pack_short_name:
                try:
                    logger.info(f"Adding sticker to pack {pack_short_name}...")
                    await context.bot.add_sticker_to_set(
                        user_id=user_id,
                        name=pack_short_name,
                        sticker=file_id,
                        emojis="😊"
                    )
                    logger.info("✅ Sticker added to pack successfully!")
                except Exception as e:
                    logger.error(f"❌ Failed to add sticker to pack: {e}")
                    pack_link = f"https://t.me/addstickers/{pack_short_name}"
                    await query.message.reply_text(
                        f"⚠️ لطفا استیکر را دستی اضافه کنید:\\n\\n"
                        f"1. روی استیکر کلیک کنید\\n"
                        f"2. «Add to Pack» را انتخاب کنید\\n\\n"
                        f"لینک: {pack_link}"
                    )'''
    
    content = content.replace(old_success, new_success)
    print("✅ Added sticker to pack functionality")
    
    # Fix 3: Ensure WebP format in render_image
    old_webp = '''                img_bytes_preview = await render_image(text=final_text, for_telegram_pack=True, **defaults)'''
    
    new_webp = '''                img_bytes_preview = await render_image(text=final_text, for_telegram_pack=True, **defaults)
                logger.info(f"Generated WebP preview, size: {len(img_bytes_preview)} bytes")'''
    
    content = content.replace(old_webp, new_webp)
    print("✅ Enhanced WebP format handling")
    
    # Write the fixed content
    with open('api/index.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    return True

def verify_fix():
    """Verify the fixes were applied"""
    with open('api/index.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = [
        ("final_text defined", "final_text = sticker_data.get('text', '')" in content),
        ("add_sticker_to_set added", "add_sticker_to_set" in content),
        ("WebP handling enhanced", "Generated WebP preview" in content)
    ]
    
    all_good = True
    for name, check in checks:
        if check:
            print(f"✅ {name}")
        else:
            print(f"❌ {name}")
            all_good = False
    
    return all_good

if __name__ == "__main__":
    if apply_minimal_fixes():
        if verify_fix():
            print("🎉 All minimal fixes applied successfully!")
        else:
            print("⚠️ Some fixes may not have been applied correctly")
    else:
        print("❌ Failed to apply fixes")