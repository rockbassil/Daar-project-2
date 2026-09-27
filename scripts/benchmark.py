"""Reproducible scaling experiment; outputs measured CSV/JSON and SVG charts."""
import argparse
import csv
import json
import platform
import statistics
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from library.db import connect
from library.engine import build_graph, import_book, search

QUERIES = [('keyword', 'sea'), ('keyword', 'love'), ('keyword', 'science'),
           ('regex', 'sea|ocean'), ('regex', 'adventur.*'), ('regex', 'lov(e|ing)')]


def chart(rows, field, title, unit, path):
    width, height = 760, 110 + 50 * len(rows)
    max_value = max((r[field] for r in rows), default=1) or 1
    shapes = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
              '<rect width="100%" height="100%" fill="#f8f6ef"/>',
              f'<text x="25" y="35" font-family="sans-serif" font-size="20" fill="#243b32">{title}</text>']
    for i, row in enumerate(rows):
        y = 67 + i * 50
        length = 470 * row[field] / max_value
        shapes += [f'<text x="25" y="{y + 20}" font-family="sans-serif" font-size="13">{row["books"]} books</text>',
                   f'<rect x="125" y="{y}" width="{length:.2f}" height="29" rx="3" fill="#47664c"/>',
                   f'<text x="{135 + length:.2f}" y="{y + 20}" font-family="sans-serif" font-size="12">{row[field]:.2f} {unit}</text>']
    shapes.append('</svg>')
    path.write_text('\n'.join(shapes), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sizes', type=int, nargs='+', default=[100, 500, 1000, 1700])
    parser.add_argument('--repeats', type=int, default=5)
    parser.add_argument('--threshold', type=float, default=.30)
    parser.add_argument('--output', type=Path, default=ROOT / 'reports' / 'results')
    args = parser.parse_args()
    if args.repeats < 1 or any(size < 1 for size in args.sizes):
        parser.error('Sizes and repeats must be positive.')
    paths = sorted((ROOT / 'data' / 'books').glob('*.json'), key=lambda p: int(p.stem))
    if not paths:
        parser.error('No corpus found. Run python -m library collect first.')
    args.output.mkdir(parents=True, exist_ok=True)
    rows, samples = [], []
    sizes = sorted(set(min(size, len(paths)) for size in args.sizes))
    metadata = {'utc': datetime.now(timezone.utc).isoformat(), 'python': sys.version,
                'platform': platform.platform(), 'processor': platform.processor(),
                'available_books': len(paths), 'requested_sizes': args.sizes,
                'actual_sizes': sizes, 'repeats': args.repeats, 'threshold': args.threshold,
                'queries': QUERIES, 'warmup': 'one execution per query per corpus size',
                'scope': 'in-process engine latency, excludes HTTP/browser/network',
                'subset_policy': 'ascending Gutenberg ID; nested subsets',
                'book_ids': [int(p.stem) for p in paths[:max(sizes)]]}
    for size in sizes:
        with tempfile.TemporaryDirectory(prefix='daar-benchmark-') as directory:
            db_path = Path(directory) / 'benchmark.sqlite3'
            db = connect(db_path)
            start = time.perf_counter()
            for path in paths[:size]:
                book = json.loads(path.read_text(encoding='utf-8'))
                import_book(db, book, path.with_suffix('.txt').read_text(encoding='utf-8'))
            index_s = time.perf_counter() - start
            graph = build_graph(db, args.threshold)
            durations = {'keyword': [], 'regex': []}
            for mode, query in QUERIES:
                search(db, query, mode)
                for iteration in range(args.repeats):
                    start = time.perf_counter()
                    result = search(db, query, mode)
                    elapsed = (time.perf_counter() - start) * 1000
                    durations[mode].append(elapsed)
                    samples.append({'books': size, 'mode': mode, 'query': query,
                                    'iteration': iteration + 1, 'ms': elapsed, 'results': result['total']})
            db.execute('PRAGMA wal_checkpoint(TRUNCATE)')
            row = {'books': size, 'index_seconds': index_s, 'graph_seconds': graph['seconds'],
                   'edges': graph['edges'], 'database_mb': db_path.stat().st_size / 1024 ** 2,
                   'keyword_median_ms': statistics.median(durations['keyword']),
                   'regex_median_ms': statistics.median(durations['regex'])}
            db.close()
            rows.append(row)
            print(json.dumps(row), flush=True)
    for filename, data in [('scaling.csv', rows), ('query_samples.csv', samples)]:
        with (args.output / filename).open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(data[0]))
            writer.writeheader()
            writer.writerows(data)
    (args.output / 'environment.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    for field, title, unit in [('index_seconds', 'Index construction', 's'),
                               ('graph_seconds', 'Jaccard graph and PageRank', 's'),
                               ('keyword_median_ms', 'Keyword search — median latency', 'ms'),
                               ('regex_median_ms', 'Regex search — median latency', 'ms')]:
        chart(rows, field, title, unit, args.output / f'{field}.svg')
    print(f'Results saved to {args.output}', flush=True)


if __name__ == '__main__':
    main()
