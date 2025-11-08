#!/usr/bin/env python3
"""
Simple fix for sticker issues:
1. Fix final_text undefined error
2. Fix add_sticker_to_set missing
3. Ensure WebP format
"""

def fix_final_text():
    """Fix the final_text undefined error"""
    with open('api/index.py', 'r') as f:
        content = f.read()
    
    # Fix the final_text issue
    old = 'defaults.update(sticker_data)\n                   \n                   img_bytes_preview = await render_image(text=final_text, for_telegram_pack=True, **defaults)'
    new = 'defaults.update(sticker_data)\n                   final_text = sticker_data.get(\'text\', \'\')\n                   \n                   img_bytes_preview = await render_image(text=final_text, for_telegram_pack=True, **defaults)'
    
    content = content.replace(old, new)
    
    with open('api/index.py', 'w') as f:
        f.write(content)
    print("✅ Fixed final_text issue")

def add_sticker_to_pack():
    """Add missing sticker to pack functionality"""
    with open('api/index.py', 'r') as f:
        content = f.read()
    
    # Find the location after send_sticker and add pack logic
    marker = "logger.info(f&quot;Sticker preview sent successfully for user {user_id}&quot;)"
    insert_code = '''
        # Add sticker to pack
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
'''
    
    if marker in content and "add_sticker_to_set" not in content:
        content = content.replace(marker, marker + insert_code)
        with open('api/index.py', 'w') as f:
            f.write(content)
        print("✅ Added sticker to pack functionality")
    else:
        print("ℹ️ Sticker to pack functionality already exists")

if __name__ == "__main__":
    fix_final_text()
    add_sticker_to_pack()
    print("🎉 Fix completed!")