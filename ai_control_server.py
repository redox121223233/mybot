from flask import Flask, request, jsonify, render_template_string
import json
import os
import time
from datetime import datetime

app = Flask(__name__)

# فایل ذخیره وضعیت
AI_STATUS_FILE = "ai_status.json"

# وضعیت پیش‌فرض
default_status = {
    "active": False,
    "last_updated": time.time(),
    "updated_by": "system"
}

def load_ai_status():
    """بارگذاری وضعیت هوش مصنوعی از فایل"""
    try:
        if os.path.exists(AI_STATUS_FILE):
            with open(AI_STATUS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return default_status.copy()
    except Exception as e:
        print(f"خطا در بارگذاری وضعیت: {e}")
        return default_status.copy()

def save_ai_status(status):
    """ذخیره وضعیت هوش مصنوعی در فایل"""
    try:
        status["last_updated"] = time.time()
        with open(AI_STATUS_FILE, 'w', encoding='utf-8') as f:
            json.dump(status, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"خطا در ذخیره وضعیت: {e}")
        return False

def is_ai_active():
    """بررسی اینکه هوش مصنوعی فعال است یا نه"""
    status = load_ai_status()
    return status.get("active", False)

@app.route('/')
def index():
    """صفحه اصلی کنترل هوش مصنوعی"""
    try:
        with open('ai_control_interface.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return """
        <h1>خطا: فایل رابط کاربری پیدا نشد</h1>
        <p>لطفاً مطمئن شوید که فایل ai_control_interface.html در همین پوشه موجود است.</p>
        """

@app.route('/api/ai-status', methods=['GET'])
def get_ai_status():
    """دریافت وضعیت فعلی هوش مصنوعی"""
    status = load_ai_status()
    return jsonify({
        "active": status.get("active", False),
        "last_updated": status.get("last_updated", 0),
        "updated_by": status.get("updated_by", "unknown"),
        "timestamp": time.time(),
        "formatted_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

@app.route('/api/ai-status', methods=['POST'])
def set_ai_status():
    """تنظیم وضعیت هوش مصنوعی"""
    try:
        data = request.get_json()
        if data is None:
            return jsonify({"error": "داده‌های JSON نامعتبر"}), 400
        
        active = data.get('active')
        if active is None:
            return jsonify({"error": "پارامتر 'active' الزامی است"}), 400
        
        # بارگذاری وضعیت فعلی
        current_status = load_ai_status()
        
        # به‌روزرسانی وضعیت
        current_status["active"] = bool(active)
        current_status["updated_by"] = request.remote_addr or "unknown"
        
        # ذخیره وضعیت جدید
        if save_ai_status(current_status):
            return jsonify({
                "success": True,
                "message": "وضعیت با موفقیت به‌روزرسانی شد",
                "active": current_status["active"],
                "timestamp": current_status["last_updated"]
            })
        else:
            return jsonify({"error": "خطا در ذخیره وضعیت"}), 500
            
    except Exception as e:
        return jsonify({"error": f"خطا در پردازش درخواست: {str(e)}"}), 500

@app.route('/api/toggle', methods=['POST'])
def toggle_ai_status():
    """تغییر وضعیت هوش مصنوعی (فعال/غیرفعال)"""
    try:
        current_status = load_ai_status()
        current_status["active"] = not current_status.get("active", False)
        current_status["updated_by"] = request.remote_addr or "unknown"
        
        if save_ai_status(current_status):
            return jsonify({
                "success": True,
                "message": "وضعیت تغییر کرد",
                "active": current_status["active"],
                "timestamp": current_status["last_updated"]
            })
        else:
            return jsonify({"error": "خطا در ذخیره وضعیت"}), 500
            
    except Exception as e:
        return jsonify({"error": f"خطا در تغییر وضعیت: {str(e)}"}), 500

@app.route('/api/check', methods=['GET'])
def check_ai_active():
    """بررسی ساده وضعیت هوش مصنوعی (برای استفاده در n8n)"""
    active = is_ai_active()
    return jsonify({
        "active": active,
        "status": "فعال" if active else "غیرفعال",
        "timestamp": time.time()
    })

@app.route('/webhook/ai-control', methods=['POST'])
def ai_control_webhook():
    """وب‌هوک برای کنترل هوش مصنوعی از n8n"""
    try:
        data = request.get_json()
        
        # بررسی کلید امنیتی (اختیاری)
        secret_key = data.get('secret_key')
        expected_key = os.environ.get('AI_CONTROL_SECRET', 'default_secret')
        
        if secret_key != expected_key:
            return jsonify({"error": "کلید امنیتی نامعتبر"}), 401
        
        action = data.get('action')
        
        if action == 'activate':
            current_status = load_ai_status()
            current_status["active"] = True
            current_status["updated_by"] = "n8n_webhook"
            save_ai_status(current_status)
            return jsonify({"success": True, "message": "هوش مصنوعی فعال شد", "active": True})
            
        elif action == 'deactivate':
            current_status = load_ai_status()
            current_status["active"] = False
            current_status["updated_by"] = "n8n_webhook"
            save_ai_status(current_status)
            return jsonify({"success": True, "message": "هوش مصنوعی غیرفعال شد", "active": False})
            
        elif action == 'toggle':
            current_status = load_ai_status()
            current_status["active"] = not current_status.get("active", False)
            current_status["updated_by"] = "n8n_webhook"
            save_ai_status(current_status)
            return jsonify({
                "success": True, 
                "message": "وضعیت تغییر کرد", 
                "active": current_status["active"]
            })
            
        elif action == 'status':
            status = load_ai_status()
            return jsonify({
                "active": status.get("active", False),
                "last_updated": status.get("last_updated", 0),
                "updated_by": status.get("updated_by", "unknown")
            })
            
        else:
            return jsonify({"error": "عمل نامعتبر. اعمال مجاز: activate, deactivate, toggle, status"}), 400
            
    except Exception as e:
        return jsonify({"error": f"خطا در پردازش وب‌هوک: {str(e)}"}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """بررسی سلامت سرور"""
    return jsonify({
        "status": "healthy",
        "timestamp": time.time(),
        "ai_active": is_ai_active()
    })

# تابع کمکی برای استفاده در بات تلگرام
def should_ai_respond():
    """بررسی اینکه آیا هوش مصنوعی باید پاسخ دهد یا نه"""
    return is_ai_active()

if __name__ == '__main__':
    # تنظیم encoding برای Windows
    import sys
    if sys.platform.startswith('win'):
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())
    
    print("سرور کنترل هوش مصنوعی در حال راه‌اندازی...")
    print(f"فایل وضعیت: {AI_STATUS_FILE}")
    
    # بارگذاری وضعیت اولیه
    initial_status = load_ai_status()
    status_text = 'فعال' if initial_status['active'] else 'غیرفعال'
    print(f"وضعیت اولیه: {status_text}")
    
    # راه‌اندازی سرور
    port = int(os.environ.get('AI_CONTROL_PORT', 5000))
    print(f"سرور در حال اجرا روی پورت: {port}")
    app.run(host='0.0.0.0', port=port, debug=False)

