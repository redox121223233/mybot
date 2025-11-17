#!/usr/bin/env python3
"""
Simple bot restart script
"""
import subprocess
import sys
import os

def main():
    print("🔄 Restarting your Telegram bot with the InputSticker fix...")
    
    # Change to the api directory
    os.chdir('api')
    
    # Set the bot token environment variable (you'll need to set this)
    print("⚠️  Make sure BOT_TOKEN environment variable is set!")
    print("💡 You can set it with: export BOT_TOKEN='your_bot_token_here'")
    
    try:
        # Start the bot
        print("🚀 Starting bot...")
        subprocess.run([sys.executable, 'index.py'], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error starting bot: {e}")
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()