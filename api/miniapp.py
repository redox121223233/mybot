#!/usr/bin/env python3
"""
Telegram Mini App Backend
Handles mini app requests and sticker creation
"""

import os
import json
import logging
import io
import uuid
from datetime import datetime, timezone
from flask import Flask, request, jsonify, send_from_directory
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Configuration
ADMIN_ID = 6053579919
SUPPORT_USERNAME = "@onedaytoalive"
ADVANCED_DAILY_LIMIT = 3

# Data storage
USERS: dict[int, dict] = {}
USER_PACKAGES: dict[int, list] = {}
USER_LIMITS: dict[int, dict] = {}

# File paths
USERS_FILE = "/tmp/users.json"
PACKAGES_FILE = "/tmp/packages.json"
LIMITS_FILE = "/tmp/user_limits.json"

def load_data():
    """Load data from files"""
    global USERS, USER_PACKAGES, USER_LIMITS
    try:
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, 'r') as f:
                USERS = json.load(f)
        if os.path.exists(PACKAGES_FILE):
            with open(PACKAGES_FILE, 'r') as f:
                USER_PACKAGES = json.load(f)
        if os.path.exists(LIMITS_FILE):
            with open(LIMITS_FILE, 'r') as f:
                USER_LIMITS = json.load(f)
    except Exception as e:
        logger.error(f"Error loading data: {e}")

def save_data():
    """Save data to files"""
    try:
        with open(USERS_FILE, 'w') as f:
            json.dump(USERS, f)
        with open(PACKAGES_FILE, 'w') as f:
            json.dump(USER_PACKAGES, f)
        with open(LIMITS_FILE, 'w') as f:
            json.dump(USER_LIMITS, f)
    except Exception as e:
        logger.error(f"Error saving data: {e}")

def get_user_limits(user_id: int) -> dict:
    """Get or create user limits"""
    if user_id not in USER_LIMITS:
        USER_LIMITS[user_id] = {
            "advanced_used": 0,
            "last_reset": datetime.now(timezone.utc).isoformat(),
            "advanced_count_today": 0
        }
        save_data()
    return USER_LIMITS[user_id]

def can_use_advanced(user_id: int) -> bool:
    """Check if user can use advanced mode"""
    limits = get_user_limits(user_id)
    try:
        last_reset = datetime.fromisoformat(limits["last_reset"])
        now = datetime.now(timezone.utc)
        
        # Reset if 24 hours have passed
        if (now - last_reset).days >= 1:
            limits["advanced_count_today"] = 0
            limits["last_reset"] = now.isoformat()
            save_data()
    except:
        limits["advanced_count_today"] = 0
        limits["last_reset"] = datetime.now(timezone.utc).isoformat()
        save_data()
    
    return limits["advanced_count_today"] < ADVANCED_DAILY_LIMIT

def use_advanced_sticker(user_id: int):
    """Use one advanced sticker"""
    limits = get_user_limits(user_id)
    limits["advanced_count_today"] += 1
    save_data()

def get_remaining_advanced(user_id: int) -> int:
    """Get remaining advanced stickers"""
    return ADVANCED_DAILY_LIMIT - get_user_limits(user_id)["advanced_count_today"]

def create_sticker(text: str, image_data: bytes, 
                   position_x: int = 256, position_y: int = 256,
                   font_size: int = 40, text_color: str = "#FFFFFF",
                   font_family: str = "Vazirmatn") -> bytes:
    """Create sticker with text and image"""
    try:
        # Load image
        img = Image.open(io.BytesIO(image_data))
        img = img.convert('RGBA')
        
        # Resize to 512x512 maintaining aspect ratio
        img.thumbnail((512, 512), Image.Resampling.LANCZOS)
        
        # Create 512x512 canvas
        canvas = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
        
        # Center the image
        x_offset = (512 - img.width) // 2
        y_offset = (512 - img.height) // 2
        canvas.paste(img, (x_offset, y_offset), img)
        img = canvas
        
        draw = ImageDraw.Draw(img)
        
        # Process Arabic/Persian text
        try:
            reshaped_text = arabic_reshaper.reshape(text)
            display_text = get_display(reshaped_text)
        except:
            display_text = text
        
        # Load font
        font = None
        font_paths = [
            f"fonts/{font_family}-Regular.ttf",
            f"fonts/{font_family}.ttf",
            "fonts/Vazirmatn-Regular.ttf",
            "fonts/IRANSans.ttf",
            "/System/Library/Fonts/Arial.ttf"
        ]
        
        for path in font_paths:
            if os.path.exists(path):
                try:
                    font = ImageFont.truetype(path, font_size)
                    break
                except:
                    continue
        
        if not font:
            font = ImageFont.load_default()
        
        # Get text dimensions
        bbox = draw.textbbox((0, 0), display_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Draw text at specified position
        x = position_x - text_width // 2
        y = position_y - text_height // 2
        
        # Add shadow
        draw.text((x + 2, y + 2), display_text, font=font, fill="#000000")
        
        # Draw main text
        draw.text((x, y), display_text, font=font, fill=text_color)
        
        # Convert to WebP
        output = io.BytesIO()
        img.save(output, format='WebP', quality=95, optimize=True)
        output.seek(0)
        
        return output.getvalue()
        
    except Exception as e:
        logger.error(f"Error creating sticker: {e}")
        return None

def get_user_packages(user_id: int) -> list:
    """Get user's sticker packages"""
    if user_id not in USER_PACKAGES:
        USER_PACKAGES[user_id] = []
        save_data()
    return USER_PACKAGES[user_id]

def create_package(user_id: int, package_name: str) -> dict:
    """Create a new sticker package"""
    packages = get_user_packages(user_id)
    
    # Check if package already exists
    for pkg in packages:
        if pkg['name'] == package_name:
            return pkg
    
    # Create new package
    new_package = {
        'id': str(uuid.uuid4()),
        'name': package_name,
        'link': f"https://t.me/addstickers/{package_name.lower().replace(' ', '_')}",
        'stickers': [],
        'created_at': datetime.now(timezone.utc).isoformat()
    }
    
    packages.append(new_package)
    save_data()
    
    return new_package

def add_sticker_to_package(user_id: int, package_id: str, sticker_data: dict):
    """Add sticker to package"""
    packages = get_user_packages(user_id)
    
    for pkg in packages:
        if pkg['id'] == package_id:
            sticker_data['id'] = str(uuid.uuid4())
            sticker_data['created_at'] = datetime.now(timezone.utc).isoformat()
            pkg['stickers'].append(sticker_data)
            save_data()
            return True
    
    return False

# Routes
@app.route('/')
def home():
    """Serve the mini app"""
    return send_from_directory('templates', 'index.html')

@app.route('/api/user-info', methods=['POST'])
def get_user_info():
    """Get user information"""
    try:
        data = request.json
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'User ID required'}), 400
        
        # Register user if not exists
        if user_id not in USERS:
            USERS[user_id] = {
                'first_name': data.get('first_name', ''),
                'username': data.get('username', ''),
                'joined_at': datetime.now(timezone.utc).isoformat()
            }
            save_data()
        
        remaining = get_remaining_advanced(user_id)
        packages = get_user_packages(user_id)
        
        return jsonify({
            'user': USERS[user_id],
            'remaining_advanced': remaining,
            'advanced_limit': ADVANCED_DAILY_LIMIT,
            'packages': packages
        })
        
    except Exception as e:
        logger.error(f"Error in user info: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/create-sticker', methods=['POST'])
def create_sticker_endpoint():
    """Create a sticker"""
    try:
        data = request.json
        user_id = data.get('user_id')
        package_name = data.get('package_name')
        text = data.get('text')
        image_data = data.get('image_data')  # Base64 encoded
        sticker_type = data.get('type', 'simple')
        
        if not all([user_id, package_name, text, image_data]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Check if package exists, create if not
        packages = get_user_packages(user_id)
        package = None
        for pkg in packages:
            if pkg['name'] == package_name:
                package = pkg
                break
        
        if not package:
            package = create_package(user_id, package_name)
        
        # Check advanced limits
        if sticker_type == 'advanced':
            if not can_use_advanced(user_id):
                return jsonify({'error': 'Daily advanced limit exceeded'}), 429
            use_advanced_sticker(user_id)
        
        # Decode image data
        import base64
        image_bytes = base64.b64decode(image_data.split(',')[1])
        
        # Create sticker
        sticker_bytes = create_sticker(
            text=text,
            image_data=image_bytes,
            position_x=data.get('position_x', 256),
            position_y=data.get('position_y', 256),
            font_size=data.get('font_size', 40),
            text_color=data.get('text_color', '#FFFFFF'),
            font_family=data.get('font_family', 'Vazirmatn')
        )
        
        if not sticker_bytes:
            return jsonify({'error': 'Failed to create sticker'}), 500
        
        # Save sticker to temporary file
        sticker_id = str(uuid.uuid4())
        temp_path = f"/tmp/{sticker_id}.webp"
        with open(temp_path, 'wb') as f:
            f.write(sticker_bytes)
        
        # Add sticker to package
        sticker_info = {
            'id': sticker_id,
            'text': text,
            'type': sticker_type,
            'file_path': temp_path
        }
        
        if add_sticker_to_package(user_id, package['id'], sticker_info):
            return jsonify({
                'success': True,
                'sticker_id': sticker_id,
                'package_link': package['link'],
                'remaining_advanced': get_remaining_advanced(user_id)
            })
        else:
            return jsonify({'error': 'Failed to add sticker to package'}), 500
        
    except Exception as e:
        logger.error(f"Error creating sticker: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/package/<package_id>')
def get_package(package_id):
    """Get package details"""
    try:
        for user_id, packages in USER_PACKAGES.items():
            for pkg in packages:
                if pkg['id'] == package_id:
                    return jsonify(pkg)
        
        return jsonify({'error': 'Package not found'}), 404
        
    except Exception as e:
        logger.error(f"Error getting package: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/tmp/<filename>')
def serve_file(filename):
    """Serve temporary files"""
    try:
        return send_from_directory('/tmp', filename)
    except:
        return "File not found", 404

if __name__ == '__main__':
    load_data()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)