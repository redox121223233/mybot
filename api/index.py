from http.server import BaseHTTPRequestHandler
import json

class handler(BaseHTTPRequestHandler):
    """
    A minimal, synchronous handler to isolate the Vercel invocation issue.
    This handler has no external dependencies or complex logic.
    Its only purpose is to print a log and return a 200 response.
    """
    def do_GET(self):
        print("--- MINIMAL GET HANDLER REACHED ---")
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ok", "message": "GET received"}).encode("utf-8"))

    def do_POST(self):
        print("--- MINIMAL POST HANDLER REACHED ---")
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ok", "message": "POST received"}).encode("utf-8"))
