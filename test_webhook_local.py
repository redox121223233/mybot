#!/usr/bin/env python3
"""Test webhook locally before deploying"""
import json
import sys
from api.webhook import handler
from io import BytesIO

class MockRequest:
    def __init__(self, body):
        self.body = body.encode('utf-8')
        self.headers = {'Content-Length': str(len(self.body))}

    def read(self, size):
        return self.body

    def get(self, key, default=None):
        return self.headers.get(key, default)

class MockHandler(handler):
    def __init__(self, body):
        self.headers = MockRequest(body).headers
        self.rfile = BytesIO(body.encode('utf-8'))
        self.response_code = None
        self.response_headers = {}
        self.response_body = b''

    def send_response(self, code):
        self.response_code = code

    def send_header(self, key, value):
        self.response_headers[key] = value

    def end_headers(self):
        pass

    class wfile:
        @staticmethod
        def write(data):
            print(f"Response: {data.decode('utf-8')}")

def test_callback_query():
    """Test callback query handling"""

    # Create a callback query update
    update = {
        "update_id": 99999,
        "callback_query": {
            "id": "test123",
            "from": {
                "id": 6053579919,
                "is_bot": False,
                "first_name": "Test",
                "username": "testuser"
            },
            "message": {
                "message_id": 1,
                "chat": {
                    "id": 6053579919,
                    "type": "private"
                },
                "date": 1633449600,
                "text": "Test"
            },
            "chat_instance": "123",
            "data": "menu:help"
        }
    }

    print("=" * 60)
    print("Testing callback query: menu:help")
    print("=" * 60)

    body = json.dumps(update)
    h = MockHandler(body)

    try:
        h.do_POST()
        print(f"\n✅ Test completed - Response code: {h.response_code}")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_callback_query()
