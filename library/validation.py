"""Read-only checks for corpus, index, graph, and centrality consistency."""
import math
from collections import Counter

from .engine import stats


def validate(db):
    db.execute('PRAGMA cache_size=-524288')
    summary = stats(db)
    # A book-by-book join through the secondary index repeatedly reads the
    # entire postings B-tree. Stream the primary table once and keep only
    # one integer total per book instead.
    totals = Counter()
    for book_id, count in db.execute('SELECT book_id,count FROM postings'):
        totals[book_id] += count
    mismatches = sum(totals[book_id] != words for book_id, words in db.execute('SELECT id,words FROM books'))
    scores = [r[0] for r in db.execute('SELECT score FROM scores')]
    graph = summary['graph']
    edge_count = db.execute('SELECT COUNT(*) FROM edges').fetchone()[0]
    missing_scores = db.execute(
        'SELECT COUNT(*) FROM books b LEFT JOIN scores s ON b.id=s.book_id WHERE s.book_id IS NULL'
    ).fetchone()[0]
    invalid_edges = db.execute(
        'SELECT COUNT(*) FROM edges WHERE a>=b OR similarity<=0 OR similarity>1'
    ).fetchone()[0]
    below_threshold = 0
    if graph:
        below_threshold = db.execute('SELECT COUNT(*) FROM edges WHERE similarity<=?', (graph['threshold'],)).fetchone()[0]
    checks = {
        'corpus_minimum': summary['corpus_ready'],
        'sqlite_integrity': db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok',
        'index_counts': mismatches == 0,
        'foreign_keys': not list(db.execute('PRAGMA foreign_key_check')),
        'graph_ready': graph is not None,
        'lecture_graph_definition': bool(graph) and graph.get('metric') == 'lecture3-weighted-shared',
        'graph_counts': bool(graph) and graph['nodes'] == summary['books'] and graph['edges'] == edge_count,
        'graph_edges': invalid_edges == 0 and below_threshold == 0,
        'pagerank_coverage': missing_scores == 0 and len(scores) == summary['books'],
        'pagerank_finite_positive': bool(scores) and all(math.isfinite(s) and s > 0 for s in scores),
        'pagerank_normalized': abs(sum(scores) - 1) < 1e-8,
    }
    return {'stats': summary, 'checks': checks}
