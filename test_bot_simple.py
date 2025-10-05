#!/usr/bin/env python3
"""تست ساده ربات"""
import asyncio
import sys

# Simulate webhook update
update_data = {
    "update_id": 12345,
    "message": {
        "message_id": 1,
        "from": {
            "id": 6053579919,
            "is_bot": False,
            "first_name": "Test",
            "username": "testuser"
        },
        "chat": {
            "id": 6053579919,
            "first_name": "Test",
            "username": "testuser",
            "type": "private"
        },
        "date": 1633449600,
        "text": "/start"
    }
}

print("Testing bot import and processing...")
print(f"Update: {update_data.get('message', {}).get('text')}")

try:
    from bot import process_update
    print("✅ Bot imported successfully")

    print("Processing update...")
    asyncio.run(process_update(update_data))
    print("✅ Update processed")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
