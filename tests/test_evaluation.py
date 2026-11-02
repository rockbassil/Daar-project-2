"""Synthetic metric fixtures only; these are not participant feedback."""
import csv
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from scripts.evaluate_relevance import FIELDS, summarize


class EvaluationTests(unittest.TestCase):
    def fixture(self, directory, complete=True):
        output = Path(directory)
        groups, rows = [], []
        for ranking, judgments in [('frequency', [1, 0, 0, 1, 0]), ('pagerank', [1, 1, 0, 1, 0])]:
            groups.append(dict(participant='synthetic', task='fixture', mode='keyword', query='sea',
                               ranking=ranking, book_ids=[1, 2, 3, 4, 5], recommendation_ids=[6]))
            for rank, judgment in enumerate(judgments, 1):
                rows.append(dict(participant='synthetic', task='fixture', mode='keyword', query='sea',
                                 ranking=ranking, rank=str(rank), book_id=str(rank),
                                 relevant=str(judgment) if complete else '', recommendation_rating='',
                                 task_completed='', comment='Synthetic unit-test fixture'))
        (output / 'manifest.json').write_text(json.dumps({'groups': groups}), encoding='utf-8')
        self.save(output, rows)
        return output, rows

    def save(self, output, rows):
        with (output / 'feedback.csv').open('w', newline='', encoding='utf-8') as stream:
            writer = csv.DictWriter(stream, FIELDS)
            writer.writeheader()
            writer.writerows(rows)

    def result(self, output):
        with redirect_stdout(StringIO()):
            return summarize(output)

    def test_known_precision_and_paired_difference(self):
        with tempfile.TemporaryDirectory() as directory:
            output, _ = self.fixture(directory)
            result = self.result(output)
            self.assertEqual(result['status'], 'complete')
            self.assertAlmostEqual(result['by_ranking']['frequency']['mean_precision_at_5'], .4)
            self.assertAlmostEqual(result['by_ranking']['pagerank']['mean_precision_at_5'], .6)
            self.assertAlmostEqual(result['mean_paired_pagerank_minus_frequency'], .2)
            self.assertIsNone(result['by_ranking']['frequency']['mean_recommendation_rating'])

    def test_blank_and_deleted_judgments_are_missing_not_negative(self):
        with tempfile.TemporaryDirectory() as directory:
            output, rows = self.fixture(directory, complete=False)
            result = self.result(output)
            self.assertEqual(result['completed_trials'], 0)
            self.assertEqual(result['missing_judgments'], 10)
            self.assertEqual(result['by_ranking'], {})
            self.save(output, rows[:-1])
            self.assertEqual(self.result(output)['missing_judgments'], 10)

    def test_incomplete_trial_does_not_enter_mean_or_pair(self):
        with tempfile.TemporaryDirectory() as directory:
            output, rows = self.fixture(directory)
            rows[0]['relevant'] = ''
            self.save(output, rows)
            result = self.result(output)
            self.assertEqual(result['status'], 'partial')
            self.assertEqual(result['completed_trials'], 1)
            self.assertEqual(result['paired_trials'], 0)
            self.assertNotIn('frequency', result['by_ranking'])

    def test_reject_duplicate_altered_and_invalid_judgments(self):
        with tempfile.TemporaryDirectory() as directory:
            output, rows = self.fixture(directory)
            self.save(output, rows + [rows[0]])
            with self.assertRaises(ValueError):
                self.result(output)
            for field, invalid in [('book_id', '999'), ('query', 'other'), ('relevant', '2')]:
                modified = [dict(row) for row in rows]
                modified[0][field] = invalid
                self.save(output, modified)
                with self.assertRaises(ValueError):
                    self.result(output)


if __name__ == '__main__':
    unittest.main()
