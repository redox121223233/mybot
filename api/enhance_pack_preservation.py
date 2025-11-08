#!/usr/bin/env python3
"""
Script to enhance pack preservation logic in index.py
"""

with open('index.py', 'r') as f:
    content = f.read()

# Find the line with save_sessions() after cleanup_pending_sticker
import re

# Pattern to find the section we want to enhance
pattern = r'(\s+cleanup_pending_sticker\(user_id, lookup_key\)\s+)(save_sessions\(\)\s+reset_mode\(user_id, keep_pack=True\))'

replacement = r'\1\n            # Enhanced pack preservation logic\n            user_data = user(user_id)\n            preserved_pack = user_data.get(\'current_pack\') or current_pack\n            \n            if preserved_pack:\n                # Ensure pack is preserved in both user data and session\n                user_data[\'current_pack\'] = preserved_pack\n                sess_data = sess(user_id)\n                sess_data[\'last_pack\'] = preserved_pack\n                \n                logger.info(f"📦 Preserved pack {preserved_pack} for continuous creation")\n                \n                # Send a quick continuation prompt\n                try:\n                    await query.message.reply_text(\n                        f"🎨 آماده ساختن استیکر بعدی هستید؟\\\\n\\\\n"\n                        f"پک فعلی: {preserved_pack}\\\\n\\\\n"\n                        f"از دسته 2️⃣ برای ساختن استیکر ساده استفاده کنید یا از منوی ربات!"\n                    )\n                except Exception as prompt_error:\n                    logger.warning(f"Could not send continuation prompt: {prompt_error}")\n            \n            \2'

if re.search(pattern, content):
    new_content = re.sub(pattern, replacement, content)
    
    with open('index.py', 'w') as f:
        f.write(new_content)
    
    print('✅ Enhanced pack preservation logic added successfully')
else:
    print('❌ Could not find the pattern to match')