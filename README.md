# Margin — DAAR book search

A responsive book search application with an SQLite inverted index, a custom
Thompson-NFA regular-expression engine, an exact Jaccard similarity graph,
PageRank ranking, and graph-neighbor recommendations.

**Python 3.10+ only. No pip/npm packages or API keys are required by the app.**
The browser UI uses plain HTML/CSS/JavaScript; it has no build step or CDN dependency.

## Run it

In PowerShell, open this project directory and run:

```powershell
# First-time setup: fetch 12 real books for development.
python -m library collect --seed
python -m library index
python -m library graph
python -m library serve
```

Open **http://127.0.0.1:8000**. Stop with Ctrl+C.
After setup, only `python -m library serve` is needed. Search works offline;
opening the original book on Gutenberg requires internet access.

Try `ocean`, `love`, `adventure`, or advanced expressions `sea|ocean`, `adventur.*`,
and `lov(e|ing)`. Keyword search accepts one word. Regex matches **whole indexed
words**, not full book text; `.*sea.*` expresses substring matching. Expressions
are case-folded like the index. Supported operators: `. | () * + ? [a-z] [^abc]`.
There are no anchors, counted repeats, shorthand classes, lookarounds or backreferences.

## Build the assignment corpus

```powershell
python -m library collect --target 1700
python -m library index
python -m library graph --threshold 0.30
python -m library validate
```

Collection is resumable. Each retained book must have at least 10,000 normalized
word tokens after Gutenberg wrapper removal. SHA-256 rejects identical cleaned
texts, but does not identify different editions of the same work. Downloads are
sequential with a two-second delay by default. A full corpus takes substantial
time and disk space; the target is 1,700 to exceed the assignment's minimum.
The development corpus is **not** sufficient for final submission.

Or run the complete preparation pipeline (collect, index, graph, validation):

```powershell
python scripts/prepare_library.py --target 1700
```

This writes progress to `data/preparation.json` and `data/preparation.log` and
stops on errors. Rerun the same command to resume after an interrupted download.
Do not start two corpus preparation processes simultaneously.

Files are fetched from an official Gutenberg mirror; the CSV metadata catalog
comes from the catalog endpoint. Original source files, including their license
wrappers, are retained in `data/books/`. The index uses cleaned content.
See [Gutenberg's robot access policy](https://www.gutenberg.org/policy/robot_access.html)
and [official mirror list](https://www.gutenberg.org/MIRRORS.ALL).

`index` skips existing IDs and invalidates old graph scores when new books are
added. Run `graph` after every import. Stop corpus mutation before a final demo
or benchmark. To inspect progress: `python -m library stats`.

## Verify and measure

```powershell
python -m unittest discover -s tests -v
python scripts/benchmark.py --sizes 4 8 12 --repeats 3
# After collecting the full corpus:
python scripts/benchmark.py --sizes 100 500 1000 1700 --repeats 5
```

The benchmark creates temporary independent indexes, uses nested subsets ordered
by Gutenberg ID, and writes raw timings, environment metadata and SVG charts to
`reports/results/`. If the corpus is smaller than a requested size, it reports the
actual size; it never labels a 12-book experiment as a 1,700-book experiment.
These measure engine latency, not end-to-end HTTP latency. Human relevance tests
and multi-device validation still need to be carried out and documented.

Optional browser checks (Chrome installed):

```powershell
npm install --prefix .tmp-browser playwright-core
node scripts/browser_check.cjs
```

Run the application first. These checks exercise the actual desktop/mobile UI
and save screenshots in `reports/results/`; the extra npm package is only a test
tool, not an application dependency.

## Demonstrate on two devices

```powershell
python -m library serve --host 0.0.0.0 --port 8000
ipconfig
```

Connect both clients to the same private Wi-Fi/LAN. On each, open
`http://SERVER_IPV4:8000` using the server's LAN IPv4 address from `ipconfig`.
Allow Python on the private network if Windows Firewall asks. Do not use
`localhost` on the other devices. This server is intended for a local course demo,
not a public internet deployment.

## Project layout

```text
library/              Python application and algorithms
  collect.py          Resumable downloads and import
  text.py             Normalization, cleaning, tokenization
  regex.py            Thompson epsilon-NFA compiler and simulation
  engine.py           Index, Jaccard, PageRank, search, recommendations
  db.py               SQLite schema
  server.py           HTTP API and static file serving
web/                  Responsive interface
tests/                Algorithm correctness and HTTP integration tests
scripts/benchmark.py  Scaling measurements and standalone charts
docs/                 Algorithm notes, project checklist, report/presentation plans
data/                 Downloaded corpus and generated DB (not source code)
```

## HTTP API

- `GET /api/stats`: corpus counts, requirement status, graph parameters.
- `GET /api/search?q=ocean&mode=keyword&ranking=pagerank&page=1`
- `GET /api/search?q=sea%7Cocean&mode=regex&ranking=frequency&page=1`

Each result includes title, author, occurrence count, PageRank and a source link.
Recommendations exclude **all** books matching the query, including other pages.
Pagination returns 12 books per page. Invalid input returns HTTP 400.

## Remaining academic deliverables

The implementation is a starting point for the assignment, not a claim that the
whole graded submission is complete. Use [the checklist](docs/checklist.md) and
[report plan](docs/report-plan.md). In particular, confirm course-specific graph
and regex definitions against the lecture notes, gather human relevance feedback,
run the full-corpus experiments, and prepare your own report and presentation.

The brief states: live presentation **16 November 2026, 10:45–12:45**; Moodle
submission **22 November 2026, 23:59**. The report is typically 10–15 pages (12
recommended; pages 16+ are not read). Use the required archive filename
`daar-assignment2-SURNAME1-SURNAME2[-SURNAME3].zip` and keep it around 30 MB or less.
Exclude generated corpus, DB, temporary tools and caches from the source archive;
include download/setup instructions and any materials the examiner needs.
Confirm with the instructor how to provide a video if it makes the archive too large.
