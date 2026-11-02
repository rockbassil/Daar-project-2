"""Exact occurrence-weighted index-table distance from DAAR Lecture 3, p. 11.

The slide sums min/max counts over shared words. Distinctive words absent from
one document do not enter those sums. No shared words is assigned distance 1.
Bit planes compute the same integer sums without Python per-word pair loops.
"""
from dataclasses import dataclass


@dataclass
class CountVector:
    present: int
    planes: tuple
    words: int


def count_vector(rows, width):
    arrays = {}
    present = bytearray(width)
    words = 0
    for term_id, count in rows:
        if count <= 0:
            raise ValueError('Word counts must be positive.')
        position, mask = divmod(term_id, 8)
        mask = 1 << mask
        present[position] |= mask
        words += count
        while count:
            lowest = count & -count
            bit = lowest.bit_length() - 1
            if bit not in arrays:
                arrays[bit] = bytearray(width)
            arrays[bit][position] |= mask
            count ^= lowest
    planes = tuple(int.from_bytes(arrays[bit], 'little') if bit in arrays else 0
                   for bit in range(max(arrays, default=-1) + 1))
    return CountVector(int.from_bytes(present, 'little'), planes, words)


def read_vectors(db):
    # The book index does not cover counts. Cache the primary postings pages
    # during these reads to avoid repeatedly fetching them from disk.
    db.execute('PRAGMA cache_size=-524288')
    ids = [row[0] for row in db.execute('SELECT id FROM books ORDER BY id')]
    max_term = db.execute('SELECT COALESCE(MAX(id),0) FROM terms').fetchone()[0]
    width = (max_term + 8) // 8
    vectors = {book_id: count_vector(db.execute(
        'SELECT term_id,count FROM postings WHERE book_id=?', (book_id,)), width)
        for book_id in ids}
    return ids, vectors


def weighted_overlap(left, right):
    """Return sum(min), sum(max), and the shared-word mask, exactly."""
    shared = left.present & right.present
    if not shared:
        return 0, 0, 0
    depth = max(len(left.planes), len(right.planes))
    a = left.planes + (0,) * (depth - len(left.planes))
    b = right.planes + (0,) * (depth - len(right.planes))
    equal, less = shared, 0
    for bit in range(depth - 1, -1, -1):
        differing = equal & (a[bit] ^ b[bit])
        if differing:
            less |= differing & b[bit]
            equal ^= differing
    choose_left = less | equal
    choose_right = shared ^ choose_left
    minimum, maximum = 0, 0
    for bit in range(depth):
        minimum += ((a[bit] & choose_left) | (b[bit] & choose_right)).bit_count() << bit
        maximum += ((b[bit] & choose_left) | (a[bit] & choose_right)).bit_count() << bit
    return minimum, maximum, shared
