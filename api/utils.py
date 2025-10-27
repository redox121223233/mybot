"""
Shared utilities for serverless Telegram Bot
"""
import logging
import os
from typing import Dict, Any, Optional
from config import SERVERLESS_CONFIG

logger = logging.getLogger(__name__)

class ServerlessCache:
    """Simple in-memory cache for serverless functions"""
    _cache = {}
    
    @classmethod
    def get(cls, key: str) -> Optional[Any]:
        """Get value from cache"""
        return cls._cache.get(key)
    
    @classmethod
    def set(cls, key: str, value: Any) -> None:
        """Set value in cache"""
        cls._cache[key] = value
    
    @classmethod
    def delete(cls, key: str) -> None:
        """Delete value from cache"""
        cls._cache.pop(key, None)
    
    @classmethod
    def clear(cls) -> None:
        """Clear all cache"""
        cls._cache.clear()

class UserStateManager:
    """Manager for user states in serverless environment"""
    _states = {}
    
    @classmethod
    def get_state(cls, user_id: int) -> Dict[str, Any]:
        """Get user state"""
        return cls._states.get(user_id, {})
    
    @classmethod
    def set_state(cls, user_id: int, state: Dict[str, Any]) -> None:
        """Set user state"""
        cls._states[user_id] = state
    
    @classmethod
    def update_state(cls, user_id: int, updates: Dict[str, Any]) -> None:
        """Update user state"""
        if user_id not in cls._states:
            cls._states[user_id] = {}
        cls._states[user_id].update(updates)
    
    @classmethod
    def delete_state(cls, user_id: int) -> None:
        """Delete user state"""
        cls._states.pop(user_id, None)

def setup_serverless_logging():
    """Setup logging for serverless environment"""
    if not SERVERLESS_CONFIG['ENABLE_LOGGING']:
        return
    
    log_level = getattr(logging, SERVERLESS_CONFIG['LOG_LEVEL'].upper())
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def validate_webhook_secret(headers: Dict[str, str]) -> bool:
    """Validate webhook secret for security"""
    secret = os.getenv('TELEGRAM_WEBHOOK_SECRET')
    if not secret:
        return True  # Skip validation if no secret is set
    
    webhook_secret = headers.get('X-Telegram-Bot-Api-Secret-Token')
    return webhook_secret == secret

def get_error_response(error: Exception, context: str = "") -> Dict[str, Any]:
    """Get standardized error response"""
    error_message = f"Error in {context}: {str(error)}" if context else str(error)
    logger.error(error_message)
    
    return {
        'status': 'error',
        'message': error_message,
        'error_type': type(error).__name__
    }

def is_valid_telegram_update(update_data: Dict[str, Any]) -> bool:
    """Validate if the update data is a valid Telegram update"""
    required_fields = ['update_id']
    return all(field in update_data for field in required_fields)

# Initialize logging
setup_serverless_logging()