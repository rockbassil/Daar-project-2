# DAAR assignment 2 requirement audit

This records the initial audit before the subsequent completion work. For current
corpus, fixes, and verification results, see `docs/progress.md` and
`reports/final-results/`. The missing-corpus and hash findings below have since
been addressed, and the graph definition has been aligned with Lecture 3; the academic and physical-testing items need actual evidence.

Verified on 4 October 2026 against all three pages of `daar_projet2_en.pdf`, the application source, generated data, tests, and existing documentation. This is an audit, not the final academic report. No application code or corpus preparation was changed or launched during this review.

The application implements the main required features and passes its current tests. The project is not ready for submission: the searchable database has only 12 books, collection stopped at 1,516 books, and the academic evaluations and final deliverables are absent from this folder.

## Verified evidence

- `python -m unittest discover -s tests -v`: all 18 tests passed, including keyword/regex search, occurrence aggregation, frequency/PageRank ordering, Jaccard edges, recommendations, and HTTP behavior.
- `python -m library validate`: failed the corpus minimum; index counts, foreign keys, graph availability, and PageRank normalization passed.
- Current database: 12 books, 1,491,826 tokens, 34,072 distinct indexed terms, shortest book 26,776 words. SQLite integrity check returned `ok`.
- Current graph: 12 vertices, 31 edges, Jaccard similarity threshold 0.30; PageRank converged in 27 iterations.
- Existing Chrome browser checks were rerun successfully: keyword search, frequency ordering, recommendations, regex, malformed-expression errors, and a 390-pixel mobile layout. These checks do not establish usability on two physical devices.
- All 1,516 downloaded text files were read and their cleaned word tokens recounted: 120,209,652 tokens total; minimum 10,021. There are 1,516 distinct cleaned-content hashes, and every metadata file has a corresponding text file.
- There are 148 books missing from the 1,664 minimum, or 184 from the configured 1,700 target. The full downloaded collection has not been indexed.
- Preparation log last changed on 27 September 2026, ending at book 1,516; the status file still says `collect`. No Python preparation process was found during the audit. The recorded PID 5464 now belongs to a different process: PID existence alone is insufficient to establish that the old preparation job is running.
- Saved benchmarks cover only 4, 8, and 12 books, three query repetitions, and engine latency. Their subsets differ from the 12 classic books currently indexed, so their graph edge counts need not match the running database.

## Requirements from the brief

“Implemented” below means verified on the development database, not validated at the required final corpus size. “No evidence” means the folder cannot establish completion; a team may have materials elsewhere.

| Brief requirement | Status and evidence | Remaining action |
| --- | --- | --- |
| Interactive web/mobile application with server logic and client views (p. 1) | Implemented in `library/server.py`, `web/index.html`, and `web/app.js`; HTTP and browser checks passed. | Recheck on final corpus and physical clients. |
| At least 1,664 books (p. 1) | Not met: 1,516 downloaded; only 12 searchable. | Complete collection, index, graph, and validation. Use 1,700 to cover the later wording referring to examples from a database of more than 1,664 books. |
| Every book at least 10,000 words (p. 1) | Met for every currently downloaded and indexed book using documented normalized word tokenization. | Retain this check for final corpus; explain tokenization in the report. |
| Storage on disk or pointers to remotely stored texts (p. 1) | Implemented: source text files plus Gutenberg links and SQLite metadata. | Document acquisition and reproducible setup. |
| Keyword search returns books whose index contains the keyword (p. 1) | Implemented with normalized single-word lookup and postings. | Check representative queries at final size. |
| Advanced regular-expression search (p. 1) | Implemented with a custom Thompson NFA over whole indexed words; this is one of the explicitly permitted approaches. | Compare grammar and semantics with Lecture 1; measure full vocabulary scans. |
| Implicit relevance ordering (p. 1) | Implemented: decreasing occurrence count or decreasing PageRank. | Evaluate actual relevance; explain tie handling. |
| Jaccard graph and at least one of closeness, betweenness, or PageRank (pp. 1–2) | Implemented: exact set Jaccard, threshold graph, unweighted undirected PageRank. PageRank alone satisfies the required centrality choice. | Compare representation, distance convention, and graph definition with Lecture 3; justify threshold on full corpus. Lecture notes are absent. |
| Report centrality definition, computation algorithm, and worked examples using actual corpus books (p. 2) | Partial: algorithm notes and synthetic hand examples exist. No final report or worked real-book computations found. | Include formula, iterations/convergence, and calculations on well-chosen actual books. |
| Implicit recommendations alongside search results (p. 2) | Implemented through graph neighbors of the three highest-ranked matches, up to six recommendations. The graph-neighbor option satisfies the brief; click tracking is not additionally required. | Evaluate recommendation usefulness. Broad queries matching all books can legitimately yield none under the current exclusion rule. |
| Relevance/user evaluations (pp. 1–2) | No actual participant feedback or completed relevance study found; `docs/report-plan.md` contains a proposed protocol. | Conduct real user tests and retain methodology, judgments, results, and limitations. |
| Performance evaluation with increasingly large datasets and stress tests (pp. 1–2) | Partial: repeatable benchmark script and tiny-corpus charts exist. No final-scale or HTTP load measurements found. | Run increasing-size experiments, stress simultaneous requests, plot results, and discuss them. |
| Algorithm problem definitions and data structures in report (p. 2) | Partial: `docs/algorithms.md` documents choices, but is not the final report. | Cover all implemented algorithms, including indexing, regex, graph construction, centrality, and recommendations. |
| Theoretical presentation/state of the art and justified choices/criticism (p. 2) | Partial: notes list suggested references. No completed literature review or technology comparison found. | Read/cite sources, compare alternatives, explain complexity and practical tradeoffs. |
| Test dataset methodology and proper references (p. 2) | Partial: collector and benchmark subset policy are documented. | Describe sourcing, sampling bias, preprocessing, experimental subsets and user recruitment; cite external work correctly. |
| Performance charts preferred to raw numbers; discussion appreciated (p. 2) | Tiny-corpus CSV and SVG bar charts exist. | Produce final-scale charts and interpret results rather than only including tables. |
| Report conclusion and perspectives for textual search engines (p. 2) | No completed report found. | Write conclusion, limitations, and future directions. |
| Typical report 10–15 pages, recommended 12; pages 16+ not read (p. 2) | Only plans/notes found. | Write the final report and export a PDF of at most 15 pages. |
| Oral presentation OR video pitch, including a working demo (pp. 2–3) | No final slides or video found. | Choose one format and rehearse/record a solid application demo. |
| Oral introduction: members, goals, functional analysis, initial wireframes, technologies plus comparison chart and justification (p. 2) | No final presentation, team roster, wireframes, or technology comparison found. | Prepare these materials. Work organization/HR chart is optional in the brief. Do not label newly created sketches as original early wireframes. |
| Oral technical part: architecture, client views vs sketches, database/index/graph storage, server algorithms (p. 2) | Architecture and algorithm notes exist; presentation absent. | Convert verified implementation and evaluation results into presentation content. |
| Oral duration at most 20 minutes; approximately 7/10/3 minutes for introduction/technical/demo; 18–22 slides recommended (pp. 2–3) | Not verifiable. | Prepare and time a rehearsal. Slide count is a recommendation. |
| Oral demo on at least two distinct clients on the same team-provided LAN/WLAN; three machines recommended (p. 3) | LAN instructions and responsive UI exist. No actual physical multi-client test evidence found. | Demonstrate simultaneous laptop/phone access; ideally one server plus two remote clients. Browser viewport emulation does not satisfy this requirement. |
| Video alternative roughly five minutes, within 10% (4:30–5:30), essential oral points and solid demo sequence (p. 3) | No video found. | If choosing video, meet length and content requirements and include the video in the package. |
| Team of two or three (p. 3) | No evidence establishing members/count. | Confirm team roster and surnames for the final filename. |
| One archive containing documentation, commented source, video if chosen, and necessary examiner materials (p. 3) | No final submission archive found. Source has comments/docstrings; documentation is unfinished. | Assemble a reproducible submission and test it from a clean extracted folder. |
| Compressed archive at most approximately 30 MB (p. 3) | No final archive. Downloaded text/metadata alone occupy 752,009,913 bytes before compression. | Measure archive size; omit generated corpus/DB/caches when examiner setup remains reproducible. Explain how the full dataset is obtained. If the examiner needs additional dataset/video delivery, resolve this with the instructor. |
| Filename `daar-assignment2-SURNAME1-SURNAME2[-SURNAME3].EXT`, accepted compressed archive extension (p. 3) | Not prepared. | Use actual surnames and e.g. `.zip`; third surname only for a three-person team. |
| Upload package to Moodle by 22 November 2026, 23:59 (p. 3) | Future submission; not verifiable from folder. | Submit the completed archive on time. Date is from the supplied PDF. |
| Oral presentation 16 November 2026, 10:45–12:45; order determined in TME5/TME6 (p. 3) | Schedule stated by supplied PDF. | If choosing oral, confirm allocated order and prepare the team LAN/demo. |

## Additional code finding

Windows line-ending conversion makes the collector's saved SHA-256 metadata inconsistent with the text subsequently read by the indexer. `collect.py` hashes downloaded cleaned content, then uses `Path.write_text()` with default Windows newline conversion. All 1,516 stored texts contain doubled CR line endings (`CR CR LF`). All 1,516 metadata hashes match after reversing that write conversion, but none match the content as `read_text()` subsequently supplies it to the indexer. This explains the mismatches; no unexplained hash mismatch was found.

This does not change the verified word counts or currently observed distinctness. It does mean collector and indexer use different digest representations, and it weakens reliable content deduplication across different newline encodings. Normalize line endings before hashing, preserve writes consistently, and reconcile existing file/DB digests before relying on hashes as an end-to-end integrity check. Do not simply treat the current metadata mismatches as file corruption.

Full-corpus behavior remains unverified. Regex scans have an eight-second vocabulary-scan budget; graph construction compares every book pair. Measure these on the final dataset. The HTTP server allows two active searches and rejects additional concurrent searches with 503, so load tests should report successful latency and rejected/error requests.

## What to do next, in order

1. Confirm the two/three-person team and compare regex/Jaccard/PageRank definitions with Lectures 1 and 3. The supplied PDF does not mandate a programming language or framework.
2. Correct the newline/hash consistency issue, accounting for existing files and digests. No repair was made as part of this audit.
3. Resume the corpus pipeline below. It resumes existing downloads, then indexes, builds the graph, and validates. Expect substantial processing time; do not launch duplicate preparation jobs. Check process identity, not merely the old saved PID.

   ```powershell
   python scripts/prepare_library.py --target 1700
   python -m library stats
   python -m library validate
   ```

   Completion means the searchable database has at least 1,664 qualifying books and all validation checks pass, not merely that files have downloaded.

4. Evaluate the full graph's threshold, connectivity, isolated nodes, and recommendation usefulness. Retain actual book examples for the report and rebuild the final graph after settling the threshold.
5. Run final performance experiments and actual relevance tests. With the current threshold:

   ```powershell
   python scripts/benchmark.py --sizes 100 500 1000 1700 --repeats 5 --output reports/final-results
   ```

   Use `--threshold` if your justified final threshold changes. Separate output preserves the existing development measurements. Also measure concurrent HTTP requests and errors; the existing benchmark measures only engine latency. Conduct real user evaluations rather than claiming automated correctness establishes relevance.

6. Test at least two distinct physical clients on the same LAN/WLAN. Start `python -m library serve --host 0.0.0.0 --port 8000`, obtain the server's LAN IPv4 using `ipconfig`, and open `http://SERVER_IPV4:8000` on both clients. Record actual test results.
7. Write the final report with real measurements, citations, justified choices, and worked centrality examples. Prepare the chosen presentation/video with a working demo, then build and test the correctly named archive within the size limit.

The brief allocates approximately 30% to code, 40% to the report, and 30% to presentation. Once the corpus and full-scale behavior are verified, prioritize evaluation and academic deliverables over extra application features.
