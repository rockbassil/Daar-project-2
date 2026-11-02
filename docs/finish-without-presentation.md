# Finish the application, evaluation and report

Presentation/video work is deferred. The application already has a qualifying corpus and functioning server. The remaining human observations cannot be replaced by automated checks.

## Ready now

- Read `docs/report-draft.pdf`: a 12-page working report with algorithm analysis, actual-book calculations, citations, plots, measurement provenance and limitations. Its editable content is `docs/report-source.html`.
- Fresh automated evidence: `reports/audit-2026-10-20/browser/` and `reports/audit-2026-10-20/http/`.
- Open `reports/evaluation/judging-sheets.html` in a browser and print or share the trial pages. The anonymous P01/P02/P03 slots are planned sessions, not completed evaluations. More participants/tasks would strengthen the study; the brief sets no participant minimum.
- `reports/evaluation/feedback.csv` has 120 blank judgments for 24 trials. Do not overwrite it with a new preparation run after entering feedback.

## Team details

Enter the actual full names of the two or three team members in the `members` array in `docs/team.json`. The current report is in English, matching the supplied brief. Review all report text, references and interpretation as a team before submitting; the PDF is deliberately labeled a draft.

## Actual two-device check

The server responded on port 8000 during preparation. The observed Wi-Fi address was `10.61.129.214`; it can change. Check `ipconfig` if needed.

1. On the server computer, open `http://127.0.0.1:8000`.
2. On a phone on the same Wi-Fi, open `http://10.61.129.214:8000` using the current server address. If the server needs restarting, run `python -m library serve --host 0.0.0.0 --port 8000`. Keep the terminal open.
3. On both clients test: keyword `whale`; advanced `sea|ocean`; frequency and PageRank ordering; Next/Previous; invalid regex `(`; a returned book link. Check the phone layout and make overlapping searches from both clients.
4. Record one actual row per device in `docs/device-tests.csv`. Use `pass`, `fail` or `not_tested` for check columns; record real observations and failures. Keep date, model and browser/version. In `regex_sea_or_ocean`, record the actual `sea|ocean` regex result.
5. Capture screenshots. Two viewports on one computer do not count as two physical clients.

If the phone cannot connect, verify the same Wi-Fi, a server bound to `0.0.0.0`, and Python's permission on the Windows private network. Campus/guest Wi-Fi can isolate clients; use a team-controlled hotspot or LAN if necessary. Do not record a pass until the remote request succeeds.

## Human relevance sessions

1. Recruit real volunteers and assign anonymous IDs matching the worksheets; do not collect unnecessary personal details. Three slots are prepared as a starting point.
2. The facilitator keeps `manifest.json` to translate trial IDs into ranking/task. The printed sheets hide ranking labels and vary trial order per participant.
3. Have participants read each task and inspect the five actual books through the supplied links. Mark relevance 1 for substantial topic fit and 0 otherwise; record uncertainty/comments. A title or one word occurrence is not sufficient evidence.
4. Ask whether the task was completed (0/1) and rate the displayed recommendation set from 1 (not useful) to 5 (very useful). Leave a recommendation rating blank when no recommendations exist.
5. Transfer each sheet to its five rows in `reports/evaluation/feedback.csv` using the manifest. Put overall `recommendation_rating` and `task_completed` on the rank-1 row only. Preserve all result IDs and ranking fields. Allow breaks; estimated time is 20–30 minutes per person.
6. Run `python scripts/evaluate_relevance.py summarize`. It computes precision@5 and paired ranking differences, flags missing trials, and never interprets blank judgments as negatives. Preserve qualitative comments and explain study limitations.

The older `docs/relevance-feedback.csv` is a generic empty template. The active study file is **`reports/evaluation/feedback.csv`**.

## Rebuild and review the report

```powershell
python scripts/evaluate_relevance.py summarize
python scripts/build_report.py
node scripts/export_report.cjs
```

HTML generation uses Python's standard library. Optional PDF export uses the existing local Playwright/Chrome test setup. On another machine, `npm install --prefix .tmp-browser playwright-core` plus installed Chrome supplies that optional tool; it is not an application runtime dependency. The HTML can also be printed to PDF from Chrome with A4 paper, CSS margins and browser headers/footers disabled.

Rebuilding refreshes metric tables and recorded device summaries. It deliberately keeps the document a draft for team review. After collecting real results, edit page 11 and the abstract/conclusion in `report-source.html` to discuss actual findings, recruitment, dates, failures and comments. Remove pending statements only once supported. Keep at most 15 pages and check layout after adding results. If choosing English, proofread the terminology and verify every cited claim against its source.

## Package review

`python scripts/package_project.py --preview` builds a review archive without inventing final academic completion. The preview includes source, report draft and evaluation records; full corpus/database and temporary tooling are excluded. Final report/video packaging is deferred until the selected video exists. The preview is not a Moodle-ready final submission.

Run `python scripts/check_package.py` after creating the preview to verify its unit tests, CLI and report HTML build in a clean temporary extraction. This check needs no downloads and deliberately excludes a fresh full-corpus acquisition.

For the current work, completion still depends on actual team names, observed physical-client results, real human judgments and review/finalization of the report. These requirements cannot honestly be checked off from generated templates.
