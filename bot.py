import os
import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot configuration
BOT_TOKEN = os.getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
ADMIN_ID = 6053579919
REQUIRED_CHANNEL = '@redoxbot_sticker'
SUPPORT_USERNAME = '@onedaytoalive'
GITHUB_REPO = os.getenv('GITHUB_REPO', 'your-username/your-repo')
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', 'your_github_token')

# User data storage
user_data: Dict = {}
user_quotas: Dict = {}

class StickerBot:
    def __init__(self):
        self.application = Application.builder().token(BOT_TOKEN).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        """Setup all command and callback handlers"""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("admin", self.admin_command))
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user_id = update.effective_user.id
        
        # Initialize user data
        if user_id not in user_data:
            user_data[user_id] = {
                'state': 'main_menu',
                'packs': [],
                'current_pack': None,
                'temp_data': {}
            }
        
        # Check membership
        is_member = await self.check_membership(user_id, context)
        
        if not is_member:
            keyboard = [
                [InlineKeyboardButton("✅ عضویت در کانال", url=f"https://t.me/{REQUIRED_CHANNEL[1:]}")],
                [InlineKeyboardButton("🔄 بررسی عضویت", callback_data="check_membership")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "🔒 برای استفاده از ربات، ابتدا در کانال زیر عضو شوید:\n\n"
                f"📢 {REQUIRED_CHANNEL}\n\n"
                "پس از عضویت، دکمه بررسی عضویت را فشار دهید.",
                reply_markup=reply_markup
            )
            return
        
        await self.show_main_menu(update, context)
    
    async def check_membership(self, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Check if user is member of required channel"""
        try:
            member = await context.bot.get_chat_member(REQUIRED_CHANNEL, user_id)
            return member.status in ['member', 'administrator', 'creator']
        except:
            return False
    
    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show main menu with all options"""
        user_id = update.effective_user.id
        quota_info = self.get_quota_info(user_id)
        
        menu_text = (
            "🎨 *ربات ساخت استیکر پیشرفته*\n\n"
            f"📊 تعداد استیکر باقی‌مانده: {quota_info['remaining']}/5\n"
            f"⏰ زمان تا بازنشانی: {quota_info['reset_time']}\n\n"
            "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:"
        )
        
        keyboard = [
            [InlineKeyboardButton("🎯 ساخت استیکر ساده", callback_data="simple_sticker")],
            [InlineKeyboardButton("🤖 ساخت استیکر پیشرفته", callback_data="advanced_sticker")],
            [InlineKeyboardButton("📦 مدیریت پک‌ها", callback_data="pack_manager")],
            [
                InlineKeyboardButton("❓ راهنما", callback_data="help"),
                InlineKeyboardButton("💬 پشتیبانی", callback_data="support")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(menu_text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(menu_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    def get_quota_info(self, user_id: int) -> Dict:
        """Get user quota information"""
        now = datetime.now()
        
        if user_id not in user_quotas:
            user_quotas[user_id] = {
                'count': 0,
                'reset_time': now + timedelta(hours=24)
            }
        
        quota = user_quotas[user_id]
        
        # Reset quota if 24 hours passed
        if now >= quota['reset_time']:
            quota['count'] = 0
            quota['reset_time'] = now + timedelta(hours=24)
        
        remaining = max(0, 5 - quota['count'])
        time_left = quota['reset_time'] - now
        hours, remainder = divmod(int(time_left.total_seconds()), 3600)
        minutes, _ = divmod(remainder, 60)
        reset_time = f"{hours:02d}:{minutes:02d}"
        
        return {
            'remaining': remaining,
            'reset_time': reset_time,
            'can_create': remaining > 0
        }
    
    async def start_simple_sticker(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start simple sticker creation process"""
        user_id = update.effective_user.id
        user_data[user_id]['state'] = 'simple_pack_name'
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            "🎯 *ساخت استیکر ساده*\n\n"
            "لطفاً نام پک استیکر خود را وارد کنید:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    def start_advanced_sticker(self, call):
        """Start advanced sticker creation process"""
        user_id = call.from_user.id
        quota_info = self.get_quota_info(user_id)
        
        if not quota_info['can_create']:
            bot.answer_callback_query(
                call.id,
                f"❌ سهمیه شما تمام شده! {quota_info['reset_time']} ساعت دیگر تلاش کنید.",
                show_alert=True
            )
            return
        
        user_data[user_id]['state'] = 'advanced_pack_name'
        user_data[user_id]['temp_data'] = {}
        
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu"))
        
        bot.edit_message_text(
            "🤖 *ساخت استیکر پیشرفته*\n\n"
            f"📊 استیکر باقی‌مانده: {quota_info['remaining']}\n\n"
            "لطفاً نام پک استیکر خود را وارد کنید:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    
    async def create_simple_sticker(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Create simple sticker"""
        user_id = update.effective_user.id
        temp_data = user_data[user_id]['temp_data']
        
        # Simulate sticker creation
        pack_name = temp_data['pack_name']
        pack_link = f"https://t.me/addstickers/{pack_name.replace(' ', '_')}"
        
        # Save to user packs
        if 'packs' not in user_data[user_id]:
            user_data[user_id]['packs'] = []
        
        user_data[user_id]['packs'].append({
            'name': pack_name,
            'link': pack_link,
            'stickers': [{'text': text, 'type': 'simple'}]
        })
        
        # Save to GitHub (simulate)
        await self.save_to_github(user_id)
        
        keyboard = [
            [InlineKeyboardButton("😊 راضی هستم", callback_data="feedback_satisfied")],
            [InlineKeyboardButton("😞 راضی نیستم", callback_data="feedback_unsatisfied")],
            [InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ *استیکر شما با موفقیت ساخته شد!*\n\n"
            f"📦 نام پک: {pack_name}\n"
            f"🔗 لینک پک: {pack_link}\n\n"
            "لطفاً نظر خود را درباره کیفیت استیکر اعلام کنید:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        user_data[user_id]['state'] = 'main_menu'
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle all button callbacks"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        data = query.data
        
        if data == "check_membership":
            is_member = await self.check_membership(user_id, context)
            if is_member:
                await query.edit_message_text("✅ عضویت شما تأیید شد!")
                await asyncio.sleep(1)
                await self.show_main_menu(update, context)
            else:
                await query.answer("❌ هنوز عضو کانال نشده‌اید!", show_alert=True)
        
        elif data == "main_menu":
            await self.show_main_menu(update, context)
        
        elif data == "simple_sticker":
            await self.start_simple_sticker(update, context)
        
        elif data == "advanced_sticker":
            await self.start_advanced_sticker(update, context)
        
        elif data == "pack_manager":
            await self.show_pack_manager(update, context)
        
        elif data == "help":
            await self.show_help(update, context)
        
        elif data == "support":
            await self.show_support(update, context)
        
        elif data.startswith("feedback_"):
            await self.handle_feedback(update, context, data)
        
        elif data.startswith("bg_"):
            await self.handle_background_selection(update, context, data)
    
    async def start_simple_sticker(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start simple sticker creation process"""
        user_id = update.effective_user.id
        user_data[user_id]['state'] = 'simple_pack_name'
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            "🎯 **ساخت استیکر ساده**\n\n"
            "لطفاً نام پک استیکر خود را وارد کنید:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def start_advanced_sticker(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start advanced sticker creation process"""
        user_id = update.effective_user.id
        quota_info = self.get_quota_info(user_id)
        
        if not quota_info['can_create']:
            await update.callback_query.answer(
                f"❌ سهمیه شما تمام شده! {quota_info['reset_time']} ساعت دیگر تلاش کنید.",
                show_alert=True
            )
            return
        
        user_data[user_id]['state'] = 'advanced_pack_name'
        user_data[user_id]['temp_data'] = {}
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            "🤖 **ساخت استیکر پیشرفته**\n\n"
            f"📊 استیکر باقی‌مانده: {quota_info['remaining']}\n\n"
            "لطفاً نام پک استیکر خود را وارد کنید:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages based on user state"""
        user_id = update.effective_user.id
        text = update.message.text
        
        if user_id not in user_data:
            await self.start_command(update, context)
            return
        
        state = user_data[user_id]['state']
        
        if state == 'simple_pack_name':
            user_data[user_id]['temp_data']['pack_name'] = text
            user_data[user_id]['state'] = 'simple_photo'
            
            await update.message.reply_text(
                "📷 عالی! حالا لطفاً عکس مورد نظر خود را ارسال کنید:"
            )
        
        elif state == 'simple_text':
            await self.create_simple_sticker(update, context, text)
        
        elif state == 'advanced_pack_name':
            user_data[user_id]['temp_data']['pack_name'] = text
            await self.show_background_options(update, context)
        
        elif state == 'advanced_text':
            await self.create_advanced_sticker(update, context, text, user_data[user_id]['temp_data'].get('bg_type', 'default'))
        
        elif state == 'feedback_reason':
            await self.send_feedback_to_admin(update, context, text)
    
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle photo messages"""
        user_id = update.effective_user.id
        
        if user_id not in user_data:
            return
        
        state = user_data[user_id]['state']
        
        if state == 'simple_photo':
            # Save photo
            photo = update.message.photo[-1]
            user_data[user_id]['temp_data']['photo'] = photo.file_id
            user_data[user_id]['state'] = 'simple_text'
            
            await update.message.reply_text(
                "✍️ عکس دریافت شد! حالا متن استیکر خود را وارد کنید:"
            )
        
        elif state == 'advanced_background_photo':
            # Save background photo for advanced sticker
            photo = update.message.photo[-1]
            user_data[user_id]['temp_data']['background_photo'] = photo.file_id
            user_data[user_id]['state'] = 'advanced_text'
            
            await update.message.reply_text(
                "✅ عکس پس‌زمینه دریافت شد!\n\n"
                "حالا متن استیکر خود را وارد کنید:"
            )
    
    async def create_simple_sticker(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Create simple sticker"""
        user_id = update.effective_user.id
        temp_data = user_data[user_id]['temp_data']
        
        # Simulate sticker creation
        pack_name = temp_data['pack_name']
        pack_link = f"https://t.me/addstickers/{pack_name.replace(' ', '_')}"
        
        # Save to user packs
        if 'packs' not in user_data[user_id]:
            user_data[user_id]['packs'] = []
        
        user_data[user_id]['packs'].append({
            'name': pack_name,
            'link': pack_link,
            'stickers': [{'text': text, 'type': 'simple'}]
        })
        
        # Save to GitHub (simulate)
        await self.save_to_github(user_id)
        
        keyboard = [
            [InlineKeyboardButton("😊 راضی هستم", callback_data="feedback_satisfied")],
            [InlineKeyboardButton("😞 راضی نیستم", callback_data="feedback_unsatisfied")],
            [InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ **استیکر شما با موفقیت ساخته شد!**\n\n"
            f"📦 نام پک: {pack_name}\n"
            f"🔗 لینک پک: {pack_link}\n\n"
            "لطفاً نظر خود را درباره کیفیت استیکر اعلام کنید:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        user_data[user_id]['state'] = 'main_menu'
    
    def show_background_options(self, message):
        """Show background selection options"""
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("🎨 پیش‌فرض", callback_data="bg_default"))
        keyboard.add(types.InlineKeyboardButton("🔍 شفاف", callback_data="bg_transparent"))
        keyboard.add(types.InlineKeyboardButton("📷 عکس دلخواه", callback_data="bg_custom"))
        keyboard.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu"))
        
        bot.send_message(
            message.chat.id,
            "🎨 *انتخاب پس‌زمینه*\n\n"
            "لطفاً نوع پس‌زمینه مورد نظر خود را انتخاب کنید:",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    
    def show_help(self, call):
        """Show help information"""
        help_text = (
            "❓ *راهنمای استفاده از ربات*\n\n"
            "🎯 *ساخت استیکر ساده:*\n"
            "• نام پک را وارد کنید\n"
            "• عکس مورد نظر را ارسال کنید\n"
            "• متن دلخواه را تایپ کنید\n\n"
            "🤖 *ساخت استیکر پیشرفته:*\n"
            "• نام پک را تعیین کنید\n"
            "• نوع پس‌زمینه را انتخاب کنید\n"
            "• موقعیت و اندازه متن را تنظیم کنید\n"
            "• پیش‌نمایش را بررسی و تأیید کنید\n\n"
            "📦 *مدیریت پک‌ها:*\n"
            "• نام پک‌های موجود را تغییر دهید\n"
            "• استیکر جدید به پک‌های موجود اضافه کنید\n\n"
            "⚠️ *محدودیت‌ها:*\n"
            "• حداکثر 5 استیکر در 24 ساعت\n"
            "• عضویت در کانال الزامی است"
        )
        
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu"))
        
        bot.edit_message_text(
            help_text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    
    def show_support(self, call):
        """Show support information"""
        support_text = (
            "💬 *پشتیبانی*\n\n"
            "برای دریافت پشتیبانی و حل مشکلات با ما در تماس باشید:\n\n"
            f"👤 {SUPPORT_USERNAME}\n\n"
            "پاسخگویی در کمترین زمان ممکن ⚡"
        )
        
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("📱 ارتباط با پشتیبانی", url=f"https://t.me/{SUPPORT_USERNAME[1:]}"))
        keyboard.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu"))
        
        bot.edit_message_text(
            support_text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    
    def show_pack_manager(self, call):
        """Show pack manager"""
        user_id = call.from_user.id
        packs = user_data.get(user_id, {}).get('packs', [])
        
        if not packs:
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu"))
            
            bot.edit_message_text(
                "📦 *مدیریت پک‌ها*\n\n"
                "شما هنوز هیچ پکی نساخته‌اید!\n"
                "ابتدا یک استیکر بسازید.",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            return
        
        pack_list = "\n".join([f"• {pack['name']}" for pack in packs])
        
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu"))
        
        bot.edit_message_text(
            f"📦 *مدیریت پک‌ها*\n\n"
            f"پک‌های شما:\n{pack_list}\n\n"
            "برای مدیریت پک‌ها با پشتیبانی تماس بگیرید.",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    
    def handle_feedback(self, call, feedback_data: str):
        """Handle user feedback"""
        user_id = call.from_user.id
        
        if feedback_data == "feedback_satisfied":
            bot.edit_message_text(
                "🙏 *از نظر مثبت شما متشکریم!*\n\n"
                "امیدواریم همیشه از خدمات ما راضی باشید. ✨",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown'
            )
            time.sleep(2)
            self.show_main_menu(call.message.chat.id, call.message.message_id)
        
        elif feedback_data == "feedback_unsatisfied":
            user_data[user_id]['state'] = 'feedback_reason'
            
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton("🔙 انصراف", callback_data="main_menu"))
            
            bot.edit_message_text(
                "😔 *متأسفیم که راضی نبودید*\n\n"
                "لطفاً دلیل عدم رضایت خود را بنویسید تا بتوانیم بهتر خدمت‌رسانی کنیم:",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
    
    def send_feedback_to_admin(self, message, reason: str):
        """Send feedback to admin"""
        user_id = message.from_user.id
        user = message.from_user
        
        admin_message = (
            f"📝 *بازخورد جدید از کاربر*\n\n"
            f"👤 کاربر: {user.full_name}\n"
            f"🆔 ID: {user_id}\n"
            f"📱 Username: @{user.username or 'ندارد'}\n\n"
            f"💬 دلیل عدم رضایت:\n{reason}"
        )
        
        try:
            bot.send_message(ADMIN_ID, admin_message, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Failed to send feedback to admin: {e}")
        
        bot.send_message(
            message.chat.id,
            "📝 *نظر شما ثبت شد*\n\n"
            "بازخورد شما به ادمین ارسال گردید. تشکر از همکاری شما! 🙏",
            parse_mode='Markdown'
        )
        
        user_data[user_id]['state'] = 'main_menu'
        time.sleep(2)
        self.show_main_menu(message.chat.id)
    
    async def save_to_github(self, user_id: int):
        """Save user data to GitHub (simulate)"""
        try:
            # This would normally save to GitHub using the API
            logger.info(f"Saved user {user_id} data to GitHub")
        except Exception as e:
            logger.error(f"Failed to save to GitHub: {e}")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle help command"""
        help_text = (
            "❓ *راهنمای استفاده از ربات*\n\n"
            "🎯 *ساخت استیکر ساده:*\n"
            "• نام پک را وارد کنید\n"
            "• عکس مورد نظر را ارسال کنید\n"
            "• متن دلخواه را تایپ کنید\n\n"
            "🤖 *ساخت استیکر پیشرفته:*\n"
            "• نام پک را تعیین کنید\n"
            "• نوع پس‌زمینه را انتخاب کنید\n"
            "• موقعیت و اندازه متن را تنظیم کنید\n\n"
            "⚠️ *محدودیت‌ها:*\n"
            "• حداکثر 5 استیکر در 24 ساعت\n"
            "• عضویت در کانال الزامی است"
        )
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin panel (only for admin user)"""
        user_id = update.effective_user.id
        
        if user_id != ADMIN_ID:
            await update.message.reply_text("❌ شما دسترسی ادمین ندارید!")
            return
        
        stats_text = (
            f"👑 *پنل ادمین*\n\n"
            f"📊 تعداد کاربران: {len(user_data)}\n"
            f"📈 تعداد پک‌های ساخته شده: {sum(len(data.get('packs', [])) for data in user_data.values())}\n"
            f"🎯 استیکرهای امروز: {sum(1 for quota in user_quotas.values() if quota['count'] > 0)}"
        )
        
        await update.message.reply_text(stats_text, parse_mode='Markdown')
    
    async def show_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show help information"""
        help_text = (
            "❓ *راهنمای استفاده از ربات*\n\n"
            "🎯 *ساخت استیکر ساده:*\n"
            "• نام پک را وارد کنید\n"
            "• عکس مورد نظر را ارسال کنید\n"
            "• متن دلخواه را تایپ کنید\n\n"
            "🤖 *ساخت استیکر پیشرفته:*\n"
            "• نام پک را تعیین کنید\n"
            "• نوع پس‌زمینه را انتخاب کنید\n"
            "• موقعیت و اندازه متن را تنظیم کنید\n"
            "• پیش‌نمایش را بررسی و تأیید کنید\n\n"
            "📦 *مدیریت پک‌ها:*\n"
            "• نام پک‌های موجود را تغییر دهید\n"
            "• استیکر جدید به پک‌های موجود اضافه کنید\n\n"
            "⚠️ *محدودیت‌ها:*\n"
            "• حداکثر 5 استیکر در 24 ساعت\n"
            "• عضویت در کانال الزامی است"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            help_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def show_support(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show support information"""
        support_text = (
            "💬 *پشتیبانی*\n\n"
            "برای دریافت پشتیبانی و حل مشکلات با ما در تماس باشید:\n\n"
            f"👤 {SUPPORT_USERNAME}\n\n"
            "پاسخگویی در کمترین زمان ممکن ⚡"
        )
        
        keyboard = [
            [InlineKeyboardButton("📱 ارتباط با پشتیبانی", url=f"https://t.me/{SUPPORT_USERNAME[1:]}")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            support_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def show_pack_manager(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show pack manager"""
        user_id = update.effective_user.id
        packs = user_data.get(user_id, {}).get('packs', [])
        
        if not packs:
            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(
                "📦 *مدیریت پک‌ها*\n\n"
                "شما هنوز هیچ پکی نساخته‌اید!\n"
                "ابتدا یک استیکر بسازید.",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            return
        
        pack_list = "\n".join([f"• {pack['name']}" for pack in packs])
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            f"📦 *مدیریت پک‌ها*\n\n"
            f"پک‌های شما:\n{pack_list}\n\n"
            "برای مدیریت پک‌ها با پشتیبانی تماس بگیرید.",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def handle_feedback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, feedback_data: str):
        """Handle user feedback"""
        user_id = update.effective_user.id
        
        if feedback_data == "feedback_satisfied":
            await update.callback_query.edit_message_text(
                "🙏 *از نظر مثبت شما متشکریم!*\n\n"
                "امیدواریم همیشه از خدمات ما راضی باشید. ✨",
                parse_mode='Markdown'
            )
            await asyncio.sleep(2)
            await self.show_main_menu(update, context)
        
        elif feedback_data == "feedback_unsatisfied":
            user_data[user_id]['state'] = 'feedback_reason'
            
            keyboard = [[InlineKeyboardButton("🔙 انصراف", callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(
                "😔 *متأسفیم که راضی نبودید*\n\n"
                "لطفاً دلیل عدم رضایت خود را بنویسید تا بتوانیم بهتر خدمت‌رسانی کنیم:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    
    async def handle_background_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE, bg_data: str):
        """Handle background selection for advanced stickers"""
        user_id = update.effective_user.id
        bg_type = bg_data.replace('bg_', '')
        
        user_data[user_id]['temp_data']['bg_type'] = bg_type
        
        if bg_type == 'custom':
            user_data[user_id]['state'] = 'advanced_background_photo'
            await update.callback_query.edit_message_text(
                "📷 **عکس پس‌زمینه**\n\n"
                "لطفاً عکس مورد نظر خود را برای پس‌زمینه ارسال کنید:",
                parse_mode='Markdown'
            )
        else:
            user_data[user_id]['state'] = 'advanced_text'
            await update.callback_query.edit_message_text(
                f"✍️ **متن استیکر**\n\n"
                f"پس‌زمینه انتخاب شده: {bg_type}\n\n"
                "حالا متن استیکر خود را وارد کنید:",
                parse_mode='Markdown'
            )
    
    async def send_feedback_to_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE, reason: str):
        """Send feedback to admin"""
        user_id = update.effective_user.id
        user = update.effective_user
        
        admin_message = (
            f"📝 *بازخورد جدید از کاربر*\n\n"
            f"👤 کاربر: {user.full_name}\n"
            f"🆔 ID: {user_id}\n"
            f"📱 Username: @{user.username or 'ندارد'}\n\n"
            f"💬 دلیل عدم رضایت:\n{reason}"
        )
        
        try:
            await context.bot.send_message(ADMIN_ID, admin_message, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Failed to send feedback to admin: {e}")
        
        await update.message.reply_text(
            "📝 *نظر شما ثبت شد*\n\n"
            "بازخورد شما به ادمین ارسال گردید. تشکر از همکاری شما! 🙏",
            parse_mode='Markdown'
        )
        
        user_data[user_id]['state'] = 'main_menu'
        await asyncio.sleep(2)
        await self.show_main_menu(update, context)
    
    async def show_background_options(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show background selection options"""
        keyboard = [
            [InlineKeyboardButton("🎨 پیش‌فرض", callback_data="bg_default")],
            [InlineKeyboardButton("🔍 شفاف", callback_data="bg_transparent")],
            [InlineKeyboardButton("📷 عکس دلخواه", callback_data="bg_custom")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🎨 **انتخاب پس‌زمینه**\n\n"
            "لطفاً نوع پس‌زمینه مورد نظر خود را انتخاب کنید:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def create_advanced_sticker(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, bg_type: str = 'default'):
        """Create advanced sticker with background options"""
        user_id = update.effective_user.id
        temp_data = user_data[user_id]['temp_data']
        
        try:
            # Check quota
            quota_info = self.get_quota_info(user_id)
            if not quota_info['can_create']:
                await update.message.reply_text(
                    f"❌ سهمیه شما تمام شده! {quota_info['reset_time']} ساعت دیگر تلاش کنید."
                )
                return
            
            # Update quota
            user_quotas[user_id]['count'] += 1
            
            # Create sticker based on background type
            if bg_type == 'transparent':
                sticker_image = await self.create_transparent_sticker(text)
            elif bg_type == 'custom' and 'background_photo' in temp_data:
                photo_file = await context.bot.get_file(temp_data['background_photo'])
                photo_bytes = await photo_file.download_as_bytearray()
                sticker_image = await self.create_sticker_with_text(bytes(photo_bytes), text)
            else:
                sticker_image = await self.create_gradient_sticker(text)
            
            # Send the sticker
            await update.message.reply_photo(
                photo=sticker_image,
                caption=f"✅ استیکر پیشرفته شما آماده شد!\n📦 پک: {temp_data['pack_name']}"
            )
            
            # Save to user packs
            pack_name = temp_data['pack_name'].replace(' ', '_').lower()
            pack_link = f"https://t.me/addstickers/{pack_name}_{user_id}"
            
            if 'packs' not in user_data[user_id]:
                user_data[user_id]['packs'] = []
            
            user_data[user_id]['packs'].append({
                'name': temp_data['pack_name'],
                'link': pack_link,
                'stickers': [{'text': text, 'type': 'advanced', 'background': bg_type, 'created_at': datetime.now().isoformat()}]
            })
            
            await self.save_to_github(user_id)
            
            keyboard = [
                [InlineKeyboardButton("😊 راضی هستم", callback_data="feedback_satisfied")],
                [InlineKeyboardButton("😞 راضی نیستم", callback_data="feedback_unsatisfied")],
                [InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"🎉 **استیکر پیشرفته با موفقیت ساخته شد!**\n\n"
                f"📦 نام پک: {temp_data['pack_name']}\n"
                f"🎨 نوع پس‌زمینه: {bg_type}\n"
                f"🔗 لینک پک: {pack_link}\n\n"
                "لطفاً نظر خود را اعلام کنید:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error creating advanced sticker: {e}")
            await update.message.reply_text(
                "❌ خطا در ساخت استیکر! لطفاً دوباره تلاش کنید."
            )
        
        user_data[user_id]['state'] = 'main_menu'
    
    async def create_transparent_sticker(self, text: str) -> BytesIO:
        """Create sticker with transparent background"""
        try:
            # Create transparent image
            img = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            # Process Persian text
            persian_text = self.process_persian_text(text)
            
            # Load font
            try:
                font = ImageFont.truetype("fonts/Vazir-Regular.ttf", 60)
            except:
                try:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 60)
                except:
                    font = ImageFont.load_default()
            
            # Calculate text position (center)
            bbox = draw.textbbox((0, 0), persian_text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            x = (512 - text_width) // 2
            y = (512 - text_height) // 2
            
            # Draw text with strong outline
            outline_width = 4
            for adj_x in range(-outline_width, outline_width + 1):
                for adj_y in range(-outline_width, outline_width + 1):
                    if adj_x != 0 or adj_y != 0:
                        draw.text((x + adj_x, y + adj_y), persian_text, font=font, fill=(0, 0, 0, 255))
            
            # Draw main text
            draw.text((x, y), persian_text, font=font, fill=(255, 255, 255, 255))
            
            output = BytesIO()
            img.save(output, format='PNG')
            output.seek(0)
            return output
            
        except Exception as e:
            logger.error(f"Error creating transparent sticker: {e}")
            return await self.create_gradient_sticker(text)
    
    async def create_gradient_sticker(self, text: str) -> BytesIO:
        """Create sticker with gradient background"""
        try:
            # Create gradient background
            img = Image.new('RGBA', (512, 512), (255, 255, 255, 255))
            
            # Create gradient
            for y in range(512):
                r = int(100 + (y / 512) * 155)  # 100 to 255
                g = int(150 + (y / 512) * 105)  # 150 to 255
                b = int(255 - (y / 512) * 100)  # 255 to 155
                
                for x in range(512):
                    img.putpixel((x, y), (r, g, b, 255))
            
            draw = ImageDraw.Draw(img)
            
            # Process Persian text
            persian_text = self.process_persian_text(text)
            
            # Load font
            try:
                font = ImageFont.truetype("fonts/Vazir-Regular.ttf", 50)
            except:
                try:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 50)
                except:
                    font = ImageFont.load_default()
            
            # Calculate text position (center)
            bbox = draw.textbbox((0, 0), persian_text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            x = (512 - text_width) // 2
            y = (512 - text_height) // 2
            
            # Draw text outline
            outline_width = 3
            for adj_x in range(-outline_width, outline_width + 1):
                for adj_y in range(-outline_width, outline_width + 1):
                    if adj_x != 0 or adj_y != 0:
                        draw.text((x + adj_x, y + adj_y), persian_text, font=font, fill=(0, 0, 0, 200))
            
            # Draw main text
            draw.text((x, y), persian_text, font=font, fill=(255, 255, 255, 255))
            
            output = BytesIO()
            img.save(output, format='PNG')
            output.seek(0)
            return output
            
        except Exception as e:
            logger.error(f"Error creating gradient sticker: {e}")
            # Fallback to simple colored background
            img = Image.new('RGBA', (512, 512), (100, 150, 255, 255))
            draw = ImageDraw.Draw(img)
            draw.text((50, 250), text, fill=(255, 255, 255, 255))
            
            output = BytesIO()
            img.save(output, format='PNG')
            output.seek(0)
            return output
    
    def run(self):
        """Start the bot"""
        logger.info("Starting Advanced Sticker Bot...")
        self.application.run_polling()

if __name__ == '__main__':
    sticker_bot = StickerBot()
    sticker_bot.run()
