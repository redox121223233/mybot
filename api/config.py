"""
Serverless configuration for Telegram Bot
"""
import os

# Serverless configuration
SERVERLESS_CONFIG = {
    'MAX_WEBHOOK_TIMEOUT': int(os.getenv('MAX_WEBHOOK_TIMEOUT', '10')),
    'ENABLE_LOGGING': os.getenv('ENABLE_LOGGING', 'true').lower() == 'true',
    'LOG_LEVEL': os.getenv('LOG_LEVEL', 'INFO'),
    'CACHE_DURATION': int(os.getenv('CACHE_DURATION', '300')),  # 5 minutes
    'MAX_RETRIES': int(os.getenv('MAX_RETRIES', '3')),
}

# Telegram configuration
TELEGRAM_CONFIG = {
    'TOKEN': os.getenv('TELEGRAM_BOT_TOKEN'),
    'WEBHOOK_SECRET': os.getenv('TELEGRAM_WEBHOOK_SECRET', ''),
    'PARSE_MODE': 'HTML',
    'DISABLE_NOTIFICATION': False,
}