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
from library.engine import build_graph, configure_bulk_import, import_book, search

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
    parser.add_argument('--threshold', type=float, default=.50)
    parser.add_argument('--output', type=Path, default=ROOT / 'reports' / 'results')
    parser.add_argument('--source-db', type=Path, help='Assemble logical subsets from an existing full index instead of reindexing text')
    parser.add_argument('--reuse-index-timings', type=Path, help='CSV of already measured unchanged index builds; requires --source-db')
    parser.add_argument('--reuse-full-graph-seconds', type=float, help='Actual recorded full-graph CLI duration; reuse matching full graph from --source-db')
    args = parser.parse_args()
    if args.repeats < 1 or any(size < 1 for size in args.sizes):
        parser.error('Sizes and repeats must be positive.')
    if bool(args.source_db) != bool(args.reuse_index_timings):
        parser.error('--source-db and --reuse-index-timings must be supplied together.')
    if args.reuse_full_graph_seconds is not None and (not args.source_db or args.reuse_full_graph_seconds <= 0):
        parser.error('Full graph timing reuse requires --source-db and a positive recorded duration.')
    prior_index = {}
    if args.reuse_index_timings:
        with args.reuse_index_timings.open(encoding='utf-8', newline='') as stream:
            prior_index = {int(row['books']): float(row['index_seconds']) for row in csv.DictReader(stream)}
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
                'graph_metric': 'lecture3-weighted-shared', 'graph_distance_threshold': 1 - args.threshold,
                'queries': QUERIES, 'warmup': 'one execution per query per corpus size',
                'scope': 'in-process engine latency, excludes HTTP/browser/network',
                'index_scope': 'file loading, cleaning, counting, postings writes, and commits',
                'graph_scope': 'complete graph/PageRank call including persistence',
                'bulk_sqlite': {'cache_mib': 512, 'synchronous': 'NORMAL', 'journal_mode': 'WAL', 'batch_books': 25},
                'subset_policy': 'ascending Gutenberg ID; nested subsets',
                'book_ids': [int(p.stem) for p in paths[:max(sizes)]]}
    if args.source_db:
        if not args.source_db.is_file() or any(size not in prior_index for size in sizes):
            parser.error('Source DB must exist and prior CSV must contain every requested actual size.')
        previous_environment = json.loads(args.reuse_index_timings.with_name('environment.json').read_text(encoding='utf-8'))
        if previous_environment['book_ids'][:max(sizes)] != metadata['book_ids']:
            parser.error('Prior index timings use different corpus IDs.')
        metadata.update(index_timing_source=str(args.reuse_index_timings),
                        subset_assembly='independent logical subset databases copied from the verified full index, retaining its term IDs',
                        index_scope='reused actual fresh-build timings from the prior unchanged indexing algorithm and corpus; subset copying timed separately')
        if args.reuse_full_graph_seconds is not None:
            metadata.update(full_graph_timing_source='data/preparation.log: weighted graph stage start to validate stage start',
                            full_graph_cli_seconds=args.reuse_full_graph_seconds,
                            full_graph_scope='prior actual matching full-corpus build, including interpreter start and persistence; copied graph used for fresh query measurements')

    def save_results():
        # Keep completed measurements if a later, larger experiment fails.
        metadata['completed_sizes'] = [row['books'] for row in rows]
        (args.output / 'environment.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
        for filename, data in [('scaling.csv', rows), ('query_samples.csv', samples)]:
            if not data:
                continue
            with (args.output / filename).open('w', encoding='utf-8', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=list(data[0]))
                writer.writeheader()
                writer.writerows(data)

    for size in sizes:
        with tempfile.TemporaryDirectory(prefix='daar-benchmark-') as directory:
            db_path = Path(directory) / 'benchmark.sqlite3'
            db = connect(db_path)
            configure_bulk_import(db)
            term_ids = {}
            start = time.perf_counter()
            assembly_s = 0
            reused_graph = None
            if args.source_db:
                print(f'Assembling independent {size}-book subset; reusing recorded index-build timing...', flush=True)
                db.execute('ATTACH DATABASE ? AS source', (str(args.source_db.resolve()),))
                db.execute('PRAGMA source.cache_size=-524288')
                db.execute('CREATE TEMP TABLE wanted_ids(id INTEGER PRIMARY KEY)')
                db.executemany('INSERT INTO wanted_ids VALUES (?)', ((int(path.stem),) for path in paths[:size]))
                db.execute('INSERT INTO books SELECT b.* FROM source.books b JOIN wanted_ids w ON b.id=w.id')
                db.execute('INSERT INTO terms SELECT t.* FROM source.terms t WHERE t.id IN '
                           '(SELECT p.term_id FROM source.postings p JOIN wanted_ids w ON p.book_id=w.id) ORDER BY t.id')
                db.execute('INSERT INTO postings SELECT p.* FROM source.postings p JOIN wanted_ids w ON p.book_id=w.id ORDER BY p.term_id,p.book_id')
                source_count = db.execute('SELECT COUNT(*) FROM source.books').fetchone()[0]
                if size == source_count and args.reuse_full_graph_seconds is not None:
                    source_graph = db.execute("SELECT value FROM source.metadata WHERE key='graph'").fetchone()
                    reused_graph = json.loads(source_graph[0]) if source_graph else None
                    if not reused_graph or reused_graph.get('metric') != 'lecture3-weighted-shared' or reused_graph['threshold'] != args.threshold:
                        raise ValueError('Recorded full graph does not match the requested metric/threshold.')
                    db.execute('INSERT INTO edges SELECT * FROM source.edges')
                    db.execute('INSERT INTO scores SELECT * FROM source.scores')
                    db.execute("INSERT INTO metadata SELECT * FROM source.metadata WHERE key='graph'")
                db.commit()
                db.execute('DETACH DATABASE source')
                assembly_s = time.perf_counter() - start
                index_s = prior_index[size]
            else:
                print(f'Building independent {size}-book benchmark index...', flush=True)
                for i, path in enumerate(paths[:size], 1):
                    book = json.loads(path.read_text(encoding='utf-8'))
                    import_book(db, book, path.with_suffix('.txt').read_text(encoding='utf-8'), term_ids=term_ids, commit=False)
                    if i % 25 == 0:
                        db.commit()
                    if i % 100 == 0:
                        print(f'  Indexed {i}/{size} books.', flush=True)
                db.commit()
                index_s = time.perf_counter() - start
            if db.execute('SELECT COUNT(*) FROM books').fetchone()[0] != size:
                raise ValueError('Subset contains duplicate IDs or contents; cannot label its timings with the requested book count.')
            if reused_graph:
                graph, graph_s = reused_graph, args.reuse_full_graph_seconds
            else:
                graph_started = time.perf_counter()
                graph = build_graph(db, args.threshold)
                graph_s = time.perf_counter() - graph_started
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
            row = {'books': size, 'index_seconds': index_s, 'graph_seconds': graph_s,
                   'edges': graph['edges'], 'database_mb': db_path.stat().st_size / 1024 ** 2,
                   'keyword_median_ms': statistics.median(durations['keyword']),
                   'regex_median_ms': statistics.median(durations['regex'])}
            if args.source_db:
                row['subset_assembly_seconds'] = assembly_s
            db.close()
            rows.append(row)
            save_results()
            print(json.dumps(row), flush=True)
    for field, title, unit in [('index_seconds', 'Index construction', 's'),
                               ('graph_seconds', 'Jaccard graph and PageRank', 's'),
                               ('keyword_median_ms', 'Keyword search — median latency', 'ms'),
                               ('regex_median_ms', 'Regex search — median latency', 'ms')]:
        chart(rows, field, title, unit, args.output / f'{field}.svg')
    print(f'Results saved to {args.output}', flush=True)


if __name__ == '__main__':
    main()
