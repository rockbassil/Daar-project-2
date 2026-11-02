"""Prepare blinded human judging sheets and summarize only completed judgments."""
import argparse
import csv
import html
import json
import random
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from library.engine import search

TASKS = [
    ('sea-travel', 'Find a book substantially about sea travel or life at sea.', 'sea', 'keyword'),
    ('detectives', 'Find a book substantially about detective investigations.', 'detective', 'keyword'),
    ('science', 'Find a book substantially about scientific knowledge or discovery.', 'science', 'keyword'),
    ('sea-regex', 'Find a book substantially about the sea or ocean, using advanced search.', 'sea|ocean', 'regex'),
]
FIELDS = ['participant', 'task', 'query', 'mode', 'ranking', 'rank', 'book_id',
          'relevant', 'recommendation_rating', 'task_completed', 'comment']


def prepare(output, participants):
    if (output / 'feedback.csv').exists():
        raise ValueError('feedback.csv already exists; choose another output folder to preserve judgments.')
    if len(set(participants)) != len(participants) or any(not p.strip() for p in participants):
        raise ValueError('Participant IDs must be unique and nonempty.')
    output.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(f'{(ROOT / "data/library.sqlite3").as_uri()}?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    rows, groups, sections = [], [], []
    try:
        for participant in participants:
            trials = [(task, instruction, query, mode, ranking)
                      for task, instruction, query, mode in TASKS
                      for ranking in ['frequency', 'pagerank']]
            random.Random('daar-evaluation-' + participant).shuffle(trials)
            for number, (task, instruction, query, mode, ranking) in enumerate(trials, 1):
                result = search(db, query, mode, ranking)
                books = result['results'][:5]
                if len(books) != 5:
                    raise ValueError(f'{query!r} has fewer than five results; revise protocol before recruitment.')
                trial = f'{participant}-{number:02d}'
                groups.append(dict(participant=participant, task=task, query=query, mode=mode,
                                   ranking=ranking, trial=trial, book_ids=[b['id'] for b in books],
                                   recommendation_ids=[b['id'] for b in result['recommendations']]))
                parts = [f'<section><h2>{html.escape(trial)}</h2><p><strong>Task:</strong> {html.escape(instruction)}</p>',
                         f'<p>Query: <code>{html.escape(query)}</code>; mode: {mode}. ',
                         'Inspect the original books using the links. Mark 1 only if the book substantially addresses the task, '
                         'rather than merely mentioning the word. Mark 0 otherwise. You may report uncertainty in a comment.</p>',
                         '<table><tr><th>Rank / book</th><th>Relevant (0/1)</th><th>Reason</th></tr>']
                for rank, book in enumerate(books, 1):
                    rows.append(dict(participant=participant, task=task, query=query, mode=mode,
                                     ranking=ranking, rank=rank, book_id=book['id'], relevant='',
                                     recommendation_rating='', task_completed='', comment=''))
                    parts.append(f'<tr><td>{rank}. <a href="{html.escape(book["source"], quote=True)}">'
                                 f'{html.escape(book["title"])} (PG {book["id"]})</a></td><td></td><td></td></tr>')
                parts.append('</table><h3>Recommended books</h3><ul>')
                for book in result['recommendations']:
                    parts.append(f'<li><a href="{html.escape(book["source"], quote=True)}">'
                                 f'{html.escape(book["title"])} (PG {book["id"]})</a></li>')
                parts.append('</ul><p>Overall recommendation usefulness: 1 (not useful) to 5 (very useful): ____; '
                             'leave blank if no recommendations. Task completed (0/1): ____.</p>'
                             '<p>Comments: ________________________________________________________</p></section>')
                sections.append(''.join(parts))
    finally:
        db.close()
    with (output / 'feedback.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    manifest = dict(prepared_utc=datetime.now(timezone.utc).isoformat(),
                    status='prepared_not_conducted', seed_policy='fixed per anonymous participant ID',
                    participants=participants, groups=groups,
                    method='Five binary judgments per task/ranking. Overall ratings on the rank-1 CSV row only.')
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    document = ('<!doctype html><html lang="en"><meta charset="utf-8"><title>Relevance judging sheets</title>'
                '<style>body{font:15px Arial;max-width:900px;margin:30px auto}section{break-before:page}'
                'table{border-collapse:collapse;width:100%}td,th{border:1px solid #888;padding:10px}'
                'td:nth-child(2){width:90px}td:last-child{width:160px}a{color:#163f6b}</style>'
                '<h1>Human relevance evaluation — uncompleted worksheets</h1>'
                '<p>Use anonymous IDs; participant slots are not evidence of recruited people. '
                'Allow approximately 20–30 minutes per participant; offer breaks. Participation is voluntary. '
                'Rankings are hidden on these sheets. Do not tell participants which algorithm produced a trial.</p>'
                '<p>After the session, the facilitator transfers judgments to feedback.csv using manifest.json '
                'to map trial IDs to task/ranking. Put recommendation_rating and task_completed on rank 1 only. '
                'Do not fill blanks with invented results. Shared books between trials can cause learning effects.</p>'
                + ''.join(sections) + '</html>')
    (output / 'judging-sheets.html').write_text(document, encoding='utf-8')
    print(f'Prepared {len(groups)} trials with {len(rows)} blank judgments in {output}')


def summarize(output):
    manifest = json.loads((output / 'manifest.json').read_text(encoding='utf-8'))
    with (output / 'feedback.csv').open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    expected = {(g['participant'], g['task'], g['mode'], g['ranking'], str(i)): str(book)
                for g in manifest['groups'] for i, book in enumerate(g['book_ids'], 1)}
    seen, grouped = set(), defaultdict(list)
    for row in rows:
        key = tuple(row.get(k, '') for k in ['participant', 'task', 'mode', 'ranking', 'rank'])
        if key not in expected or key in seen or row['book_id'] != expected[key]:
            raise ValueError(f'Unexpected, duplicate or altered result row: {key}')
        seen.add(key)
        if row['query'] != next(g['query'] for g in manifest['groups'] if
                               (g['participant'], g['task'], g['mode'], g['ranking']) == key[:4]):
            raise ValueError(f'Altered query: {key}')
        for field, allowed in [('relevant', {'', '0', '1'}), ('task_completed', {'', '0', '1'}),
                               ('recommendation_rating', {'', '1', '2', '3', '4', '5'})]:
            if row[field] not in allowed:
                raise ValueError(f'Invalid {field} for {key}')
        if row['rank'] != '1' and (row['task_completed'] or row['recommendation_rating']):
            raise ValueError('Overall ratings belong on the rank-1 row only.')
        grouped[key[:4]].append(row)
    completed, aggregates = [], defaultdict(list)
    for key, trial_rows in grouped.items():
        if len(trial_rows) != 5 or any(r['relevant'] == '' for r in trial_rows):
            continue
        precision = sum(int(r['relevant']) for r in trial_rows) / 5
        first = next(r for r in trial_rows if r['rank'] == '1')
        item = dict(participant=key[0], task=key[1], mode=key[2], ranking=key[3],
                    precision_at_5=precision,
                    recommendation_rating=int(first['recommendation_rating']) if first['recommendation_rating'] else None,
                    task_completed=int(first['task_completed']) if first['task_completed'] else None)
        completed.append(item)
        aggregates[key[3]].append(item)
    by_ranking = {}
    for ranking, items in aggregates.items():
        ratings = [i['recommendation_rating'] for i in items if i['recommendation_rating'] is not None]
        tasks = [i['task_completed'] for i in items if i['task_completed'] is not None]
        by_ranking[ranking] = dict(completed_trials=len(items),
            mean_precision_at_5=sum(i['precision_at_5'] for i in items) / len(items),
            recommendation_ratings=len(ratings), mean_recommendation_rating=sum(ratings)/len(ratings) if ratings else None,
            task_completion_responses=len(tasks), task_completion_rate=sum(tasks)/len(tasks) if tasks else None)
    pairs = defaultdict(dict)
    for item in completed:
        pairs[(item['participant'], item['task'], item['mode'])][item['ranking']] = item['precision_at_5']
    differences = [p['pagerank']-p['frequency'] for p in pairs.values() if len(p) == 2]
    result = dict(status='no_completed_trials' if not completed else
                  ('complete' if len(completed) == len(manifest['groups']) else 'partial'),
                  expected_trials=len(manifest['groups']), completed_trials=len(completed),
                  participants_with_completed_trials=len({i['participant'] for i in completed}),
                  missing_judgments=sum(r['relevant'] == '' for r in rows) + len(expected)-len(seen),
                  by_ranking=by_ranking, paired_trials=len(differences),
                  mean_paired_pagerank_minus_frequency=sum(differences)/len(differences) if differences else None,
                  trials=completed,
                  note='Descriptive judgments only; no recall, causal benefit or statistical significance is established.')
    (output / 'summary.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k != 'trials'}, indent=2))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare', 'summarize'])
    parser.add_argument('--output', type=Path, default=ROOT / 'reports/evaluation')
    parser.add_argument('--participants', nargs='+', default=['P01', 'P02', 'P03'])
    args = parser.parse_args()
    try:
        prepare(args.output, args.participants) if args.command == 'prepare' else summarize(args.output)
    except (ValueError, OSError) as error:
        parser.exit(1, f'Error: {error}\n')


if __name__ == '__main__':
    main()
