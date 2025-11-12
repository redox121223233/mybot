#!/usr/bin/env python3
"""
Simple test script to verify the webhook endpoint
"""
import json
import asyncio
from fastapi.testclient import TestClient
from api.index import app

def test_webhook_endpoint():
    """Test the webhook endpoint with a sample update"""
    client = TestClient(app)
    
    # Test root endpoint
    response = client.get("/")
    print(f"Root endpoint status: {response.status_code}")
    print(f"Root endpoint response: {response.json()}")
    
    # Test webhook endpoint with sample update
    sample_update = {
        "update_id": 123456789,
        "message": {
            "message_id": 1,
            "from": {
                "id": 123456789,
                "is_bot": False,
                "first_name": "Test",
                "username": "test_user"
            },
            "chat": {
                "id": 123456789,
                "first_name": "Test",
                "username": "test_user",
                "type": "private"
            },
            "date": 1234567890,
            "text": "/start"
        }
    }
    
    response = client.post("/webhook", json=sample_update)
    print(f"Webhook endpoint status: {response.status_code}")
    print(f"Webhook endpoint response: {response.text}")

if __name__ == "__main__":
    test_webhook_endpoint()