# Assignment compliance review — 20 October 2026

Reviewed all three pages of `daar_projet2_en.pdf` against the current source, database, tests, documentation, saved measurements and preview archive. The PDF was used as the assessment specification. This review does not establish completion of work outside this folder.

**Verdict: the core application passes the checks performed, but the complete assignment is not ready for submission.**

## Fresh verification

- `python -m unittest discover -s tests -v`: 27 tests passed, covering algorithms, normalization, search, ranking, graph behavior, recommendations and HTTP integration.
- `python -m library validate`: all 11 checks passed, including SQLite integrity, postings totals, foreign keys, graph consistency and positive normalized PageRank coverage.
- Current database: 1,700 books, 133,587,611 indexed tokens, minimum 10,021 tokens per book, 1,700 distinct content digests, 522,166 indexed terms, 310,714 graph edges.
- `node scripts/browser_check.cjs`, against a temporary local server on port 18020: passed keyword search, frequency ordering, pagination, regex search, invalid-regex errors, recommendation rendering and a 390-pixel mobile layout, with no detected JavaScript errors. The temporary server was stopped. Fresh screenshots and metadata are in `reports/audit-2026-10-20/browser/`.
- Checked the graph formula against the locally available Lecture 3 PDF, pages 10–12: the code uses occurrence counts over shared words and a strict distance threshold, matching the displayed formula. Unicode tokenization is a documented extension of the lecture's Latin-letter example; explain it in the report.
- Existing `dist/daar-assignment2-PREVIEW.zip`: approximately 1.06 MB; ZIP integrity check passed. Its status explicitly says preview, its name has no actual team surnames, and it contains no final report or video.

## Requirements and remaining evidence

| Requirement in brief | Assessment | Evidence or required action |
| --- | --- | --- |
| Interactive web/mobile app, server logic and client views (p. 1) | Pass within automated scope | Python HTTP server, browser UI, fresh HTTP and browser tests. |
| At least 1,664 books, each at least 10,000 words (p. 1) | Pass by current index counts | 1,700 indexed books; shortest 10,021 normalized tokens. Stored counts agree with postings. |
| Disk storage or remote content pointers (p. 1) | Implemented | Local source corpus, SQLite metadata and Gutenberg source links. |
| Keyword search (p. 1) | Pass | Inverted-index lookup, functional and HTTP tests. |
| Advanced regex search (p. 1) | Pass for supported grammar | Custom Thompson NFA matches complete indexed words, an explicitly permitted search approach. |
| Ranked results and at least one specified centrality (pp. 1–2) | Pass | Frequency and PageRank ordering; PageRank satisfies the centrality choice. Closeness and betweenness are not additionally required. |
| Implicit recommendations (p. 2) | Implemented and tested | Neighbors of the highest-ranked results in the course graph. Click tracking is an alternative, not an additional requirement. Human usefulness remains unverified. |
| Increasing-size performance experiments and stress tests (pp. 1–2) | Existing evidence present | CSV, environment metadata and SVG charts for 100/500/1,000/1,700 books; HTTP concurrency experiments at 1/2/4 clients. These historical measurements were inspected, not rerun in this review. |
| Relevance/user test campaign (pp. 1–2) | Missing evidence | `docs/relevance-feedback.csv` contains only a header. Collect actual judgments of search results and recommendations; document methodology and results. |
| Centrality definition, implemented algorithm and actual-book calculations in final report (p. 2) | Supporting notes only | Algorithm notes and real-book examples exist, but no final report PDF was found. Integrate and explain them in the report. |
| Algorithm definitions/data structures, literature, justified choices, dataset methodology, citations, charts/discussion, conclusion and perspectives (p. 2) | Final deliverable missing | Existing plans and notes do not establish completion of these report requirements. |
| Report normally 10–15 pages, 12 recommended (p. 2) | Missing | Write and export the final report. Pages 16 onward will not be read. |
| Presentation with working demo (pp. 2–3) | Missing | The folder selects a video and contains a plan, but no finished video. Record 4:30–5:30 covering essential presentation points and a solid working demonstration. Alternatively prepare the permitted live presentation, maximum 20 minutes. |
| Various clients; live demo on at least two distinct clients on the same LAN/WLAN (pp. 2–3) | No physical-test evidence | Browser viewport emulation does not establish this. Record actual devices, browsers, simultaneous searches and outcomes. Three machines—one server and two clients—are recommended for the live demo. |
| Team of two or three (p. 3) | Unverified | Establish actual members and surnames. |
| One final archive with documentation, commented source, video if selected and necessary examiner materials (p. 3) | Incomplete | Only a preview exists. Assemble the finished materials and verify setup after extracting the final package into a clean folder. |
| Archive approximately 30 MB maximum, required surname filename (p. 3) | Final package unverified | Preview size passes, but does not predict final size with video. Use `daar-assignment2-SURNAME1-SURNAME2[-SURNAME3].zip`. |
| Moodle upload by 22 November 2026, 23:59 (p. 3) | Not verifiable locally | Submit the completed package by the deadline stated in the supplied brief. Live presentation, if chosen: 16 November 2026, 10:45–12:45. |

## Limits and issues to explain

The existing HTTP results show 24/24 successful requests with one or two clients, but only 2/24 successes and 22 HTTP 503 responses at four clients. The server deliberately permits two active searches. This is a capacity limitation to discuss; rejected requests must not be counted as successful search throughput. The brief supplies no numeric latency or concurrency pass threshold.

Saved scaling measurements reuse some indexing and full-graph timing phases, as disclosed in `docs/results-summary.md` and the experiment metadata. Preserve that disclosure in the final report. Engine latency excludes HTTP, browser rendering and network time.

Database validation checks internal consistency; it does not independently reconstruct every edge or recompute all source word counts. The earlier `reports/final-results/corpus-verification.json` reports source hash and wrapper checks with no issues. Those full source checks were not repeated here. Exact-content deduplication does not establish that every retained Gutenberg edition is a different literary work.

The existing `docs/requirement-audit.md` describes an older development state with 12 indexed books and historical defects. Its historical findings must not be mistaken for the current database status. Use this review for the current submission gaps.

## Completion order

1. Collect real human relevance and recommendation feedback, and record actual client-device tests.
2. Finish the original report with citations, actual-book calculations, charts and interpretation of limitations.
3. Record and time the selected video, including the working demonstration and essential presentation content.
4. Confirm the team, package the finished materials with the required filename and size, and test the extracted submission.
5. Upload the final package to Moodle on time.

The brief assigns approximately 30% to code, 40% to the report and 30% to presentation. Passing the application tests does not establish completion of those academic deliverables. No application source was changed during this review.
