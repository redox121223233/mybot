import json
import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

class UserManager:
    def __init__(self, data_file: str = "user_data.json"):
        self.data_file = data_file
        self.users: Dict[int, Dict[str, Any]] = {}
        self.load_data()
    
    def load_data(self):
        """Load user data from file"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self.users = json.load(f)
                logger.info(f"Loaded {len(self.users)} users from database")
        except Exception as e:
            logger.error(f"Error loading user data: {e}")
            self.users = {}
    
    def save_data(self):
        """Save user data to file"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.users, f, ensure_ascii=False, indent=2, default=str)
            logger.info("User data saved successfully")
        except Exception as e:
            logger.error(f"Error saving user data: {e}")
    
    def get_user(self, user_id: int) -> Dict[str, Any]:
        """Get user data"""
        if user_id not in self.users:
            self.users[user_id] = {
                "id": user_id,
                "first_name": "",
                "last_name": "",
                "username": "",
                "language_code": "fa",
                "is_premium": False,
                "joined_at": datetime.now().isoformat(),
                "last_active": datetime.now().isoformat(),
                "message_count": 0,
                "commands_used": [],
                "settings": {
                    "notifications": True,
                    "language": "fa",
                    "theme": "light"
                },
                "usage_stats": {
                    "search_count": 0,
                    "music_count": 0,
                    "image_count": 0,
                    "sticker_count": 0,
                    "game_count": 0
                }
            }
        return self.users[user_id]
    
    def update_user(self, update: Update):
        """Update user information from Telegram update"""
        user = update.effective_user
        if not user:
            return
        
        user_data = self.get_user(user.id)
        
        # Update basic info
        user_data["first_name"] = user.first_name or ""
        user_data["last_name"] = user.last_name or ""
        user_data["username"] = user.username or ""
        user_data["language_code"] = user.language_code or "fa"
        user_data["is_premium"] = getattr(user, 'is_premium', False)
        user_data["last_active"] = datetime.now().isoformat()
        
        self.save_data()
    
    def increment_command_usage(self, user_id: int, command: str):
        """Increment command usage counter"""
        user_data = self.get_user(user_id)
        user_data["message_count"] += 1
        
        if command not in user_data["commands_used"]:
            user_data["commands_used"].append(command)
        
        # Update specific usage stats
        if command in ["search", "image"]:
            user_data["usage_stats"]["search_count"] += 1
        elif command in ["music", "download"]:
            user_data["usage_stats"]["music_count"] += 1
        elif command == "sticker":
            user_data["usage_stats"]["sticker_count"] += 1
        elif command in ["game", "quiz"]:
            user_data["usage_stats"]["game_count"] += 1
        
        self.save_data()
    
    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive user statistics"""
        user_data = self.get_user(user_id)
        
        # Calculate additional stats
        joined_date = datetime.fromisoformat(user_data["joined_at"])
        last_active = datetime.fromisoformat(user_data["last_active"])
        days_active = (datetime.now() - joined_date).days
        
        return {
            "basic_info": {
                "id": user_data["id"],
                "name": f"{user_data['first_name']} {user_data['last_name']}".strip(),
                "username": user_data["username"],
                "is_premium": user_data["is_premium"]
            },
            "activity": {
                "joined_at": user_data["joined_at"],
                "last_active": user_data["last_active"],
                "days_active": days_active,
                "message_count": user_data["message_count"]
            },
            "usage": user_data["usage_stats"],
            "commands_used": user_data["commands_used"],
            "settings": user_data["settings"]
        }
    
    def get_top_users(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top users by activity"""
        sorted_users = sorted(
            self.users.values(),
            key=lambda x: x["message_count"],
            reverse=True
        )
        
        return [
            {
                "id": user["id"],
                "name": f"{user['first_name']} {user['last_name']}".strip(),
                "username": user["username"],
                "message_count": user["message_count"],
                "commands_used": len(user["commands_used"])
            }
            for user in sorted_users[:limit]
        ]
    
    def get_bot_statistics(self) -> Dict[str, Any]:
        """Get overall bot statistics"""
        total_users = len(self.users)
        premium_users = sum(1 for user in self.users.values() if user["is_premium"])
        
        # Calculate activity stats
        active_today = sum(
            1 for user in self.users.values()
            if (datetime.now() - datetime.fromisoformat(user["last_active"])).days == 0
        )
        
        total_messages = sum(user["message_count"] for user in self.users.values())
        total_searches = sum(user["usage_stats"]["search_count"] for user in self.users.values())
        total_stickers = sum(user["usage_stats"]["sticker_count"] for user in self.users.values())
        
        return {
            "users": {
                "total": total_users,
                "premium": premium_users,
                "active_today": active_today
            },
            "usage": {
                "total_messages": total_messages,
                "total_searches": total_searches,
                "total_stickers_created": total_stickers
            },
            "performance": {
                "avg_messages_per_user": total_messages / total_users if total_users > 0 else 0,
                "most_active_users": self.get_top_users(5)
            }
        }
    
    def set_user_setting(self, user_id: int, setting: str, value: Any):
        """Set user setting"""
        user_data = self.get_user(user_id)
        user_data["settings"][setting] = value
        self.save_data()
    
    def search_users(self, query: str) -> List[Dict[str, Any]]:
        """Search users by name or username"""
        query = query.lower()
        results = []
        
        for user in self.users.values():
            if (query in user["first_name"].lower() or 
                query in user["last_name"].lower() or 
                query in user["username"].lower()):
                results.append({
                    "id": user["id"],
                    "name": f"{user['first_name']} {user['last_name']}".strip(),
                    "username": user["username"],
                    "message_count": user["message_count"]
                })
        
        return results[:10]  # Limit to 10 results

# Global user manager instance
user_manager = UserManager()