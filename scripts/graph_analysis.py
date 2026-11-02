"""Compare graph thresholds and export worked computations on actual books."""
import argparse
import csv
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from library.db import DEFAULT_DB, connect
from library.engine import stats
from library.jaccard import count_vector, read_vectors, weighted_overlap


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', type=Path, default=DEFAULT_DB)
    parser.add_argument('--thresholds', type=float, nargs='+', default=[.50, .55, .60, .65])
    parser.add_argument('--output', type=Path, default=ROOT / 'reports' / 'final-results' / 'graph')
    args = parser.parse_args()
    if any(not 0 <= threshold < 1 for threshold in args.thresholds):
        parser.error('Similarity thresholds must be in [0,1).')
    args.output.mkdir(parents=True, exist_ok=True)
    db = connect(args.db)
    try:
        corpus = stats(db)
        if not corpus['corpus_ready'] or not corpus['graph']:
            parser.error('Prepare the full corpus and graph first.')
        started = time.perf_counter()
        ids = [r[0] for r in db.execute('SELECT id FROM books ORDER BY id')]
        levels = {threshold: {'edges': 0, 'degrees': dict.fromkeys(ids, 0),
                              'parent': {node: node for node in ids}, 'size': dict.fromkeys(ids, 1)}
                  for threshold in sorted(set(args.thresholds))}

        def find(parent, node):
            while parent[node] != node:
                parent[node] = parent[parent[node]]
                node = parent[node]
            return node

        reuse_edges = min(levels) >= corpus['graph']['threshold']
        if reuse_edges:
            pairs_to_check = db.execute('SELECT a,b,similarity FROM edges')
        else:
            ids, all_vectors = read_vectors(db)
            def all_pairs():
                for i, a in enumerate(ids):
                    for b in ids[i + 1:]:
                        minimum, maximum, _ = weighted_overlap(all_vectors[a], all_vectors[b])
                        yield a, b, minimum / maximum if maximum else 0
            pairs_to_check = all_pairs()
        for a, b, similarity in pairs_to_check:
            for threshold, level in levels.items():
                if similarity <= threshold:
                    break
                level['edges'] += 1
                level['degrees'][a] += 1
                level['degrees'][b] += 1
                parent = level['parent']
                left, right = find(parent, a), find(parent, b)
                if left != right:
                    if level['size'][left] < level['size'][right]:
                        left, right = right, left
                    parent[right] = left
                    level['size'][left] += level['size'][right]
        rows = []
        n = len(ids)
        for threshold, level in levels.items():
            components = {find(level['parent'], node) for node in ids}
            row = {'threshold': threshold, 'books': n, 'edges': level['edges'],
                   'density': 2 * level['edges'] / (n * (n - 1)),
                   'mean_degree': 2 * level['edges'] / n,
                   'isolated_books': sum(degree == 0 for degree in level['degrees'].values()),
                   'components': len(components),
                   'largest_component': max(level['size'][root] for root in components)}
            rows.append(row)
            print(json.dumps(row), flush=True)
        with (args.output / 'thresholds.csv').open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

        books = {r['id']: dict(r) for r in db.execute('SELECT id,title,words FROM books')}
        selected = [node for node in [11, 84, 1342, 1661, 2701] if node in books]
        db.execute('PRAGMA cache_size=-524288')
        max_term = db.execute('SELECT COALESCE(MAX(id),0) FROM terms').fetchone()[0]
        vectors = {node: count_vector(db.execute('SELECT term_id,count FROM postings WHERE book_id=?', (node,)), (max_term + 8) // 8)
                   for node in selected}
        pairs = []
        for i, a in enumerate(selected):
            for b in selected[i + 1:]:
                minimum, maximum, shared = weighted_overlap(vectors[a], vectors[b])
                similarity = minimum / maximum if maximum else 0
                pairs.append({'a': books[a], 'b': books[b],
                              'unique_words_a': vectors[a].present.bit_count(),
                              'unique_words_b': vectors[b].present.bit_count(),
                              'shared_words': shared.bit_count(),
                              'minimum_count_sum_shared': minimum, 'maximum_count_sum_shared': maximum,
                              'similarity': similarity, 'distance': 1 - similarity,
                              'edge_in_final_graph': similarity > corpus['graph']['threshold']})
        adjacency = {node: [] for node in ids}
        for a, b in db.execute('SELECT a,b FROM edges'):
            adjacency[a].append(b)
            adjacency[b].append(a)
        ranks = dict(db.execute('SELECT book_id,score FROM scores'))
        dangling = sum(ranks[node] for node in ids if not adjacency[node])
        damping = corpus['graph']['damping']
        examples = []
        for node in selected:
            contributions = [{'id': neighbor, 'title': books[neighbor]['title'],
                              'pagerank': ranks[neighbor], 'degree': len(adjacency[neighbor]),
                              'contribution': damping * ranks[neighbor] / len(adjacency[neighbor])}
                             for neighbor in adjacency[node]]
            teleport = (1 - damping) / n
            dangling_share = damping * dangling / n
            recomputed = teleport + dangling_share + sum(c['contribution'] for c in contributions)
            examples.append({'book': books[node], 'degree': len(adjacency[node]),
                             'pagerank': ranks[node], 'teleportation': teleport,
                             'dangling_share': dangling_share,
                             'neighbor_contribution_total': sum(c['contribution'] for c in contributions),
                             'recomputed_next_iteration': recomputed,
                             'absolute_residual': abs(recomputed - ranks[node]),
                             'largest_contributions': sorted(contributions, key=lambda c: -c['contribution'])[:5]})
        result = {'corpus': corpus, 'thresholds': rows, 'jaccard_examples': pairs,
                  'pagerank_examples': examples, 'analysis_seconds': time.perf_counter() - started,
                  'note': 'Connectivity alone does not establish semantic relevance; collect real user judgments.'}
        result['threshold_method'] = 'exact filtering of the stored complete edge set for stricter cutoffs' if reuse_edges else 'exact all-pairs recomputation'
        (args.output / 'analysis.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    finally:
        db.close()


if __name__ == '__main__':
    main()
