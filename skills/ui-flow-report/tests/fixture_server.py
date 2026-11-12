"""Local synthetic app/backend for manual or Playwright capture verification."""
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import argparse


class Handler(BaseHTTPRequestHandler):
    profile = {'name': 'Test Member', 'external_count': 0}

    def do_GET(self):
        if self.path == '/profile':
            data, mime = json.dumps(self.profile).encode(), 'application/json'
        else:
            data, mime = Path(__file__).with_name('fixture.html').read_bytes(), 'text/html'
        self.send_response(200)
        self.send_header('Content-Type', mime)
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        if self.path == '/profile':
            self.profile['name'] = body['name']
        elif self.path == '/external':
            self.profile['external_count'] += 1
        self.do_GET()

    def log_message(self, *args):
        pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8768)
    args = parser.parse_args()
    HTTPServer(('127.0.0.1', args.port), Handler).serve_forever()
