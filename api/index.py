from http.server import BaseHTTPRequestHandler
import json

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        response = {
            'status': 'healthy',
            'bot': 'running',
            'message': 'Bot is active!'
        }
        self.wfile.write(json.dumps(response).encode())
    
    def do_POST(self):
        self.do_GET()