#!/usr/bin/env python3
"""
Apply the simple fix to replace the broken sticker handler
"""

def apply_fix():
    """Replace the broken sticker handler with the simple working version"""
    
    print("🔧 Applying simple sticker handler fix...")
    
    # Read the current file
    with open('api/index.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Define the simple replacement code
    simple_handler_code = '''        # 1. Send the sticker as proper preview with fallback
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
                    caption=f"🎨 **استیکر WebP شما!**\\\\n\\\\n💡 **نحوه استفاده:**\\\\n1. فایل را دانلود کنید\\\\n2. استیکر را به پک خود اضافه کنید\\\\n\\\\n⚠️ این فایل WebP بهینه شده برای تلگرام است"
                )
                logger.info(f"✅ Fallback WebP document sent for user {user_id}")
            except Exception as fallback_error:
                logger.error(f"❌ Fallback also failed: {fallback_error}")
                await context.bot.send_message(
                    chat_id=user_id,
                    text="❌ مشکلی در ارسال استیکر پیش آمد. لطفا دوباره تلاش کنید."
                )

        # 2. Add sticker to pack with enhanced retry logic
        pack_short_name = get_current_pack_short_name(user_id)
        logger.info(f"🎯 Current pack detected: {pack_short_name} for user {user_id}")
        
        if pack_short_name:
            success = False
            max_attempts = 3
            
            for attempt in range(max_attempts):
                try:
                    logger.info(f"🔄 Attempt {attempt + 1}/{max_attempts} to add sticker to pack...")
                    
                    if attempt > 0:
                        await asyncio.sleep(1)  # Wait between attempts
                    
                    await context.bot.add_sticker_to_set(
                        user_id=user_id,
                        name=pack_short_name,
                        sticker=file_id,
                        emojis="😊"
                    )
                    
                    logger.info(f"✅ SUCCESS: Sticker added to pack {pack_short_name}")
                    success = True
                    break
                    
                except Exception as attempt_error:
                    logger.warning(f"⚠️ Attempt {attempt + 1} failed: {attempt_error}")
                    if attempt == max_attempts - 1:
                        logger.error(f"❌ All attempts failed for user {user_id}")
            
            # Send appropriate result message
            if success:
                pack_link = f"https://t.me/addstickers/{pack_short_name}"
                await query.message.reply_text(
                    f"✅ **استیکر با موفقیت به پک اضافه شد!**\\\\n\\\\n"
                    f"🔗 [مشاهده پک]({pack_link})\\\\n\\\\n"
                    f"📌 اگر استیکر نمایش داده نشد، به پک مراجعه کنید",
                    parse_mode='Markdown',
                    disable_web_page_preview=True
                )
            else:
                pack_link = f"https://t.me/addstickers/{pack_short_name}"
                await query.message.reply_text(
                    f"⚠️ **لطفا استیکر را دستی اضافه کنید:**\\\\n\\\\n"
                    f"1. روی استیکر کلیک کنید\\\\n"
                    f"2. گزینه «Add to Pack» را انتخاب کنید\\\\n\\\\n"
                    f"🔗 **لینک پک:** {pack_link}",
                    disable_web_page_preview=True
                )
        else:
            logger.error(f"❌ No pack found for user {user_id}")
            await query.message.reply_text(
                "❌ هیچ پکی یافت نشد. لطفا ابتدا یک پک بسازید."
            )'''
    
    # Find the start of the broken section
    start_marker = "        # 1. Send the sticker as proper preview with fallback"
    
    if start_marker in content:
        # Find where the broken section starts
        start_idx = content.find(start_marker)
        
        # Find where to end (before the pack_short_name line)
        end_marker = "        pack_short_name = get_current_pack_short_name(user_id)"
        end_idx = content.find(end_marker, start_idx)
        
        if start_idx != -1 and end_idx != -1:
            # Replace the entire section
            new_content = (
                content[:start_idx] + 
                simple_handler_code + 
                content[end_idx:]
            )
            
            # Write the fixed content
            with open('api/index.py', 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            print("✅ Simple sticker handler fix applied successfully!")
            return True
        else:
            print("❌ Could not find section boundaries")
            return False
    else:
        print("❌ Could not find start marker")
        return False

def verify_syntax():
    """Verify the syntax is correct after applying the fix"""
    try:
        import ast
        with open('api/index.py', 'r', encoding='utf-8') as f:
            content = f.read()
        ast.parse(content)
        print("✅ Python syntax is valid!")
        return True
    except SyntaxError as e:
        print(f"❌ Syntax error on line {e.lineno}: {e.msg}")
        return False
    except IndentationError as e:
        print(f"❌ Indentation error on line {e.lineno}: {e.msg}")
        return False
    except Exception as e:
        print(f"❌ Other error: {e}")
        return False

if __name__ == "__main__":
    if apply_fix():
        if verify_syntax():
            print("🎉 Fix completed successfully!")
        else:
            print("⚠️ Fix applied but syntax issues remain")
    else:
        print("❌ Fix failed to apply")