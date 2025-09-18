import json
import os
import time
import logging
from typing import Dict, Any, Optional

# Configure logger directly
logger = logging.getLogger("database_manager")

class DatabaseManager:
    """مدیریت ذخیره‌سازی و بارگذاری داده‌های ربات"""
    
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.files = {
            'users': os.path.join(base_dir, 'users.json'),
            'subscriptions': os.path.join(base_dir, 'subscriptions.json'),
            'payments': os.path.join(base_dir, 'pending_payments.json'),
            'feedback': os.path.join(base_dir, 'feedback_data.json'),
            'packs': os.path.join(base_dir, 'user_packs.json'),
            'settings': os.path.join(base_dir, 'bot_settings.json')
        }
        
        os.makedirs(base_dir, exist_ok=True)
        
        self.data = {}
        self.load_all_data()
    
    def load_all_data(self):
        for key, filepath in self.files.items():
            self.data[key] = self.load_json_file(filepath)
    
    def load_json_file(self, filepath: str) -> Dict[str, Any]:
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.info(f"Loaded {len(data)} items from {os.path.basename(filepath)}")
                    return data
            else:
                logger.info(f"File not found, creating empty: {os.path.basename(filepath)}")
                return {}
        except Exception as e:
            logger.error(f"Error loading {filepath}: {e}")
            return {}
    
    def save_json_file(self, key: str, data: Dict[str, Any]):
        try:
            filepath = self.files[key]
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved {len(data)} items to {os.path.basename(filepath)}")
        except Exception as e:
            logger.error(f"Error saving {key}: {e}")
    
    def save_all_data(self):
        for key in self.data:
            self.save_json_file(key, self.data[key])
    
    # -------------------- User methods --------------------
    def get_user_data(self, user_id: int) -> Dict[str, Any]:
        return self.data['users'].get(str(user_id), {})
    
    def set_user_data(self, user_id: int, data: Dict[str, Any]):
        self.data['users'][str(user_id)] = data
        self.save_json_file('users', self.data['users'])
    
    def update_user_data(self, user_id: int, updates: Dict[str, Any]):
        user_data = self.get_user_data(user_id)
        user_data.update(updates)
        self.set_user_data(user_id, user_data)
    
    # -------------------- Subscription methods --------------------
    def get_subscription(self, user_id: int) -> Optional[Dict[str, Any]]:
        return self.data['subscriptions'].get(str(user_id))
    
    def set_subscription(self, user_id: int, subscription_data: Dict[str, Any]):
        self.data['subscriptions'][str(user_id)] = subscription_data
        self.save_json_file('subscriptions', self.data['subscriptions'])
    
    def remove_subscription(self, user_id: int):
        if str(user_id) in self.data['subscriptions']:
            del self.data['subscriptions'][str(user_id)]
            self.save_json_file('subscriptions', self.data['subscriptions'])
    
    def is_subscribed(self, user_id: int) -> bool:
        subscription = self.get_subscription(user_id)
        if not subscription:
            return False
        
        current_time = time.time()
        expires_at = subscription.get('expires_at', 0)
        
        if current_time >= expires_at:
            self.remove_subscription(user_id)
            return False
        
        return True
    
    # -------------------- Sticker packs methods --------------------
    def get_user_packs(self, user_id: int) -> list:
        return self.data['packs'].get(str(user_id), [])
    
    def add_user_pack(self, user_id: int, pack_info: Dict[str, Any]):
        user_packs = self.get_user_packs(user_id)
        for existing_pack in user_packs:
            if existing_pack.get('name') == pack_info.get('name'):
                return False
        
        user_packs.append({
            'name': pack_info.get('name'),
            'title': pack_info.get('title'),
            'created_at': time.time(),
            'sticker_count': pack_info.get('sticker_count', 0)
        })
        
        self.data['packs'][str(user_id)] = user_packs
        self.save_json_file('packs', self.data['packs'])
        return True
    
    def update_pack_sticker_count(self, user_id: int, pack_name: str):
        user_packs = self.get_user_packs(user_id)
        for pack in user_packs:
            if pack.get('name') == pack_name:
                pack['sticker_count'] = pack.get('sticker_count', 0) + 1
                break
        self.data['packs'][str(user_id)] = user_packs
        self.save_json_file('packs', self.data['packs'])
    
    # -------------------- Payment methods --------------------
    def add_pending_payment(self, payment_id: str, payment_data: Dict[str, Any]):
        self.data['payments'][payment_id] = payment_data
        self.save_json_file('payments', self.data['payments'])
    
    def get_pending_payments(self) -> Dict[str, Any]:
        return self.data['payments']
    
    def remove_pending_payment(self, payment_id: str):
        if payment_id in self.data['payments']:
            del self.data['payments'][payment_id]
            self.save_json_file('payments', self.data['payments'])
    
    # -------------------- Feedback methods --------------------
    def add_feedback(self, feedback_id: str, feedback_data: Dict[str, Any]):
        self.data['feedback'][feedback_id] = feedback_data
        self.save_json_file('feedback', self.data['feedback'])
    
    def get_feedback_stats(self) -> Dict[str, int]:
        positive = sum(1 for f in self.data['feedback'].values() if f.get('type') == 'positive')
        negative = sum(1 for f in self.data['feedback'].values() if f.get('type') == 'negative')
        return {'positive': positive, 'negative': negative, 'total': positive + negative}
    
    # -------------------- Settings methods --------------------
    def get_setting(self, key: str, default=None):
        return self.data['settings'].get(key, default)
    
    def set_setting(self, key: str, value: Any):
        self.data['settings'][key] = value
        self.save_json_file('settings', self.data['settings'])
    
    # -------------------- Stats methods --------------------
    def get_stats(self) -> Dict[str, Any]:
        total_users = len(self.data['users'])
        subscribed_users = len(self.data['subscriptions'])
        active_subscriptions = sum(1 for sub in self.data['subscriptions'].values() 
                                 if time.time() < sub.get('expires_at', 0))
        total_packs = sum(len(packs) for packs in self.data['packs'].values())
        pending_payments = len(self.data['payments'])
        feedback_stats = self.get_feedback_stats()
        
        return {
            'total_users': total_users,
            'subscribed_users': subscribed_users,
            'active_subscriptions': active_subscriptions,
            'total_packs': total_packs,
            'pending_payments': pending_payments,
            'feedback': feedback_stats
        }
    
    def backup_data(self, backup_dir: str):
        try:
            os.makedirs(backup_dir, exist_ok=True)
            timestamp = int(time.time())
            for key, filepath in self.files.items():
                if os.path.exists(filepath):
                    backup_filename = f"{key}_{timestamp}.json"
                    backup_path = os.path.join(backup_dir, backup_filename)
                    import shutil
                    shutil.copy2(filepath, backup_path)
                    logger.info(f"Backed up {key} to {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Error backing up data: {e}")
            return False
    
    def cleanup_old_backups(self, backup_dir: str, keep_days: int = 7):
        try:
            if not os.path.exists(backup_dir):
                return
            cutoff_time = time.time() - (keep_days * 24 * 3600)
            for filename in os.listdir(backup_dir):
                filepath = os.path.join(backup_dir, filename)
                if os.path.isfile(filepath) and filename.endswith('.json'):
                    if os.path.getmtime(filepath) < cutoff_time:
                        os.remove(filepath)
                        logger.info(f"Removed old backup: {filename}")
        except Exception as e:
            logger.error(f"Error cleaning up backups: {e}")
            
    def save_data(self, key: str, data: Dict[str, Any] = None):
        try:
            if key in self.data:
                if data is None:
                    data = self.data[key]
                else:
                    self.data[key] = data
                self.save_json_file(key, data)
                logger.info(f"Data saved for key: {key}")
                return True
            else:
                logger.error(f"Invalid key for save_data: {key}")
                return False
        except Exception as e:
            logger.error(f"Error in save_data for key {key}: {e}")
            return False
