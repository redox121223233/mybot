#!/usr/bin/env python3
"""
Complete integrated Telegram Bot for Vercel
All code in one file to avoid import issues
"""

import os
import json
import logging
import asyncio
import random
import io
import re
from http.server import BaseHTTPRequestHandler
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile, InputSticker
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.error import BadRequest
from telegram.constants import ChatMemberStatus
from PIL import Image, ImageDraw, ImageFont

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Global variables for user states
ADMIN_ID = 6053579919
SIMPLE_QUOTA = 10
ADVANCED_QUOTA = 3

class TelegramBotFeatures:
    """Complete bot features class"""

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id

        is_member = await self.check_channel_membership(context, user_id)
        if not is_member:
            keyboard = [[InlineKeyboardButton("عضویت در کانال", url="https://t.me/redoxbot_sticker")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            message_text = "برای استفاده از ربات، لطفاً ابتدا در کانال ما عضو شوید و سپس دکمه /start را بزنید."
            if update.callback_query:
                await update.callback_query.edit_message_text(message_text, reply_markup=reply_markup)
            else:
                await update.message.reply_text(message_text, reply_markup=reply_markup)
            return

        welcome_text = """🎉 به ربات استیکر ساز خوش آمدید! 🎉

از منوی زیر یکی از گزینه‌ها را انتخاب کنید:
"""
        keyboard = [
            [
                InlineKeyboardButton("🎨 استیکر ساز", callback_data="sticker_creator"),
                InlineKeyboardButton("🛍️ پک‌های من", callback_data="my_packs")
            ],
            [
                InlineKeyboardButton("🎮 بازی و سرگرمی", callback_data="games_menu"),
                InlineKeyboardButton("📊 سهمیه من", callback_data="my_quota")
            ],
            [
                InlineKeyboardButton("📚 راهنما", callback_data="help"),
                InlineKeyboardButton("📞 پشتیبانی", callback_data="support")
            ]
        ]
        if user_id == ADMIN_ID:
            keyboard.append([InlineKeyboardButton("👑 پنل ادمین", callback_data="admin_panel")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.callback_query:
            await update.callback_query.edit_message_text(welcome_text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(welcome_text, reply_markup=reply_markup)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = "این راهنمای ربات است. (در آینده تکمیل می‌شود)"
        await update.message.reply_text(help_text)

    async def create_simple_sticker(self, image_stream):
        """Creates a simple sticker from an image"""
        try:
            img = Image.open(image_stream).convert("RGBA")
            img = img.resize((512, 512))
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='WEBP')
            img_bytes.seek(0)
            return img_bytes
        except Exception as e:
            logger.error(f"Error creating simple sticker: {e}")
            return None

    async def create_sticker_with_text(self, image_stream, text, font_size=60):
        """Create a sticker by adding text to an image"""
        try:
            img = Image.open(image_stream).convert("RGBA")
            img = img.resize((512, 512))
            draw = ImageDraw.Draw(img)
            try:
                font = ImageFont.truetype("fonts/Vazir.ttf", font_size)
            except IOError:
                font = ImageFont.load_default()
            text_bbox = draw.textbbox((0, 0), text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            position = ((512 - text_width) / 2, (512 - text_height) / 2)
            stroke_width = 2
            stroke_fill = "black"
            draw.text((position[0]-stroke_width, position[1]-stroke_width), text, font=font, fill=stroke_fill)
            draw.text((position[0]+stroke_width, position[1]-stroke_width), text, font=font, fill=stroke_fill)
            draw.text((position[0]-stroke_width, position[1]+stroke_width), text, font=font, fill=stroke_fill)
            draw.text((position[0]+stroke_width, position[1]+stroke_width), text, font=font, fill=stroke_fill)
            draw.text(position, text, font=font, fill="white")
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='WEBP')
            img_bytes.seek(0)
            return img_bytes
        except Exception as e:
            logger.error(f"Error creating sticker with text: {e}")
            return None

    async def add_sticker_to_pack(self, context: ContextTypes.DEFAULT_TYPE, user_id: int, pack_name: str, sticker_bytes: io.BytesIO):
        """Adds a sticker to a pack, creating it if it doesn't exist."""
        bot = context.bot
        pack_name_suffix = f"_by_{bot.username}"
        full_pack_name = f"{pack_name}{pack_name_suffix}"

        sticker_to_add = InputSticker(sticker_bytes, ["✅"])

        try:
            # First, try to add to an existing pack
            await bot.add_sticker_to_set(user_id=user_id, name=full_pack_name, sticker=sticker_to_add)
            logger.info(f"Sticker added to existing pack {full_pack_name}")
            return full_pack_name, None
        except BadRequest as e:
            if "sticker set name is already occupied" in e.message.lower():
                 return None, "occupied"
            elif "stickerset_invalid" in e.message.lower():
                # Pack doesn't exist, so create it
                try:
                    await bot.create_new_sticker_set(user_id=user_id, name=full_pack_name, title=pack_name, stickers=[sticker_to_add], sticker_format='static')
                    logger.info(f"Created new sticker pack {full_pack_name}")
                    return full_pack_name, None
                except BadRequest as e2:
                    logger.error(f"Failed to create new sticker set: {e2}")
                    return None, str(e2)
            else:
                logger.error(f"Unhandled BadRequest when adding sticker: {e}")
                return None, str(e)
        except Exception as e:
            logger.error(f"Unexpected error when adding sticker: {e}")
            return None, str(e)

    async def check_channel_membership(self, context: ContextTypes.DEFAULT_TYPE, user_id: int):
        """Checks if a user is a member of the required channel."""
        try:
            member = await context.bot.get_chat_member(chat_id="@redoxbot_sticker", user_id=user_id)
            logger.info(f"User {user_id} has channel membership status: {member.status}")
            return member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, 'creator']
        except BadRequest as e:
            if "user not found" in e.message.lower():
                # This is expected for new users, not an error.
                pass
            else:
                logger.error(f"Error checking channel membership (BadRequest): {e}. Is the bot an admin in the channel?")
            return False
        except Exception as e:
            logger.error(f"Error checking channel membership: {e}")
            return False

    def is_valid_pack_name(self, name: str) -> bool:
        """Validates pack name based on Telegram rules."""
        if not (4 <= len(name) <= 32):
            return False
        if not name[0].isalpha():
            return False
        if not re.match("^[a-zA-Z0-9_]*$", name):
            return False
        if name.isdigit():
            return False
        return True

# Initialize bot features
bot_features = TelegramBotFeatures()

# Handler functions
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await bot_features.start_command(update, context)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await bot_features.help_command(update, context)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    if user_data.get("state") == "awaiting_sticker_image":
        photo_file_id = update.message.photo[-1].file_id
        user_data["photo_id"] = photo_file_id

        keyboard = [
            [
                InlineKeyboardButton("🖼️ پس‌زمینه پیش‌فرض", callback_data="bg_default"),
                InlineKeyboardButton("✨ پس‌زمینه عکس خودم", callback_data="bg_user")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("یک گزینه برای پس‌زمینه انتخاب کنید:", reply_markup=reply_markup)

# Initialize bot_features object
bot_features = TelegramBotFeatures()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    user_id = update.effective_user.id
    current_state = user_data.get("state")

    if current_state == "awaiting_pack_name":
        pack_name = update.message.text
        if not bot_features.is_valid_pack_name(pack_name):
            await update.message.reply_text("نام بسته نامعتبر است. لطفاً با توجه به قوانین، نام دیگری انتخاب کنید.")
            return

        user_data["state"] = "awaiting_sticker_image"
        user_data["pack_name"] = pack_name
        await update.message.reply_text(f"نام بسته '{pack_name}' انتخاب شد. لطفاً اولین تصویر را برای استیکر خود ارسال کنید.")

    elif current_state == "awaiting_text":
        text = update.message.text
        photo_id = user_data.get("photo_id")

        photo_file = await context.bot.get_file(photo_id)
        photo_stream = io.BytesIO()
        await photo_file.download_to_memory(photo_stream)
        photo_stream.seek(0)

        # Add background if needed
        if user_data.get("background") == "bg_default":
            background = Image.open("assets/default_background.png")
            img = Image.open(photo_stream).convert("RGBA")
            background.paste(img, (0, 0), img)
            photo_stream = io.BytesIO()
            background.save(photo_stream, format='PNG')
            photo_stream.seek(0)

        sticker_bytes = await bot_features.create_sticker_with_text(photo_stream, text)
        if sticker_bytes:
            user_data["state"] = "awaiting_satisfaction"
            user_data["sticker_bytes"] = sticker_bytes.getvalue()
            keyboard = [
                [
                    InlineKeyboardButton("👍 بله", callback_data="satisfaction_yes"),
                    InlineKeyboardButton("👎 خیر", callback_data="satisfaction_no")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_document(sticker_bytes, filename="sticker.webp", caption="آیا از نتیجه راضی هستید؟", reply_markup=reply_markup)
        else:
            await update.message.reply_text("خطا در ساخت استیکر.")

    # Admin states
    elif user_id == ADMIN_ID:
        if current_state == "awaiting_admin_user_id_for_message":
            try:
                target_user_id = int(update.message.text)
                user_data["state"] = "awaiting_admin_message_to_send"
                user_data["target_user_id"] = target_user_id
                await update.message.reply_text(f"پیام خود را برای کاربر {target_user_id} وارد کنید:")
            except ValueError:
                await update.message.reply_text("شناسه نامعتبر است. لطفاً شناسه عددی کاربر را وارد کنید.")

        elif current_state == "awaiting_admin_message_to_send":
            target_user_id = user_data.get("target_user_id")
            message_text = update.message.text
            try:
                await context.bot.send_message(chat_id=target_user_id, text=message_text)
                await update.message.reply_text("پیام با موفقیت ارسال شد.")
            except Exception as e:
                await update.message.reply_text(f"خطا در ارسال پیام: {e}")
            user_data.clear()

        elif current_state == "awaiting_admin_broadcast_message":
            message_text = update.message.text
            await update.message.reply_text(f"پیام همگانی (نمایشی): {message_text}")
            user_data.clear()

        elif current_state == "awaiting_admin_user_id_for_quota_increase":
            try:
                target_user_id = int(update.message.text)
                user_data["state"] = "awaiting_admin_quota_increase_amount"
                user_data["target_user_id"] = target_user_id
                await update.message.reply_text(f"مقدار افزایش سهمیه برای کاربر {target_user_id} را وارد کنید:")
            except ValueError:
                await update.message.reply_text("شناسه نامعتبر است. لطفاً شناسه عددی کاربر را وارد کنید.")

        elif current_state == "awaiting_admin_quota_increase_amount":
            target_user_id = user_data.get("target_user_id")
            try:
                amount = int(update.message.text)
                target_user_data = context.bot_data.get(target_user_id, {})
                check_and_update_quota(target_user_data, "any") # Initialize if not exists
                target_user_data["quota"]["simple"] += amount
                target_user_data["quota"]["advanced"] += amount
                context.bot_data[target_user_id] = target_user_data
                await update.message.reply_text(f"سهمیه کاربر {target_user_id} افزایش یافت.")
            except ValueError:
                await update.message.reply_text("مقدار نامعتبر است. لطفاً عدد وارد کنید.")
            user_data.clear()

        elif current_state == "awaiting_admin_user_id_for_quota_decrease":
            try:
                target_user_id = int(update.message.text)
                user_data["state"] = "awaiting_admin_quota_decrease_amount"
                user_data["target_user_id"] = target_user_id
                await update.message.reply_text(f"مقدار کاهش سهمیه برای کاربر {target_user_id} را وارد کنید:")
            except ValueError:
                await update.message.reply_text("شناسه نامعتبر است. لطفاً شناسه عددی کاربر را وارد کنید.")

        elif current_state == "awaiting_admin_quota_decrease_amount":
            target_user_id = user_data.get("target_user_id")
            try:
                amount = int(update.message.text)
                target_user_data = context.bot_data.get(target_user_id, {})
                check_and_update_quota(target_user_data, "any") # Initialize if not exists
                target_user_data["quota"]["simple"] = max(0, target_user_data["quota"]["simple"] - amount)
                target_user_data["quota"]["advanced"] = max(0, target_user_data["quota"]["advanced"] - amount)
                context.bot_data[target_user_id] = target_user_data
                await update.message.reply_text(f"سهمیه کاربر {target_user_id} کاهش یافت.")
            except ValueError:
                await update.message.reply_text("مقدار نامعتبر است. لطفاً عدد وارد کنید.")
            user_data.clear()
    else:
        await update.message.reply_text("دستور شما را متوجه نشدم. لطفاً از دکمه‌ها استفاده کنید یا /start را بزنید.")

def check_and_update_quota(user_data: dict, sticker_type: str):
    """Checks and updates the user's quota within user_data. Returns True if the user has quota, False otherwise."""
    now = datetime.utcnow()
    quota_data = user_data.get("quota", {})

    if not quota_data or now >= quota_data.get("reset_time", now):
        quota_data = {
            "simple": SIMPLE_QUOTA,
            "advanced": ADVANCED_QUOTA,
            "reset_time": now + timedelta(hours=24)
        }
        user_data["quota"] = quota_data

    if sticker_type == "any": # Just to initialize/reset
        return True

    quota_type = "simple" if sticker_type == "simple" else "advanced"
    if quota_data.get(quota_type, 0) > 0:
        quota_data[quota_type] -= 1
        return True
    return False

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_data = context.user_data
    user_id = query.from_user.id

    is_member = await bot_features.check_channel_membership(context, user_id)
    if not is_member:
        keyboard = [[InlineKeyboardButton(" عضویت در کانال", url="https://t.me/redoxbot_sticker")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("برای استفاده از ربات، لطفاً ابتدا در کانال ما عضو شوید.", reply_markup=reply_markup)
        return

    if query.data == "start_menu":
        user_data.clear()
        await bot_features.start_command(update, context)

    elif query.data == "sticker_creator":
        keyboard = [
            [
                InlineKeyboardButton("ساده", callback_data="simple_sticker"),
                InlineKeyboardButton("پیشرفته", callback_data="advanced_sticker")
            ],
            [InlineKeyboardButton("بازگشت", callback_data="start_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("نوع استیکر خود را انتخاب کنید:", reply_markup=reply_markup)

    elif query.data in ["simple_sticker", "advanced_sticker"]:
        sticker_type = "simple" if query.data == "simple_sticker" else "advanced"
        user_data["state"] = "awaiting_pack_name"
        user_data["type"] = sticker_type
        pack_name_rules = """
لطفاً یک نام برای بسته استیکر خود وارد کنید.

**قوانین نام‌گذاری:**
- نام باید با یک حرف انگلیسی شروع شود.
- فقط شامل حروف انگلیسی، اعداد و خط زیر (\_) باشد.
- نمی‌تواند فقط شامل اعداد باشد.
- طول آن بین ۴ تا ۳۲ کاراکتر باشد.
"""
        await query.edit_message_text(pack_name_rules, parse_mode='Markdown')

    elif query.data in ["bg_default", "bg_user"]:
        user_data["background"] = query.data
        keyboard = [
            [
                InlineKeyboardButton("✍️ با متن", callback_data="text_yes"),
                InlineKeyboardButton("🖼️ بدون متن", callback_data="text_no")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("آیا می‌خواهید به استیکر خود متن اضافه کنید؟", reply_markup=reply_markup)

    elif query.data == "text_no":
        user_data["text"] = None
        user_data["type"] = "simple"
        # Create sticker without text
        photo_id = user_data.get("photo_id")
        photo_file = await context.bot.get_file(photo_id)
        photo_stream = io.BytesIO()
        await photo_file.download_to_memory(photo_stream)
        photo_stream.seek(0)

        # Add background if needed
        if user_data.get("background") == "bg_default":
            background = Image.open("assets/default_background.png")
            img = Image.open(photo_stream).convert("RGBA")
            background.paste(img, (0, 0), img)
            photo_stream = io.BytesIO()
            background.save(photo_stream, format='PNG')
            photo_stream.seek(0)

        sticker_bytes = await bot_features.create_simple_sticker(photo_stream)

        if sticker_bytes:
            user_data["state"] = "awaiting_satisfaction"
            user_data["sticker_bytes"] = sticker_bytes.getvalue()
            keyboard = [
                [
                    InlineKeyboardButton("👍 بله", callback_data="satisfaction_yes"),
                    InlineKeyboardButton("👎 خیر", callback_data="satisfaction_no")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_document(sticker_bytes, filename="sticker.webp", caption="آیا از نتیجه راضی هستید؟", reply_markup=reply_markup)
        else:
            await query.edit_message_text("خطا در ساخت استیکر.")

    elif query.data == "text_yes":
        user_data["state"] = "awaiting_text"
        await query.edit_message_text("لطفاً متنی که می‌خواهید روی استیکر باشد را ارسال کنید:")

    elif query.data == "satisfaction_yes":
        if user_data.get("state") == "awaiting_satisfaction":
            sticker_type = user_data["type"]

            await query.message.delete()
            if not check_and_update_quota(user_data, sticker_type):
                await query.message.reply_text("متاسفانه سهمیه روزانه شما برای این نوع استیکر به پایان رسیده است.")
                return

            pack_name = user_data["pack_name"]
            sticker_bytes = io.BytesIO(user_data["sticker_bytes"])
            full_pack_name, error = await bot_features.add_sticker_to_pack(context, user_id, pack_name, sticker_bytes)

            if error == "occupied":
                user_data["state"] = "awaiting_pack_name"
                await query.message.reply_text("این نام بسته قبلاً توسط کاربر دیگری گرفته شده است. لطفاً نام دیگری انتخاب کنید:")
            elif error:
                await query.message.reply_text(f"خطایی رخ داد: {error}")
            else:
                user_packs = user_data.get("packs", [])
                if full_pack_name not in user_packs:
                    user_packs.append(full_pack_name)
                user_data["packs"] = user_packs

                quota_data = user_data.get("quota", {})
                remaining_quota = quota_data.get("simple" if sticker_type == "simple" else "advanced", 0)
                user_data["state"] = "awaiting_sticker_image"

                await query.message.reply_text(
                    f"استیکر شما با موفقیت به بسته '{pack_name}' اضافه شد!\n"
                    f"سهمیه باقی‌مانده ({'ساده' if sticker_type == 'simple' else 'پیشرفته'}): {remaining_quota}\n\n"
                    f"برای مشاهده: https://t.me/addstickers/{full_pack_name}\n\n"
                    "می‌توانید تصویر بعدی را ارسال کنید یا با ارسال /done کار را تمام کنید."
                )
        else:
            await query.message.reply_text("خطای وضعیت. لطفاً دوباره با /start شروع کنید.")

    elif query.data == "satisfaction_no":
        user_data["state"] = "awaiting_sticker_image"
        await query.message.delete()
        await query.message.reply_text("عملیات لغو شد. لطفاً تصویر جدیدی برای استیکر خود ارسال کنید.")

    elif query.data == "my_packs":
        user_packs = user_data.get("packs", [])
        if user_packs:
            packs_links = [f"[{name.split('_by_')[0]}](t.me/addstickers/{name})" for name in user_packs]
            packs_list = "\n".join(packs_links)
            await query.edit_message_text(f"لیست پک‌های شما:\n{packs_list}", parse_mode='Markdown')
        else:
            await query.edit_message_text("شما هنوز هیچ پکی نساخته‌اید.")

    elif query.data == "support":
        await query.edit_message_text("برای پشتیبانی به آیدی @onedaytoalive پیام دهید.")

    elif query.data == "my_quota":
        check_and_update_quota(user_data, "any") # Ensures quota is initialized/reset
        quota_data = user_data.get("quota", {})

        now = datetime.utcnow()
        reset_time = quota_data.get('reset_time', now + timedelta(hours=24))
        time_left = reset_time - now
        hours, remainder = divmod(time_left.seconds, 3600)
        minutes, _ = divmod(remainder, 60)

        quota_text = (
            f"📊 **سهمیه شما**\n\n"
            f"🎨 **استیکر ساده:** {quota_data.get('simple', SIMPLE_QUOTA)}/{SIMPLE_QUOTA}\n"
            f"✨ **استیکر پیشرفته:** {quota_data.get('advanced', ADVANCED_QUOTA)}/{ADVANCED_QUOTA}\n\n"
            f"⏳ **زمان تا شارژ بعدی:** {hours} ساعت و {minutes} دقیقه"
        )
        await query.edit_message_text(quota_text, parse_mode='Markdown')

    elif query.data == "admin_panel":
        if user_id == ADMIN_ID:
            keyboard = [
                [InlineKeyboardButton("ارسال پیام به کاربر", callback_data="admin_send_user")],
                [InlineKeyboardButton("ارسال پیام همگانی", callback_data="admin_broadcast")],
                [InlineKeyboardButton("افزایش سهمیه", callback_data="admin_increase_quota")],
                [InlineKeyboardButton("کاهش سهمیه", callback_data="admin_decrease_quota")],
                [InlineKeyboardButton("بازگشت", callback_data="start_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("به پنل ادمین خوش آمدید.", reply_markup=reply_markup)
        else:
            await query.edit_message_text("شما اجازه دسترسی به این بخش را ندارید.")

    elif query.data == "admin_send_user":
        user_data["state"] = "awaiting_admin_user_id_for_message"
        await query.edit_message_text("شناسه عددی کاربر مورد نظر را وارد کنید:")

    elif query.data == "admin_broadcast":
        user_data["state"] = "awaiting_admin_broadcast_message"
        await query.edit_message_text("پیام همگانی خود را وارد کنید:")

    elif query.data == "admin_increase_quota":
        user_data["state"] = "awaiting_admin_user_id_for_quota_increase"
        await query.edit_message_text("شناسه عددی کاربر مورد نظر برای افزایش سهمیه را وارد کنید:")

    elif query.data == "admin_decrease_quota":
        user_data["state"] = "awaiting_admin_user_id_for_quota_decrease"
        await query.edit_message_text("شناسه عددی کاربر مورد نظر برای کاهش سهمیه را وارد کنید:")

    elif query.data == "games_menu":
        await query.edit_message_text("بخش بازی و سرگرمی در حال ساخت است. به زودی برمی‌گردیم!")

    else:
        await query.edit_message_text(f"گزینه ناشناخته: {query.data}")


# Vercel Handler
application = None

def ensure_application_initialized():
    global application
    if application is None:
        TELEGRAM_TOKEN = os.getenv('BOT_TOKEN')
        if TELEGRAM_TOKEN:
            application = Application.builder().token(TELEGRAM_TOKEN).build()
            application.add_handler(CommandHandler("start", start_command))
            application.add_handler(CommandHandler("help", help_command))
            application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
            application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
            application.add_handler(CallbackQueryHandler(button_callback))
        else:
            logger.error("No Telegram token found")

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Bot is running.')

    def do_POST(self):
        ensure_application_initialized()
        if application is None:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b'Bot not initialized')
            return

        try:
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length)
            update_data = json.loads(body.decode('utf-8'))

            async def process():
                await application.initialize()
                update = Update.de_json(update_data, application.bot)
                await application.process_update(update)
                await application.shutdown()

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(process())

            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')
        except Exception as e:
            logger.error(f"Error in handler: {e}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f'Error: {e}'.encode())
