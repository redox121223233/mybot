import re

# Read the current file with conflicts
with open('api/index.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Define the choices for conflicts
conflicts = [
    {
        'search': r'<<<<<<< HEAD\nEnhanced Telegram Sticker Bot - Working Version\nSupports pack creation, website integration, and channel subscription\n=======\nEnhanced Telegram Sticker Bot - Professional Version\nSupports online sticker creation, pack management, and advanced features\n>>>>>>> f36420dcbbdb0803862906dab6a62e0567f89a3c',
        'replace': 'Enhanced Telegram Sticker Bot - Working Version\nSupports pack creation, website integration, and channel subscription'
    },
    {
        'search': r'<<<<<<< HEAD\nfrom telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot\n=======\nfrom telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup\n>>>>>>> f36420dcbbdb0803862906dab6a62e0567f89a3c',
        'replace': 'from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot'
    },
    {
        'search': r'<<<<<<< HEAD\n            try:\n                pack_result = await create_new_sticker_pack(update, context, pack_name)\n                if pack_result:\n                    await update.message.reply_text(\n                        f"✅ استیکر پک {pack_name} با موفقیت ساخته شد!\\n" +\n                        f"📦 می‌توانید استیکرهای خود را به این پک اضافه کنید.\\n" +\n                        f"🔗 لینک استیکر پک: {pack_result}",\n                        reply_markup=InlineKeyboardMarkup([\n                            [InlineKeyboardButton("📦 باز کردن استیکر پک", url=pack_result)]\n                        ])\n                    )\n                else:\n                    await update.message.reply_text("❌ خطا در ساختن استیکر پک. لطفا با ادمین تماس بگیرید.")\n            except Exception as e:\n                logger.error(f"Error creating pack: {e}")\n                await update.message.reply_text("❌ خطا در ساختن استیکر پک. لطفا بعدا دوباره تلاش کنید.")\n            return\n=======\n            try:\n                pack_result = await create_new_sticker_pack(update, context, pack_name)\n                if pack_result:\n                    await update.message.reply_text(\n                        f"✅ استیکر پک {pack_name} با موفقیت ساخته شد!\\n" +\n                        f"📦 حالا می‌توانید استیکرهای خود را ارسال کنید.",\n                        reply_markup=InlineKeyboardMarkup([\n                            [InlineKeyboardButton("📦 باز کردن استیکر پک", url=pack_result)]\n                        ])\n                    )\n                else:\n                    await update.message.reply_text("❌ خطا در ساختن استیکر پک")\n            except Exception as e:\n                await update.message.reply_text("❌ خطا در ساختن استیکر پک")\n            return\n>>>>>>> f36420dcbbdb0803862906dab6a62e0567f89a3c',
        'replace': '''            try:
                pack_result = await create_new_sticker_pack(update, context, pack_name)
                if pack_result:
                    await update.message.reply_text(
                        f"✅ استیکر پک {pack_name} با موفقیت ساخته شد!\\n" +
                        f"📦 می‌توانید استیکرهای خود را به این پک اضافه کنید.\\n" +
                        f"🔗 لینک استیکر پک: {pack_result}",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("📦 باز کردن استیکر پک", url=pack_result)]
                        ])
                    )
                else:
                    await update.message.reply_text("❌ خطا در ساختن استیکر پک. لطفا با ادمین تماس بگیرید.")
            except Exception as e:
                logger.error(f"Error creating pack: {e}")
                await update.message.reply_text("❌ خطا در ساختن استیکر پک. لطفا بعدا دوباره تلاش کنید.")
            return'''
    },
    {
        'search': r'<<<<<<< HEAD\n    except Exception as e:\n        logger.error(f"Webhook error: {e}")\n        return jsonify({"status": "error", "message": str(e)}), 500\n=======\n    except Exception as e:\n        logger.error(f"Webhook error: {e}")\n        return jsonify({"status": "error", "message": str(e)}), 500\n>>>>>>> f36420dcbbdb0803862906dab6a62e0567f89a3c',
        'replace': '    except Exception as e:\n        logger.error(f"Webhook error: {e}")\n        return jsonify({"status": "error", "message": str(e)}), 500'
    }
]

# Apply all fixes
for conflict in conflicts:
    content = re.sub(conflict['search'], conflict['replace'], content, flags=re.DOTALL)

# Write the fixed content
with open('api/index.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed merge conflicts in api/index.py")