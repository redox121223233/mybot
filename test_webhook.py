#!/usr/bin/env python3
"""
Simple Webhook Test for Telegram Bot
Run this to test if your webhook endpoint is working
"""

from flask import Flask, request, jsonify
import json

app = Flask(__name__)

@app.route('/api/webhook', methods=['POST'])
def webhook():
    """Test webhook endpoint"""
    try:
        if request.is_json:
            data = request.get_json()
            print("📨 Received webhook data:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            
            # Simple echo response for testing
            if "message" in data:
                message = data["message"]
                chat_id = message["chat"]["id"]
                text = message.get("text", "")
                
                if text == "/test":
                    # Send test response
                    return jsonify({
                        "method": "sendMessage",
                        "chat_id": chat_id,
                        "text": "✅ Webhook is working! Bot is responding."
                    })
            
            return jsonify({"status": "ok"})
        else:
            return jsonify({"error": "Invalid request"}), 400
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/webhook', methods=['GET'])
def webhook_info():
    """Webhook info endpoint"""
    return jsonify({
        "status": "running",
        "endpoint": "/api/webhook",
        "methods": ["POST", "GET"],
        "test_command": "/test"
    })

@app.route('/')
def home():
    return """
    <h1>🤖 Telegram Webhook Test</h1>
    <p>Status: Running ✅</p>
    <p>Endpoint: /api/webhook</p>
    <p>Send /test to your bot to test the webhook</p>
    """

if __name__ == "__main__":
    print("🚀 Starting webhook test server...")
    print("📡 Webhook URL: http://localhost:5000/api/webhook")
    print("🧪 Test with: /test command")
    app.run(host="0.0.0.0", port=5000, debug=True)