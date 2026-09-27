import itertools
import re
import tempfile
import unittest
from pathlib import Path

from library.db import connect
from library.engine import build_graph, import_book, pagerank, search, stats
from library.regex import Regex
from library.text import clean_text, tokens


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


class SearchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = connect(Path(self.temp.name) / 'test.sqlite3')
        corpus = {1: 'sea sea ocean adventure', 2: 'sea ocean voyage',
                  3: 'ocean voyage ship', 4: 'forest tree green'}
        for book_id, text in corpus.items():
            import_book(self.db, {'id': book_id, 'title': str(book_id), 'author': 'Test'}, text, min_words=1)
        build_graph(self.db, threshold=.4)

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def test_jaccard_edges_against_hand_calculation(self):
        edges = [tuple(r) for r in self.db.execute('SELECT * FROM edges ORDER BY a,b')]
        self.assertEqual(edges, [(1, 2, .5), (2, 3, .5)])

    def test_keyword_and_frequency_ranking(self):
        result = search(self.db, 'SEA', ranking='frequency')
        self.assertEqual([(b['id'], b['occurrences']) for b in result['results']], [(1, 2), (2, 1)])
        self.assertEqual(result['recommendations'][0]['id'], 3)
        self.assertEqual(result['recommendations'][0]['similarity'], .5)

    def test_pagerank_ranking(self):
        result = search(self.db, 'sea')
        self.assertEqual([b['id'] for b in result['results']], [2, 1])

    def test_regex_occurrence_aggregation(self):
        result = search(self.db, 'sea|ocean', mode='regex', ranking='frequency')
        self.assertEqual([(b['id'], b['occurrences']) for b in result['results']], [(1, 3), (2, 2), (3, 1)])
        self.assertEqual(set(result['matched_terms']), {'sea', 'ocean'})

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


if __name__ == '__main__':
    unittest.main()
