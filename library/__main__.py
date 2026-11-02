import argparse
import json
import sys

from .db import DEFAULT_DB, ROOT, connect


def main():
    parser = argparse.ArgumentParser(description='DAAR book search toolkit (Python standard library only).')
    parser.add_argument('--db', default=str(DEFAULT_DB), help='Path to SQLite database')
    sub = parser.add_subparsers(dest='command', required=True)
    collect = sub.add_parser('collect', help='Download and validate books; safe to resume')
    collect.add_argument('--target', type=int, default=1700)
    collect.add_argument('--seed', action='store_true', help='Download 12 classic books for initial development')
    collect.add_argument('--delay', type=float, default=2.0)
    collect.add_argument('--data-dir', default=str(ROOT / 'data'))
    index = sub.add_parser('index', help='Build/update the inverted index')
    index.add_argument('--books-dir', default=str(ROOT / 'data' / 'books'))
    graph = sub.add_parser('graph', help='Build Jaccard graph and compute PageRank')
    graph.add_argument('--threshold', type=float, default=0.50, help='Similarity must exceed this value; distance must be less than 1 minus this value')
    sub.add_parser('validate', help='Verify corpus, postings and graph invariants')
    sub.add_parser('stats')
    server = sub.add_parser('serve', help='Start the application')
    server.add_argument('--host', default='127.0.0.1')
    server.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    try:
        if args.command == 'collect':
            from .collect import collect as run_collect
            count = run_collect(args.data_dir, args.target, args.seed, args.delay)
            required = min(args.target, 12) if args.seed else args.target
            return 0 if count >= required else 1
        if args.command == 'serve':
            from .server import serve
            serve(args.db, args.host, args.port)
            return 0
        db = connect(args.db)
        try:
            from .engine import build_graph, stats
            if args.command == 'index':
                from .collect import index_directory
                print(f'Imported {index_directory(db, args.books_dir)} new books.')
            elif args.command == 'graph':
                print(json.dumps(build_graph(db, args.threshold), indent=2))
            elif args.command == 'stats':
                print(json.dumps(stats(db), indent=2))
            elif args.command == 'validate':
                from .validation import validate
                result = validate(db)
                print(json.dumps(result, indent=2))
                return 0 if all(result['checks'].values()) else 1
        finally:
            db.close()
    except (ValueError, OSError) as error:
        print(f'Error: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
