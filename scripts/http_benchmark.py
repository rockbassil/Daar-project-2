"""Measure real local HTTP latency, throughput, and rejected concurrent searches."""
import argparse
import csv
import json
import math
import platform
import statistics
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from library.db import DEFAULT_DB, connect
from library.engine import stats
from library.server import make_handler

QUERIES = [('keyword', 'sea'), ('keyword', 'love'), ('regex', 'sea|ocean'), ('regex', 'adventur.*')]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', type=Path, default=DEFAULT_DB)
    parser.add_argument('--clients', type=int, nargs='+', default=[1, 2, 4])
    parser.add_argument('--requests', type=int, default=24, help='Total requests per concurrency level')
    parser.add_argument('--output', type=Path, default=ROOT / 'reports' / 'final-results' / 'http')
    args = parser.parse_args()
    if args.requests < 1 or any(n < 1 for n in args.clients):
        parser.error('Client counts and request count must be positive.')
    db = connect(args.db)
    try:
        corpus = stats(db)
    finally:
        db.close()
    if not corpus['corpus_ready'] or not corpus['graph']:
        parser.error('Prepare and validate the full corpus first.')
    args.output.mkdir(parents=True, exist_ok=True)
    handler = make_handler(args.db)
    handler.log_message = lambda *a: None
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f'http://127.0.0.1:{server.server_port}'
    samples, rows = [], []

    def request(index):
        mode, query = QUERIES[index % len(QUERIES)]
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(base + '/api/search?' + urlencode({'q': query, 'mode': mode}), timeout=30) as response:
                data = json.load(response)
                status = response.status
        except urllib.error.HTTPError as error:
            status = error.code
            data = json.loads(error.read())
        except (OSError, TimeoutError) as error:
            status, data = 0, {'error': str(error)}
        return {'request': index + 1, 'mode': mode, 'query': query, 'status': status,
                'ms': (time.perf_counter() - started) * 1000,
                'results': data.get('total', ''), 'error': data.get('error', '')}

    try:
        for index in range(len(QUERIES)):
            warmup = request(index)
            if warmup['status'] != 200:
                raise RuntimeError(f'Warm-up failed: {warmup}')
        for clients in sorted(set(args.clients)):
            started = time.perf_counter()
            with ThreadPoolExecutor(max_workers=clients) as pool:
                current = list(pool.map(request, range(args.requests)))
            seconds = time.perf_counter() - started
            successful = sorted(s['ms'] for s in current if s['status'] == 200)
            row = {'clients': clients, 'requests': len(current), 'successes': len(successful),
                   'rejected_503': sum(s['status'] == 503 for s in current),
                   'other_errors': sum(s['status'] not in (200, 503) for s in current),
                   'seconds': seconds, 'completed_requests_per_second': len(current) / seconds,
                   'successful_requests_per_second': len(successful) / seconds,
                   'success_median_ms': statistics.median(successful) if successful else None,
                   'success_p95_ms': successful[math.ceil(.95 * len(successful)) - 1] if successful else None}
            rows.append(row)
            samples.extend(dict(clients=clients, **sample) for sample in current)
            print(json.dumps(row), flush=True)
            for name, data in [('summary.csv', rows), ('samples.csv', samples)]:
                with (args.output / name).open('w', encoding='utf-8', newline='') as stream:
                    writer = csv.DictWriter(stream, fieldnames=list(data[0]))
                    writer.writeheader()
                    writer.writerows(data)
        info = {'utc': datetime.now(timezone.utc).isoformat(), 'python': sys.version,
                'platform': platform.platform(), 'corpus': corpus, 'clients': args.clients,
                'requests_per_level': args.requests, 'queries': QUERIES,
                'scope': 'loopback HTTP including parsing, SQLite connection, search, and JSON serialization',
                'warmup': 'one request per query before measurements',
                'p95': 'nearest rank over successful requests only',
                'physical_devices': False, 'active_search_limit': 2}
        (args.output / 'environment.json').write_text(json.dumps(info, indent=2), encoding='utf-8')
        height = 100 + 65 * len(rows)
        parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="800" height="{height}" viewBox="0 0 800 {height}">',
                 f'<rect width="800" height="{height}" fill="#f8f6ef"/>',
                 '<text x="24" y="32" font-family="sans-serif" font-size="20">HTTP outcomes by concurrent client count</text>']
        for i, row in enumerate(rows):
            y = 65 + 65 * i
            success_width = 450 * row['successes'] / row['requests']
            parts.extend([f'<text x="24" y="{y+20}" font-family="sans-serif">{row["clients"]} clients</text>',
                          f'<rect x="125" y="{y}" width="{success_width}" height="30" fill="#47664c"/>',
                          f'<rect x="{125+success_width}" y="{y}" width="{450-success_width}" height="30" fill="#b45b44"/>',
                          f'<text x="590" y="{y+20}" font-family="sans-serif">{row["successes"]}/{row["requests"]} succeeded</text>'])
        parts.append('</svg>')
        (args.output / 'outcomes.svg').write_text('\n'.join(parts), encoding='utf-8')
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
    print(f'HTTP results saved to {args.output}', flush=True)


if __name__ == '__main__':
    main()
