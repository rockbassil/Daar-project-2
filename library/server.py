"""Small read-only HTTP API and static UI for a trusted LAN demonstration."""
import json
import mimetypes
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from .db import ROOT, connect
from .engine import search, stats


def make_handler(db_path):
    static = ROOT / 'web'
    search_slots = threading.BoundedSemaphore(2)

    class Handler(BaseHTTPRequestHandler):
        def send(self, status, content, content_type='application/json; charset=utf-8'):
            body = json.dumps(content, ensure_ascii=False).encode('utf-8') if isinstance(content, dict) else content
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Content-Security-Policy', "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            parsed = urlsplit(self.path)
            if parsed.path.startswith('/api/'):
                db = None
                acquired = False
                try:
                    if parsed.path == '/api/search':
                        acquired = search_slots.acquire(blocking=False)
                        if not acquired:
                            return self.send(503, {'error': 'Search is busy. Please try again shortly.'})
                    db = connect(db_path)
                    if parsed.path == '/api/stats':
                        return self.send(200, stats(db))
                    if parsed.path == '/api/search':
                        params = parse_qs(parsed.query)
                        result = search(db, params.get('q', [''])[0],
                                        params.get('mode', ['keyword'])[0],
                                        params.get('ranking', ['pagerank'])[0],
                                        int(params.get('page', ['1'])[0]))
                        return self.send(200, result)
                    return self.send(404, {'error': 'API endpoint not found.'})
                except ValueError as error:
                    return self.send(400, {'error': str(error)})
                except sqlite3.Error:
                    return self.send(503, {'error': 'The library is temporarily unavailable. Please retry.'})
                finally:
                    if db is not None:
                        db.close()
                    if acquired:
                        search_slots.release()
            files = {'/': 'index.html', '/style.css': 'style.css', '/app.js': 'app.js', '/favicon.svg': 'favicon.svg'}
            if parsed.path not in files:
                return self.send(404, {'error': 'Page not found.'})
            path = static / files[parsed.path]
            mime = mimetypes.guess_type(path.name)[0] or 'application/octet-stream'
            self.send(200, path.read_bytes(), mime + '; charset=utf-8')

    return Handler


def serve(db_path, host='127.0.0.1', port=8000):
    with ThreadingHTTPServer((host, port), make_handler(db_path)) as server:
        print(f'Book search is running at http://{host}:{port}', flush=True)
        print('Press Ctrl+C to stop.', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
