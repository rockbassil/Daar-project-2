import itertools
import hashlib
import json
import re
import random
import tempfile
import unittest
from pathlib import Path

from library.db import connect
from library.engine import build_graph, import_book, pagerank, search, stats
from library.regex import Regex
from library.text import clean_text, tokens
from library.collect import collect, index_directory
from library.validation import validate
from library.jaccard import count_vector, weighted_overlap


class RegexTests(unittest.TestCase):
    def test_supported_grammar_against_independent_reference(self):
        patterns = ['a', '', 'a|b', '(a|b)*', 'ab+c?', 'a.*b', '[a-c]+', '[^b]*',
                    '(ab|ba)?', 'a(b|)c', '(a*)*', r'a\?', '[-ab]+', '[a-c]?b*']
        words = [''.join(s) for n in range(5) for s in itertools.product('abc', repeat=n)] + ['a?']
        for pattern in patterns:
            if not pattern:
                continue
            matcher = Regex(pattern)
            for word in words:
                with self.subTest(pattern=pattern, word=word):
                    self.assertEqual(matcher.fullmatch(word), re.fullmatch(pattern, word) is not None)

    def test_reject_invalid_or_unsupported_patterns(self):
        for pattern in ['', '(', ')', '[abc', '[]', '[z-a]', '*a', 'a**', '\\', r'\d', '^a$', 'a{2}']:
            with self.subTest(pattern=pattern), self.assertRaises(ValueError):
                Regex(pattern)

    def test_nested_quantifier_does_not_backtrack(self):
        self.assertFalse(Regex('(a+)+b').fullmatch('a' * 10000))


class TextTests(unittest.TestCase):
    def test_line_endings_have_identical_cleaned_content(self):
        text = 'sea ocean\n\nwhale adventure\n'
        expected = clean_text(text)
        for separator in ['\r\n', '\r\r\n', '\r']:
            self.assertEqual(clean_text(text.replace('\n', separator)), expected)

    def test_legacy_corpus_hash_migration_and_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            books = root / 'books'
            books.mkdir()
            (root / 'pg_catalog.csv').write_text('Text#,Title,Authors,Language,Type\n1,Test,Author,en,Text\n', encoding='utf-8')
            original = ('ocean sea\r\n' * 5000).strip()
            old_digest = hashlib.sha256(original.encode('utf-8')).hexdigest()
            (books / '1.txt').write_bytes(original.replace('\n', '\r\n').encode('utf-8'))
            (books / '1.json').write_text(json.dumps({'id': 1, 'title': 'Test', 'words': 10000, 'digest': old_digest}), encoding='utf-8')
            db = connect(root / 'test.sqlite3')
            try:
                import_book(db, {'id': 1, 'title': 'Test'}, original)
                with db:
                    db.execute('UPDATE books SET digest=? WHERE id=1', (old_digest,))
                self.assertEqual(collect(root, target=1, delay=0), 1)
                metadata = json.loads((books / '1.json').read_text(encoding='utf-8'))
                digest = hashlib.sha256(clean_text((books / '1.txt').read_text(encoding='utf-8')).encode('utf-8')).hexdigest()
                self.assertEqual(metadata['digest'], digest)
                self.assertNotIn(b'\r', (books / '1.txt').read_bytes())
                self.assertEqual(index_directory(db, books), 0)
                self.assertEqual(db.execute('SELECT digest FROM books WHERE id=1').fetchone()[0], digest)
                self.assertFalse(import_book(db, {'id': 2, 'title': 'Duplicate'}, original.replace('\r\n', '\n')))
            finally:
                db.close()

    def test_wrappers_and_unicode(self):
        raw = 'License\n*** START OF THE PROJECT GUTENBERG EBOOK TEST ***\nCafé DON’T 123 ocean.\n*** END OF THE PROJECT GUTENBERG EBOOK TEST ***\nLicense'
        self.assertEqual(tokens(clean_text(raw)), ['café', "don't", 'ocean'])


class PageRankTests(unittest.TestCase):
    def test_star_graph_has_known_stationary_distribution(self):
        rank, _ = pagerank([1, 2, 3], [(1, 2), (1, 3)])
        # Center x = .05 + .85*(1-x); each leaf receives half its mass.
        self.assertAlmostEqual(rank[1], .9 / 1.85, places=8)
        self.assertAlmostEqual(rank[2], rank[3], places=10)
        self.assertAlmostEqual(sum(rank.values()), 1, places=10)

    def test_isolates_and_empty_graph(self):
        self.assertEqual(pagerank([], [])[0], {})
        self.assertEqual(pagerank([1, 2], [])[0], {1: .5, 2: .5})
        rank, _ = pagerank([1, 2, 3], [(1, 2)])
        self.assertGreater(rank[1], rank[3])
        self.assertAlmostEqual(sum(rank.values()), 1)


class WeightedJaccardTests(unittest.TestCase):
    def test_bit_planes_against_independent_count_sums(self):
        rng = random.Random(2026)
        term_ids = list(range(30)) + [127, 255, 2057]
        documents = [{term: rng.choice([1, 2, 3, 8, 256, 4095, 50000])
                      for term in term_ids if rng.random() < .55} for _ in range(12)]
        documents += [{}, {0: 1}, {2057: 2}]
        vectors = [count_vector(counts.items(), 258) for counts in documents]
        for i, left in enumerate(documents):
            for j, right in enumerate(documents):
                common = left.keys() & right.keys()
                expected_min = sum(min(left[t], right[t]) for t in common)
                expected_max = sum(max(left[t], right[t]) for t in common)
                minimum, maximum, mask = weighted_overlap(vectors[i], vectors[j])
                with self.subTest(left=i, right=j):
                    self.assertEqual((minimum, maximum, mask.bit_count()), (expected_min, expected_max, len(common)))

    def test_graph_uses_strict_course_distance_threshold(self):
        with tempfile.TemporaryDirectory() as directory:
            db = connect(Path(directory) / 'weighted.sqlite3')
            try:
                import_book(db, {'id': 1, 'title': 'A'}, 'a a b', min_words=1)
                import_book(db, {'id': 2, 'title': 'B'}, 'a c', min_words=1)
                self.assertEqual(build_graph(db, .5)['edges'], 0)
                self.assertEqual(build_graph(db, .49)['edges'], 1)
                self.assertEqual(db.execute('SELECT similarity FROM edges').fetchone()[0], .5)
                self.assertEqual(build_graph(db, 0)['edges'], 1)
            finally:
                db.close()


class SearchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = connect(Path(self.temp.name) / 'test.sqlite3')
        corpus = {1: 'sea sea ocean adventure', 2: 'sea ocean voyage',
                  3: 'ocean voyage ship', 4: 'forest tree green'}
        term_ids = {}
        for book_id, text in corpus.items():
            import_book(self.db, {'id': book_id, 'title': str(book_id), 'author': 'Test'}, text, min_words=1, term_ids=term_ids)
        build_graph(self.db, threshold=.9)

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def test_jaccard_edges_against_hand_calculation(self):
        edges = [tuple(r) for r in self.db.execute('SELECT * FROM edges ORDER BY a,b')]
        self.assertEqual(edges, [(1, 3, 1.0), (2, 3, 1.0)])

    def test_keyword_and_frequency_ranking(self):
        result = search(self.db, 'SEA', ranking='frequency')
        self.assertEqual([(b['id'], b['occurrences']) for b in result['results']], [(1, 2), (2, 1)])
        self.assertEqual(result['recommendations'][0]['id'], 3)
        self.assertEqual(result['recommendations'][0]['similarity'], 1.0)

    def test_pagerank_ranking(self):
        result = search(self.db, 'ocean')
        self.assertEqual([b['id'] for b in result['results']], [3, 1, 2])

    def test_regex_occurrence_aggregation(self):
        result = search(self.db, 'sea|ocean', mode='regex', ranking='frequency')
        self.assertEqual([(b['id'], b['occurrences']) for b in result['results']], [(1, 3), (2, 2), (3, 1)])
        self.assertEqual(set(result['matched_terms']), {'sea', 'ocean'})

    def test_regex_prefix_filter_against_exhaustive_reference(self):
        postings = list(self.db.execute('SELECT book_id,word,count FROM postings JOIN terms ON terms.id=term_id'))
        for pattern in ['(s|o).*', 's?ocean', '(sea|)ocean?', '()', '[fs].*', '[^s].*', '.*', '[a-z]+']:
            expected = {}
            for book_id, word, count in postings:
                if re.fullmatch(pattern, word):
                    expected[book_id] = expected.get(book_id, 0) + count
            result = search(self.db, pattern, mode='regex')
            with self.subTest(pattern=pattern):
                self.assertEqual({b['id']: b['occurrences'] for b in result['results']}, expected)

    def test_unicode_regex_prefix(self):
        import_book(self.db, {'id': 5, 'title': 'Unicode'}, 'éclair élève ocean', min_words=1)
        result = search(self.db, '[é].*', mode='regex')
        self.assertEqual([(b['id'], b['occurrences']) for b in result['results']], [(5, 2)])

    def test_pagination_and_recommendation_consistency(self):
        a = search(self.db, 'sea', page=1, page_size=1)
        b = search(self.db, 'sea', page=2, page_size=1)
        self.assertEqual(a['total'], 2)
        self.assertNotEqual(a['results'][0]['id'], b['results'][0]['id'])
        self.assertEqual(a['recommendations'], b['recommendations'])

    def test_invalid_inputs(self):
        for kwargs in [{'query': ''}, {'query': 'sea ocean'}, {'query': 'sea', 'mode': 'unknown'},
                       {'query': 'sea', 'page': 0}, {'query': 'sea', 'ranking': 'unknown'}]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                search(self.db, **kwargs)

    def test_empty_result(self):
        result = search(self.db, 'absent')
        self.assertEqual(result['total'], 0)
        self.assertEqual(result['recommendations'], [])

    def test_duplicate_and_undersized_books(self):
        self.assertFalse(import_book(self.db, {'id': 7, 'title': 'Copy'}, 'forest tree green', min_words=1))
        with self.assertRaises(ValueError):
            import_book(self.db, {'id': 8, 'title': 'Short'}, 'short')
        self.assertEqual(stats(self.db)['books'], 4)

    def test_new_book_invalidates_graph(self):
        import_book(self.db, {'id': 5, 'title': 'New'}, 'new vocabulary', min_words=1)
        self.assertIsNone(stats(self.db)['graph'])
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM scores').fetchone()[0], 0)

    def test_validation_detects_incomplete_normalized_scores(self):
        with self.db:
            self.db.execute('DELETE FROM scores WHERE book_id=4')
            self.db.execute('UPDATE scores SET score=score/(SELECT SUM(score) FROM scores)')
        checks = validate(self.db)['checks']
        self.assertTrue(checks['pagerank_normalized'])
        self.assertFalse(checks['pagerank_coverage'])

    def test_validation_detects_incorrect_posting_totals(self):
        with self.db:
            self.db.execute('UPDATE postings SET count=count+1 WHERE book_id=1')
        checks = validate(self.db)['checks']
        self.assertFalse(checks['index_counts'])
        self.assertTrue(checks['graph_counts'])

    def test_bulk_import_rolls_back_failed_batch_and_preserves_graph(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for book_id, text in [(7, 'sea whale ocean adventure ' * 2500), (8, 'too short')]:
                (root / f'{book_id}.json').write_text(json.dumps({'id': book_id, 'title': 'Bulk test'}), encoding='utf-8')
                (root / f'{book_id}.txt').write_text(text, encoding='utf-8')
            graph = stats(self.db)['graph']
            with self.assertRaises(ValueError):
                index_directory(self.db, root)
            self.assertEqual(self.db.execute('SELECT COUNT(*) FROM books').fetchone()[0], 4)
            self.assertEqual(stats(self.db)['graph'], graph)


if __name__ == '__main__':
    unittest.main()
