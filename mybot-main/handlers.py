#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Handler functions for Advanced Sticker Bot
"""

import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from PIL import Image, ImageDraw, ImageFont, ImageOps
import requests
from io import BytesIO

from config import *

class StickerHandler:
    def __init__(self):
        self.user_data = {}
        self.user_quotas = {}
    
    async def create_sticker_image(self, 
                                 text: str, 
                                 background_type: str = 'default',
                                 text_position: str = 'center',
                                 font_size: int = 24,
                                 background_image: Optional[bytes] = None) -> BytesIO:
        """Create sticker image with Persian text support"""
        
        # Create base image
        if background_type == 'transparent':
            img = Image.new('RGBA', (STICKER_WIDTH, STICKER_HEIGHT), (0, 0, 0, 0))
        elif background_type == 'custom' and background_image:
            bg_img = Image.open(BytesIO(background_image))
            img = bg_img.resize((STICKER_WIDTH, STICKER_HEIGHT))
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
        else:
            # Default gradient background
            img = Image.new('RGBA', (STICKER_WIDTH, STICKER_HEIGHT), (255, 255, 255, 255))
            draw = ImageDraw.Draw(img)
            for i in range(STICKER_HEIGHT):
                color = int(255 - (i / STICKER_HEIGHT) * 50)
                draw.line([(0, i), (STICKER_WIDTH, i)], fill=(color, color, 255, 255))
        
        # Load font with better fallback system
        font_paths = [
            FONT_PATH,
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"
        ]
        
        font = None
        for font_path in font_paths:
            try:
                if os.path.exists(font_path):
                    font = ImageFont.truetype(font_path, font_size)
                    break
            except:
                continue
        
        if font is None:
            try:
                font = ImageFont.load_default()
            except:
                font = None
        
        # Prepare text (Persian RTL support)
        lines = self.prepare_persian_text(text, font, STICKER_WIDTH - 40)
        
        # Calculate text dimensions
        draw = ImageDraw.Draw(img)
        total_height = len(lines) * font_size * 1.2
        
        # Get position coordinates
        pos_x, pos_y = TEXT_POSITIONS.get(text_position, (0.5, 0.5))
        
        # Calculate starting position
        start_x = int(pos_x * STICKER_WIDTH)
        start_y = int(pos_y * STICKER_HEIGHT - total_height / 2)
        
        # Draw text with outline for better visibility
        for i, line in enumerate(lines):
            line_y = start_y + i * int(font_size * 1.2)
            
            # Get text width for centering
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            line_x = start_x - text_width // 2
            
            # Draw outline
            for adj_x in range(-2, 3):
                for adj_y in range(-2, 3):
                    if adj_x != 0 or adj_y != 0:
                        draw.text((line_x + adj_x, line_y + adj_y), line, 
                                font=font, fill=(0, 0, 0, 128))
            
            # Draw main text
            draw.text((line_x, line_y), line, font=font, fill=(255, 255, 255, 255))
        
        # Save to BytesIO
        output = BytesIO()
        img.save(output, format='PNG')
        output.seek(0)
        
        return output
    
    def prepare_persian_text(self, text: str, font, max_width: int) -> List[str]:
        """Prepare Persian text with proper RTL direction and line wrapping"""
        words = text.split()
        lines = []
        current_line = ""
        
        for word in words:
            test_line = f"{current_line} {word}".strip()
            
            # Check if line fits
            bbox = ImageDraw.Draw(Image.new('RGB', (1, 1))).textbbox((0, 0), test_line, font=font)
            line_width = bbox[2] - bbox[0]
            
            if line_width <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        
        if current_line:
            lines.append(current_line)
        
        # Better Persian text handling - don't reverse individual characters
        # The reshaping should be done at text level, not line level
        if any('\u0600' <= char <= '\u06FF' for char in text):
            # Try to use proper Persian text processing
            try:
                from arabic_reshaper import reshape
                from bidi.algorithm import get_display
                
                # Process each line properly
                processed_lines = []
                for line in lines:
                    reshaped = reshape(line)
                    bidi_line = get_display(reshaped)
                    processed_lines.append(bidi_line)
                lines = processed_lines
            except ImportError:
                # Simple fallback: reverse word order but keep characters intact
                processed_lines = []
                for line in lines:
                    words = line.split()
                    if len(words) > 1:
                        processed_lines.append(' '.join(reversed(words)))
                    else:
                        processed_lines.append(line)
                lines = processed_lines
        
        return lines
    
    async def download_photo(self, context: ContextTypes.DEFAULT_TYPE, file_id: str) -> bytes:
        """Download photo from Telegram"""
        file = await context.bot.get_file(file_id)
        file_bytes = await file.download_as_bytearray()
        return bytes(file_bytes)
    
    def save_user_pack(self, user_id: int, pack_data: Dict):
        """Save user pack data"""
        if user_id not in self.user_data:
            self.user_data[user_id] = {'packs': []}
        
        # Check if pack exists
        existing_pack = None
        for pack in self.user_data[user_id]['packs']:
            if pack['name'] == pack_data['name']:
                existing_pack = pack
                break
        
        if existing_pack:
            existing_pack['stickers'].append(pack_data['sticker'])
        else:
            self.user_data[user_id]['packs'].append({
                'name': pack_data['name'],
                'link': pack_data['link'],
                'stickers': [pack_data['sticker']],
                'created_at': datetime.now().isoformat()
            })
    
    async def save_to_github(self, user_id: int):
        """Save user data to GitHub repository"""
        try:
            # Prepare data
            user_file_data = {
                'user_id': user_id,
                'packs': self.user_data.get(user_id, {}).get('packs', []),
                'last_updated': datetime.now().isoformat()
            }
            
            # GitHub API call would go here
            # For now, save locally
            filename = f"{DATA_DIR}/user_{user_id}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(user_file_data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"Error saving to GitHub: {e}")
            return False
    
    def update_quota(self, user_id: int) -> bool:
        """Update user quota and return if creation is allowed"""
        now = datetime.now()
        
        if user_id not in self.user_quotas:
            self.user_quotas[user_id] = {
                'count': 0,
                'reset_time': now + timedelta(hours=QUOTA_RESET_HOURS)
            }
        
        quota = self.user_quotas[user_id]
        
        # Reset quota if time passed
        if now >= quota['reset_time']:
            quota['count'] = 0
            quota['reset_time'] = now + timedelta(hours=QUOTA_RESET_HOURS)
        
        # Check if can create
        if quota['count'] >= MAX_STICKERS_PER_DAY:
            return False
        
        # Increment count
        quota['count'] += 1
        return True
    
    def get_quota_status(self, user_id: int) -> Dict:
        """Get current quota status for user"""
        now = datetime.now()
        
        if user_id not in self.user_quotas:
            return {
                'remaining': MAX_STICKERS_PER_DAY,
                'reset_time': '24:00:00',
                'can_create': True
            }
        
        quota = self.user_quotas[user_id]
        
        # Reset if time passed
        if now >= quota['reset_time']:
            quota['count'] = 0
            quota['reset_time'] = now + timedelta(hours=QUOTA_RESET_HOURS)
        
        remaining = max(0, MAX_STICKERS_PER_DAY - quota['count'])
        time_left = quota['reset_time'] - now
        hours, remainder = divmod(int(time_left.total_seconds()), 3600)
        minutes, _ = divmod(remainder, 60)
        reset_time = f"{hours:02d}:{minutes:02d}:00"
        
        return {
            'remaining': remaining,
            'reset_time': reset_time,
            'can_create': remaining > 0
        }

class PackManager:
    def __init__(self, sticker_handler: StickerHandler):
        self.sticker_handler = sticker_handler
    
    def get_user_packs(self, user_id: int) -> List[Dict]:
        """Get all packs for a user"""
        return self.sticker_handler.user_data.get(user_id, {}).get('packs', [])
    
    def rename_pack(self, user_id: int, old_name: str, new_name: str) -> bool:
        """Rename a user's pack"""
        packs = self.get_user_packs(user_id)
        
        for pack in packs:
            if pack['name'] == old_name:
                pack['name'] = new_name
                pack['link'] = f"https://t.me/addstickers/{new_name.replace(' ', '_')}"
                return True
        
        return False
    
    def delete_pack(self, user_id: int, pack_name: str) -> bool:
        """Delete a user's pack"""
        if user_id not in self.sticker_handler.user_data:
            return False
        
        packs = self.sticker_handler.user_data[user_id]['packs']
        original_length = len(packs)
        
        self.sticker_handler.user_data[user_id]['packs'] = [
            pack for pack in packs if pack['name'] != pack_name
        ]
        
        return len(self.sticker_handler.user_data[user_id]['packs']) < original_length
