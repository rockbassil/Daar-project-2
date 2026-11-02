"""Inverted index, lecture-defined weighted graph, PageRank and search."""
import hashlib
import json
import time
from collections import Counter
from contextlib import nullcontext

from .regex import Regex
from .text import clean_text, frequencies, tokens
from .jaccard import read_vectors, weighted_overlap


def configure_bulk_import(db):
    """Bound the bulk-import page cache and reduce regenerable WAL fsyncs."""
    db.execute('PRAGMA cache_size=-524288')  # At most 512 MiB, allocated as needed.
    db.execute('PRAGMA synchronous=NORMAL')  # WAL remains corruption-safe.


def import_book(db, book, text, min_words=10000, term_ids=None, commit=True):
    """Insert one book and its postings atomically; reject duplicate contents."""
    if db.execute('SELECT 1 FROM books WHERE id=?', (book['id'],)).fetchone():
        return False
    content = clean_text(text)
    counts = frequencies(content)
    size = sum(counts.values())
    if size < min_words:
        raise ValueError(f"Book {book['id']} has only {size:,} words.")
    digest = hashlib.sha256(content.encode('utf-8')).hexdigest()
    if db.execute('SELECT 1 FROM books WHERE digest=?', (digest,)).fetchone():
        return False
    new_ids = {}
    with db if commit else nullcontext(db):
        db.execute('INSERT INTO books VALUES (?,?,?,?,?,?,?)',
                   (book['id'], book['title'], book.get('author', 'Unknown'),
                    book.get('source', ''), size, digest, ' '.join(content.split())[:650]))
        if term_ids is None:
            db.executemany('INSERT OR IGNORE INTO terms(word) VALUES (?)', ((w,) for w in counts))
            db.executemany('INSERT INTO postings SELECT id,?,? FROM terms WHERE word=?',
                           ((book['id'], n, w) for w, n in counts.items()))
        else:
            # Reuse the vocabulary map for a bulk import instead of repeating
            # dictionary B-tree lookups for every term in every book.
            missing = [w for w in counts if w not in term_ids]
            db.executemany('INSERT OR IGNORE INTO terms(word) VALUES (?)', ((w,) for w in missing))
            for offset in range(0, len(missing), 500):
                words = missing[offset:offset + 500]
                placeholders = ','.join('?' for _ in words)
                new_ids.update((word, term_id) for term_id, word in db.execute(
                    f'SELECT id,word FROM terms WHERE word IN ({placeholders})', words))
            postings = sorted((term_ids[w] if w in term_ids else new_ids[w], book['id'], n)
                              for w, n in counts.items())
            db.executemany('INSERT INTO postings VALUES (?,?,?)', postings)
        db.execute("DELETE FROM metadata WHERE key='graph'")
        db.execute('DELETE FROM scores')
        db.execute('DELETE FROM edges')
    if term_ids is not None:
        term_ids.update(new_ids)
    return True


def pagerank(nodes, edges, damping=0.85, tolerance=1e-10, max_iterations=200):
    """Unweighted undirected PageRank with uniform dangling-node redistribution."""
    nodes = list(nodes)
    if not nodes:
        return {}, 0
    adjacency = {node: [] for node in nodes}
    for a, b, *_ in edges:
        adjacency[a].append(b)
        adjacency[b].append(a)
    n = len(nodes)
    rank = dict.fromkeys(nodes, 1 / n)
    for iteration in range(1, max_iterations + 1):
        dangling = sum(rank[v] for v in nodes if not adjacency[v])
        base = (1 - damping) / n + damping * dangling / n
        updated = dict.fromkeys(nodes, base)
        for v in nodes:
            if adjacency[v]:
                share = damping * rank[v] / len(adjacency[v])
                for neighbor in adjacency[v]:
                    updated[neighbor] += share
        delta = sum(abs(updated[v] - rank[v]) for v in nodes)
        rank = updated
        if delta < tolerance:
            return rank, iteration
    raise ValueError(f'PageRank did not converge after {max_iterations} iterations.')


def book_vectors(db):
    """Return exact vocabulary bitsets and set sizes without changing the DB."""
    ids = [r[0] for r in db.execute('SELECT id FROM books ORDER BY id')]
    max_term = db.execute('SELECT COALESCE(MAX(id),0) FROM terms').fetchone()[0]
    vectors, sizes = {}, {}
    for book_id in ids:
        bits = bytearray((max_term + 8) // 8)
        size = 0
        for (term,) in db.execute('SELECT term_id FROM postings WHERE book_id=?', (book_id,)):
            bits[term // 8] |= 1 << (term % 8)
            size += 1
        vectors[book_id] = int.from_bytes(bits, 'little')
        sizes[book_id] = size
    return ids, vectors, sizes


def build_graph(db, threshold=0.50):
    """Lecture 3 count-weighted distance, strict distance < 1-threshold."""
    if not 0 <= threshold < 1:
        raise ValueError('Similarity threshold must be in [0, 1).')
    started = time.perf_counter()
    ids, vectors = read_vectors(db)
    edges = []
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            minimum, maximum, _ = weighted_overlap(vectors[a], vectors[b])
            similarity = minimum / maximum if maximum else 0
            if similarity > threshold:
                edges.append((a, b, similarity))
    ranks, iterations = pagerank(ids, edges)
    info = {'threshold': threshold, 'distance_threshold': 1 - threshold,
            'comparison': 'distance strictly less than distance_threshold',
            'metric': 'lecture3-weighted-shared', 'nodes': len(ids), 'edges': len(edges),
            'iterations': iterations, 'damping': 0.85, 'tolerance': 1e-10,
            'seconds': round(time.perf_counter() - started, 4),
            'representation': 'occurrence counts over shared normalized indexed words',
            'empty_intersection_distance': 1,
            'ranking': 'unweighted undirected PageRank'}
    with db:
        db.execute('DELETE FROM edges')
        db.execute('DELETE FROM scores')
        db.executemany('INSERT INTO edges VALUES (?,?,?)', edges)
        db.executemany('INSERT INTO scores VALUES (?,?)', ranks.items())
        db.execute('INSERT OR REPLACE INTO metadata VALUES (?,?)', ('graph', json.dumps(info)))
    return info


def stats(db):
    books = db.execute('SELECT COUNT(*), COALESCE(SUM(words),0), COALESCE(MIN(words),0) FROM books').fetchone()
    graph = db.execute("SELECT value FROM metadata WHERE key='graph'").fetchone()
    return {'books': books[0], 'words': books[1], 'min_words': books[2],
            'terms': db.execute('SELECT COUNT(*) FROM terms').fetchone()[0],
            'corpus_ready': books[0] >= 1664 and books[2] >= 10000,
            'graph': json.loads(graph[0]) if graph else None}


def recommend(db, ranked_ids, excluded, limit=6):
    candidates = {}
    # The three highest-ranked matches determine the recommendation neighborhood.
    for source in ranked_ids[:3]:
        for row in db.execute('SELECT b AS neighbor, similarity FROM edges WHERE a=? '
                              'UNION ALL SELECT a AS neighbor, similarity FROM edges WHERE b=?', (source, source)):
            neighbor, similarity = row
            if neighbor in excluded:
                continue
            if neighbor not in candidates or similarity > candidates[neighbor][0]:
                candidates[neighbor] = (similarity, source)
    output = []
    for book_id, (similarity, source) in sorted(candidates.items(), key=lambda x: (-x[1][0], x[0]))[:limit]:
        book = dict(db.execute('SELECT id,title,author,source,words FROM books WHERE id=?', (book_id,)).fetchone())
        book.update(similarity=round(similarity, 6), related_to=source)
        output.append(book)
    return output


def search(db, query, mode='keyword', ranking='pagerank', page=1, page_size=12):
    started = time.perf_counter()
    query = query.strip()
    if not query or len(query) > 128:
        raise ValueError('Enter a query between 1 and 128 characters.')
    if mode not in ('keyword', 'regex') or ranking not in ('pagerank', 'frequency'):
        raise ValueError('Invalid search mode or ranking.')
    if page < 1 or not 1 <= page_size <= 50:
        raise ValueError('Invalid page or page size.')
    matched = []
    if mode == 'keyword':
        words = tokens(query)
        if len(words) != 1:
            raise ValueError('Keyword search accepts one word. Use regex for alternatives such as sea|ocean.')
        matched = list(db.execute('SELECT id,word FROM terms WHERE word=?', (words[0],)))
    else:
        # Indexed vocabulary is case-folded, so expressions use the same convention.
        matcher = Regex(query.casefold())
        first = matcher.first_characters()
        parameters, predicates = [], []
        if first is not None and len(first) <= 8:
            for char in sorted(first):
                if ord(char) < 0x10ffff:
                    predicates.append('(word>=? AND word<?)')
                    parameters.extend([char, chr(ord(char) + 1)])
                else:
                    predicates.append('word>=?')
                    parameters.append(char)
            if matcher.fullmatch(''):
                predicates.append("word=''")
            # BINARY word ordering makes each interval an exact first-character
            # prefix. Every candidate still passes through the custom NFA.
            vocabulary_sql = 'SELECT id,word FROM terms WHERE ' + (' OR '.join(predicates) or '0')
        else:
            vocabulary_sql = 'SELECT id,word FROM terms'
        for row in db.execute(vocabulary_sql, parameters):
            if time.perf_counter() - started > 8:
                raise ValueError('This regex is too expensive. Try a shorter, more specific expression.')
            if matcher.fullmatch(row['word']):
                matched.append(row)
    counts = Counter()
    for offset in range(0, len(matched), 500):
        ids = [row['id'] for row in matched[offset:offset + 500]]
        placeholders = ','.join('?' for _ in ids)
        for book_id, count in db.execute(f'SELECT book_id,SUM(count) FROM postings WHERE term_id IN ({placeholders}) GROUP BY book_id', ids):
            counts[book_id] += count
    scores = dict(db.execute('SELECT book_id,score FROM scores'))
    if ranking == 'pagerank':
        ordered = sorted(counts, key=lambda b: (-scores.get(b, 0), -counts[b], b))
    else:
        ordered = sorted(counts, key=lambda b: (-counts[b], -scores.get(b, 0), b))
    selected = ordered[(page - 1) * page_size:page * page_size]
    results = []
    for book_id in selected:
        book = dict(db.execute('SELECT id,title,author,source,words,excerpt FROM books WHERE id=?', (book_id,)).fetchone())
        book.update(occurrences=counts[book_id], pagerank=scores.get(book_id, 0))
        results.append(book)
    return {'query': query, 'mode': mode, 'ranking': ranking, 'total': len(ordered),
            'page': page, 'page_size': page_size, 'results': results,
            'matched_terms': [r['word'] for r in matched[:30]], 'matched_term_count': len(matched),
            'recommendations': recommend(db, ordered, set(ordered)),
            'graph_ready': bool(scores),
            'elapsed_ms': round((time.perf_counter() - started) * 1000, 2)}
