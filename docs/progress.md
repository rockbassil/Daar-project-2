# Current checkpoint — 20 October 2026

Presentation/video work is deferred. The application source and full corpus are unchanged by this completion pass.

- Fresh review: 27 existing application tests and 11 database validation checks passed; desktop/mobile viewport browser checks passed. Four new evaluation-metric tests also pass, for 31 total.
- Fresh HTTP results at 1/2/4 clients are in `reports/audit-2026-10-20/http/`: 24/24 successes at one and two clients; 2/24 successes and 22 busy responses at four clients. This is a documented server-capacity limit.
- `docs/report-draft.pdf` is a verified 12-page working report with editable HTML source, citations, plots and actual-book computations. It remains a draft until team details, real evaluations and team review are completed.
- `reports/evaluation/judging-sheets.html` and `feedback.csv` prepare a blinded comparison on actual search results. The 24 planned trials contain 120 **blank** judgments and zero completed participants/trials. Preparation is not human evaluation.
- `docs/device-tests.csv` is a blank physical-client observation record. No phone-test pass has been claimed.
- The updated source/results preview is about 2.34 MB. `scripts/check_package.py` passed tests, CLI usage and report HTML generation from a clean temporary extraction without downloads. Evidence is in `reports/audit-2026-10-20/package-check.json`.
- See `docs/finish-without-presentation.md` for the exact remaining steps and report rebuild commands.

Still required outside presentation/video: actual 2–3 member names, human search/recommendation judgments, physical-client observations, and review/finalization of the report. The final Moodle package remains deferred with the selected video.

The following checkpoint records earlier work.

# Historical checkpoint — 4 October 2026

The application is ready for testing at http://127.0.0.1:8000. Double-click `run.cmd` to start it again. See `docs/testing-guide.md` for functional and physical LAN tests.

- 1,700 distinct downloaded and indexed books, 133,587,611 normalized word tokens; shortest book 10,021 words.
- 522,166 indexed terms and 310,714 graph edges. The graph now follows Lecture 3's occurrence-weighted shared-word definition, with strict distance < 0.50.
- PageRank converged in 77 iterations with damping 0.85 and L1 tolerance 1e-10.
- All 11 full-database validation checks and all 27 automated tests passed.
- Final Chrome checks passed for search, ranking, pagination, recommendations, regex/errors, and a 390-pixel mobile layout.
- All source files have Gutenberg wrapper markers and matching canonical hashes. Windows newline corruption was repaired.
- Scaling experiments for 100/500/1,000/1,700 books, graph threshold analysis, and HTTP load tests are complete. Two concurrent HTTP clients completed all 24 requests; four clients triggered expected busy responses from the two-slot search limit.

`docs/results-summary.md` explains measurements, reused phases, actual-book calculations and limitations. Evidence is in `reports/final-results/`. The set-based graph results in `reports/set-jaccard-results/` are historical comparisons, not the final implementation.

Bulk imports use cached vocabulary IDs, atomic 25-book batches and a SQLite cache capped at 512 MiB. Resume saved corpus preparation with `python scripts/prepare_library.py --target 1700 --skip-collect`. Regex matching uses bounded NFA transitions and safe initial-character index ranges.

Remaining academic work requires actual team details, human relevance feedback (`docs/relevance-feedback.csv`), physical two-client LAN testing, the original 10–15-page report and the selected 4:30–5:30 demo video (`docs/video-plan.md`). Automated tests do not establish human relevance or physical-device usability. `scripts/package_project.py --preview` creates a source/results preview; final packaging requires surnames, report PDF and video.

The checkpoint below is historical and does not describe the current corpus or graph.

# Historical development checkpoint — 27 September 2026

## Working and verified

- Application at http://127.0.0.1:8000 when `python -m library serve` is running.
- Initial development database: 12 real Gutenberg books, 1,491,826 indexed words,
  34,072 distinct terms; shortest book 26,776 words.
- Graph at Jaccard threshold .30: 12 vertices, 31 edges; PageRank converged in
  27 iterations to the configured L1 tolerance of 1e-10.
- 18 automated algorithm/HTTP tests passed.
- Headless Chrome checks passed for keyword search, frequency ordering, regex,
  malformed regex errors, recommendations, and a 390-pixel mobile viewport.
- Desktop and mobile screenshots saved under `reports/results/`.
- Small-corpus benchmarks executed; these are development measurements, not the
  required final full-corpus performance evaluation.

## Full corpus preparation

The resumable 1,700-book collection pipeline was launched. It collects books,
then imports them, builds the graph, and validates the final database.
The existing 12-book app stays available during collection.

For current status, inspect these generated files rather than this checkpoint:

```powershell
Get-Content data/preparation.json
Get-Content data/preparation.log -Tail 15
```

If interrupted, resume with:

```powershell
python scripts/prepare_library.py --target 1700
```

Do not run a second pipeline while the existing process is active. The status
file includes its PID. `stage: complete` indicates successful final validation;
`stage: failed` includes the failed stage. After an abrupt system shutdown, the
last stage may remain recorded even though the PID is no longer active.

The development database intentionally fails only the corpus-size requirement
in `python -m library validate`; its index counts, references, graph, and PageRank
normalization passed. Do not claim final compliance until full validation passes.

## Next academic work

After full preparation, run the large scaling benchmarks, evaluate graph
thresholds on the full corpus, collect real human relevance judgments, test two
physical clients on the same LAN, and write the report/presentation with actual
results. Lecture notes and any technology constraints have not been supplied;
the chosen graph/regex definitions still need to be checked against those notes.
