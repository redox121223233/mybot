#!/usr/bin/env python3
"""
Complete replacement for the broken sticker handler section
"""

# This is the corrected version of the problematic section
CORRECTED_CODE = '''
        # 1. Send the sticker as proper preview
        try:
            await context.bot.send_sticker(chat_id=user_id, sticker=file_id)
            logger.info(f"✅ Sticker preview sent successfully for user {user_id}")
        except Exception as preview_error:
            logger.error(f"❌ Sticker preview failed: {preview_error}")
            # Fallback: create and send WebP document
            try:
                current_sess = sess(user_id)
                sticker_data = current_sess.get('sticker_data', {})
                final_text = sticker_data.get('text', '')
                defaults = {
                    "v_pos": "center",
                    "h_pos": "center", 
                    "font_key": "Default",
                    "color_hex": "#FFFFFF",
                    "size_key": "medium"
                }
                defaults.update(sticker_data)
                
                img_bytes_preview = await render_image(text=final_text, for_telegram_pack=True, **defaults)
                await context.bot.send_document(
                    chat_id=user_id,
                    document=InputFile(img_bytes_preview, "sticker.webp"),
                    caption=f"🎨 **استیکر WebP شما!**\\n\\n💡 **نحوه افزودن به پک:**\\n1. روی فایل بالا کلیک کنید\\n2. استیکر را ذخیره کنید\\n3. به پک خود اضافه کنید"
                )
                logger.info(f"✅ Fallback document sent for user {user_id}")
            except Exception as fallback_error:
                logger.error(f"❌ Fallback also failed: {fallback_error}")
                await context.bot.send_message(
                    chat_id=user_id,
                    text="❌ مشکلی در ارسال استیکر پیش آمد. لطفا دوباره تلاش کنید."
                )

        # 2. Try to add sticker to pack
        pack_short_name = get_current_pack_short_name(user_id)
        logger.info(f"🔍 Current pack detected: {pack_short_name} for user {user_id}")
        
        if pack_short_name:
            try:
                logger.info(f"🔍 Adding sticker to pack {pack_short_name}...")
                await context.bot.add_sticker_to_set(
                    user_id=user_id,
                    name=pack_short_name,
                    sticker=file_id,
                    emojis="😊"
                )
                logger.info(f"✅ SUCCESS: Sticker added to pack {pack_short_name}")
            except Exception as e:
                logger.error(f"❌ Failed to add sticker to pack: {e}")
                # Send manual instructions
                pack_link = f"https://t.me/addstickers/{pack_short_name}"
                await query.message.reply_text(
                    f"📋 **لطفا استیکر را دستی اضافه کنید:**\\n\\n"
                    f"1. روی استیکر بالا کلیک کنید\\n"
                    f"2. گزینه «Add to Pack» را انتخاب کنید\\n"
                    f"3. یا به پک مراجعه کنید: {pack_link}",
                    parse_mode='Markdown'
                )
        else:
            logger.error(f"❌ No pack found for user {user_id}")
            await query.message.reply_text(
                "❌ هیچ پکی یافت نشد. لطفا ابتدا یک پک بسازید."
            )
'''

def apply_fix():
    """Apply the fix to api/index.py"""
    print("🔧 Applying sticker handler fix...")
    
    with open('api/index.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find and replace the broken section
    start_marker = "# 1. Send the sticker as proper preview with fallback"
    end_marker = "logger.info(f&quot;✅ Sticker creation cycle completed - pack {current_pack}"
    
    if start_marker in content and end_marker in content:
        start_idx = content.find(start_marker)
        end_idx = content.find(end_marker, start_idx)
        
        if start_idx != -1 and end_idx != -1:
            # Find the end of the line with end_marker
            end_line_idx = content.find('\n', end_idx)
            
            # Replace the broken section
            new_content = (
                content[:start_idx] + 
                CORRECTED_CODE + 
                content[end_line_idx:]
            )
            
            with open('api/index.py', 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            print("✅ Fix applied successfully!")
            return True
        else:
            print("❌ Could not find section boundaries")
            return False
    else:
        print("❌ Could not find markers in the file")
        return False

if __name__ == "__main__":
    apply_fix()