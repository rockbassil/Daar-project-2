import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from library.db import connect
from library.engine import build_graph, import_book
from library.server import make_handler


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        path = Path(cls.temp.name) / 'http.sqlite3'
        db = connect(path)
        import_book(db, {'id': 1, 'title': '<script>title</script>'}, 'ocean ocean sea', min_words=1)
        build_graph(db)
        db.close()
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), make_handler(path))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.temp.cleanup()

    def get(self, path):
        return urllib.request.urlopen(self.base + path, timeout=10)

    def test_static_interface_and_headers(self):
        with self.get('/') as response:
            self.assertIn(b'Margin', response.read())
            self.assertIn("default-src 'self'", response.headers['Content-Security-Policy'])

    def test_search_and_stats(self):
        with self.get('/api/stats') as response:
            self.assertEqual(json.load(response)['books'], 1)
        with self.get('/api/search?q=ocean') as response:
            self.assertEqual(json.load(response)['results'][0]['occurrences'], 2)

    def test_error_statuses_and_path_isolation(self):
        for path, code in [('/api/search?q=%28&mode=regex', 400), ('/api/search?q=ocean&page=no', 400),
                           ('/data/library.sqlite3', 404), ('/../library/engine.py', 404), ('/api/missing', 404)]:
            with self.subTest(path=path), self.assertRaises(urllib.error.HTTPError) as caught:
                self.get(path)
            self.assertEqual(caught.exception.code, code)


if __name__ == '__main__':
    unittest.main()
