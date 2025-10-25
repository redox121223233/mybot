import os
import hashlib
import time
import logging
from typing import Dict, Set, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class SecurityManager:
    def __init__(self):
        self.admin_id = int(os.getenv('ADMIN_ID', '0'))
        self.allowed_users: Set[int] = set()
        self.rate_limits: Dict[int, Dict[str, int]] = {}
        self.blocked_users: Set[int] = set()
        self.api_keys: Dict[str, str] = {}
        
    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin"""
        return user_id == self.admin_id
    
    def is_user_allowed(self, user_id: int) -> bool:
        """Check if user is allowed to use the bot"""
        if user_id in self.blocked_users:
            return False
        
        # If no users are explicitly allowed, allow everyone
        if not self.allowed_users:
            return True
            
        return user_id in self.allowed_users or self.is_admin(user_id)
    
    def add_allowed_user(self, user_id: int) -> bool:
        """Add user to allowed list"""
        if self.is_admin(user_id):
            self.allowed_users.add(user_id)
            return True
        return False
    
    def block_user(self, user_id: int, duration_hours: int = 24) -> bool:
        """Block user for specified duration"""
        if not self.is_user_allowed(user_id):
            return False
        
        self.blocked_users.add(user_id)
        logger.info(f"User {user_id} blocked for {duration_hours} hours")
        
        # Schedule unblock (in real implementation, you'd use a proper scheduler)
        return True
    
    def check_rate_limit(self, user_id: int, max_requests: int = 10, time_window: int = 60) -> bool:
        """Check if user exceeded rate limit"""
        current_time = int(time.time())
        
        if user_id not in self.rate_limits:
            self.rate_limits[user_id] = {"count": 1, "window_start": current_time}
            return True
        
        user_data = self.rate_limits[user_id]
        
        # Reset window if expired
        if current_time - user_data["window_start"] > time_window:
            user_data["count"] = 1
            user_data["window_start"] = current_time
            return True
        
        # Increment count
        user_data["count"] += 1
        
        # Check if exceeded
        if user_data["count"] > max_requests:
            logger.warning(f"User {user_id} exceeded rate limit")
            return False
        
        return True
    
    def generate_api_key(self, user_id: int) -> Optional[str]:
        """Generate API key for user"""
        if not self.is_user_allowed(user_id):
            return None
        
        key_data = f"{user_id}_{int(time.time())}_{os.urandom(8).hex()}"
        api_key = hashlib.sha256(key_data.encode()).hexdigest()
        
        self.api_keys[api_key] = {
            "user_id": user_id,
            "created_at": datetime.now(),
            "last_used": None,
            "usage_count": 0
        }
        
        logger.info(f"Generated API key for user {user_id}")
        return api_key
    
    def validate_api_key(self, api_key: str) -> Optional[int]:
        """Validate API key and return user ID"""
        if api_key not in self.api_keys:
            return None
        
        key_data = self.api_keys[api_key]
        key_data["last_used"] = datetime.now()
        key_data["usage_count"] += 1
        
        return key_data["user_id"]
    
    def log_security_event(self, event_type: str, user_id: int, details: str = ""):
        """Log security events"""
        logger.info(f"SECURITY: {event_type} | User: {user_id} | Details: {details}")
    
    def get_user_stats(self, user_id: int) -> Dict:
        """Get user statistics"""
        stats = {
            "user_id": user_id,
            "is_admin": self.is_admin(user_id),
            "is_allowed": self.is_user_allowed(user_id),
            "is_blocked": user_id in self.blocked_users,
            "rate_limit_data": self.rate_limits.get(user_id, {}),
        }
        
        # Find API keys for this user
        user_api_keys = {k: v for k, v in self.api_keys.items() if v["user_id"] == user_id}
        stats["api_keys_count"] = len(user_api_keys)
        
        return stats

# Global security manager instance
security_manager = SecurityManager()