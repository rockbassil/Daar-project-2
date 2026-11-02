# Assignment completion checklist

## Implemented in this workspace

- [x] Reproducible, resumable corpus collector with minimum word count and exact-content deduplication.
- [x] Inverted index with occurrence counts and Unicode normalization.
- [x] Keyword search.
- [x] Regex search over indexed words, using a custom Thompson NFA.
- [x] Lecture 3 occurrence-weighted Jaccard graph with configurable strict threshold.
- [x] PageRank with dangling-node handling and convergence checking.
- [x] Ranked results and graph-neighbor recommendations.
- [x] Responsive browser UI with errors, loading state, pagination and source links.
- [x] Algorithm correctness tests and HTTP integration tests.
- [x] Repeatable scaling experiment with raw measurements and SVG charts.
- [x] Setup and LAN demo instructions.

## Must be verified/completed before submission

- [ ] Confirm team of 2–3 and any additional technology constraints.
- [x] Check graph and regex definitions against the supplied course materials.
- [x] Download and index at least 1,664 qualifying books (1,700 completed).
- [x] Rebuild graph and run `python -m library validate` successfully.
- [x] Measure graph thresholds and connectivity on the full corpus.
- [ ] Evaluate recommendation quality with real users.
- [x] Run full-corpus performance experiments; document results and limitations.
- [ ] Run human relevance tests; record actual feedback and methodology.
- [ ] Demonstrate on two distinct client machines on the same LAN/WLAN.
- [ ] Write original 10–15-page report with citations and actual book examples.
  - A 12-page working draft now exists in `docs/report-draft.pdf`; finalization awaits team details, actual evaluations and team review. See `docs/finish-without-presentation.md`.
- [ ] Record the selected video presentation (4:30–5:30); plan is in `docs/video-plan.md`.
- [ ] Include a solid demonstration in the chosen presentation format.
- [ ] Package commented source, documentation and required materials, around 30 MB max.
- [ ] Use `daar-assignment2-SURNAME1-SURNAME2[-SURNAME3].zip`.
- [ ] Submit on Moodle by 22 November 2026, 23:59 (date in supplied brief).

Do not check off human evaluations or multi-device testing based on automated tests.
