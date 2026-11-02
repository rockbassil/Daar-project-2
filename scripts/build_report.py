"""Build the editable 12-page report from verified results, preserving pending evidence."""
import csv
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def table(headers, rows):
    return '<table><tr>' + ''.join(f'<th>{html.escape(str(h))}</th>' for h in headers) + '</tr>' + ''.join(
        '<tr>' + ''.join(f'<td>{html.escape(str(v))}</td>' for v in row) + '</tr>' for row in rows) + '</table>'


def main():
    template = (ROOT / 'docs/report-source.html').read_text(encoding='utf-8')
    team = json.loads((ROOT / 'docs/team.json').read_text(encoding='utf-8'))
    members = team.get('members', [])
    if not isinstance(members, list) or any(not isinstance(m, str) or not m.strip() for m in members):
        raise ValueError('Team members must be nonempty strings.')
    if members and len(members) not in (2, 3):
        raise ValueError('The brief requires two or three team members.')
    summary_path = ROOT / 'reports/evaluation/summary.json'
    # Refresh metrics from actual CSV judgments; never rely on stale summary data.
    if (summary_path.parent / 'feedback.csv').exists():
        from evaluate_relevance import summarize
        evaluation = summarize(summary_path.parent)
    else:
        evaluation = {'completed_trials': 0, 'status': 'no_completed_trials'}
    with (ROOT / 'docs/device-tests.csv').open(encoding='utf-8-sig', newline='') as stream:
        devices = list(csv.DictReader(stream))
    with (ROOT / 'reports/final-results/scaling.csv').open(encoding='utf-8', newline='') as stream:
        scaling = list(csv.DictReader(stream))
    graph = json.loads((ROOT / 'reports/final-results/graph/analysis.json').read_text(encoding='utf-8'))
    http_path = ROOT / 'reports/audit-2026-10-20/http/summary.csv'
    with http_path.open(encoding='utf-8', newline='') as stream:
        http_rows = list(csv.DictReader(stream))
    missing = []
    if not members:
        missing.append('team names')
    if evaluation.get('status') != 'complete':
        missing.append('completed human evaluation')
    # Recorded device observations are displayed, but machine code cannot certify real devices.
    missing.append('team review of physical-client evidence and report')
    human = ('Human evaluation is pending: no completed judgments. Prepared slots are not actual participants.'
             if not evaluation['completed_trials'] else
             f'Human evaluation status: {evaluation["status"]}; {evaluation["completed_trials"]} completed trials; '
             f'{evaluation["participants_with_completed_trials"]} participants with completed trials. '
             'Review the full summary and integrate qualitative feedback before submission.')
    if evaluation['completed_trials']:
        human += table(['Ranking', 'Completed trials', 'Mean P@5'],
                       [(r, v['completed_trials'], f'{v["mean_precision_at_5"]:.3f}')
                        for r, v in evaluation['by_ranking'].items()])
    device_html = ('<p>No physical-client observations have been recorded. This section is pending.</p>' if not devices else
                  table(['Date', 'Device', 'Browser', 'Notes'],
                        [(d['date'], d['device'], d['browser'], d['notes']) for d in devices]) +
                  '<p>See the full device CSV for individual checks; recorded rows require team review.</p>')
    replacements = {
        'TEAM': html.escape(', '.join(members)) if members else 'Pending — actual 2–3 member names required',
        'STATUS': 'WORKING DRAFT — pending ' + html.escape('; '.join(missing)) + '. Presentation/video deferred.',
        'HUMAN_STATUS': human,
        'DEVICE_STATUS': device_html,
        'THRESHOLDS': table(['Similarity >', 'Edges', 'Isolates', 'Components', 'Largest'],
                            [(t['threshold'], f'{t["edges"]:,}', t['isolated_books'], t['components'], t['largest_component'])
                             for t in graph['thresholds']]),
        'SCALING_PREP': table(['Books', 'Index (s)', 'Graph (s)', 'Edges', 'DB (MiB)'],
                             [(r['books'], f'{float(r["index_seconds"]):.2f}', f'{float(r["graph_seconds"]):.2f}',
                               f'{int(r["edges"]):,}', f'{float(r["database_mb"]):.2f}') for r in scaling]),
        'HTTP': table(['Clients', 'Success / 24', '503', 'Median ms', 'p95 ms'],
                      [(r['clients'], r['successes'], r['rejected_503'], f'{float(r["success_median_ms"]):.2f}',
                        f'{float(r["success_p95_ms"]):.2f}') for r in http_rows]),
    }
    for key, value in replacements.items():
        template = template.replace('{{' + key + '}}', value)
    if '{{' in template:
        raise ValueError('Unresolved template field.')
    destination = ROOT / 'docs/report-draft.html'
    destination.write_text(template, encoding='utf-8')
    print(f'Built {destination}; export with node scripts/export_report.cjs')


if __name__ == '__main__':
    main()
