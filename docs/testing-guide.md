# Test the completed application

The app runs with Python 3.10+ and uses no pip/npm packages or API keys. Start it from this project directory:

```powershell
python -m library serve --host 0.0.0.0 --port 8000
```

Open http://127.0.0.1:8000 on the server computer. Alternatively, double-click `run.cmd`, which validates the database before starting the server. If a server is already running on port 8000, use that instance rather than starting another.

## Functional test route

| Action | Expected behavior |
| --- | --- |
| Read the collection counts | At least 1,664 books, with a built graph; the development warning is absent. |
| Search `whale` in keyword mode | Matching books appear with occurrence counts and PageRank scores. |
| Change order to Word frequency | Occurrence counts decrease from the first result downward. |
| Change order to PageRank | PageRank decreases from the first result downward; ties use occurrence counts. |
| Search uppercase `OCEAN` | Same normalized keyword matches as `ocean`. |
| Search `ocean`, use Next and Previous | Different books on successive pages; controls indicate the current page. |
| Use Advanced / Regex with `sea\|ocean` | Books containing either indexed word; occurrence counts aggregate matching terms. |
| Use `adventur.*` or `lov(e\|ing)` | Whole indexed words matching the expression are shown above the results. |
| Enter `(` in regex mode | A readable missing-parenthesis error; the page remains usable. |
| Search `zzzznotawordzzzz` | An empty-results message. |
| Search `frankenstein` and inspect recommendations | Recommendations, when graph neighbors outside the matching set exist, link to actual Gutenberg records and show vocabulary similarity. |
| Open a returned book | Its Gutenberg page opens in a new tab. This action needs internet. |
| Test a narrow phone viewport | Search controls and results fit without horizontal scrolling. |

Regex matches whole indexed words. Use `.*sea.*` for words containing `sea`. Unsupported anchors, shorthand classes such as `\d`, lookarounds, counted repeats, and backreferences return errors. A broad query may match every book, leaving no nonmatching recommendation candidates; that is permitted behavior.

## Two real client devices

Use at least two distinct client machines on the same private Wi-Fi/LAN. The server computer's browser and a phone can provide two clients; ideally use a separate server and two remote clients. Start the server with `--host 0.0.0.0` as above. Run `ipconfig`, find the LAN IPv4 address of the active network adapter, and open `http://SERVER_IPV4:8000` on each remote client. A remote client must use the server's address, rather than its own `localhost`. Allow Python on the private network if Windows Firewall requests it.

Perform different searches from both devices and record the devices, browsers, date, and observed results. The automated browser checks use viewport emulation; they do not replace this physical test.

## Capture real relevance feedback

Use `docs/relevance-feedback.csv` as a blank template. Ask several real participants to perform predefined tasks, inspect the top five results, mark relevance, and rate recommendations. Record actual judgments and negative comments. Compare frequency ordering with PageRank using the same queries and randomized presentation order. Keep participant identifiers anonymous.

Suggested tasks: sea travel, detective stories, scientific discovery, and a named character. Keyword matching can find books mentioning a topic without making the whole book relevant; evaluate that limitation honestly. Report precision@5, task completion, recommendation usefulness, participant count, and the judging method. No human feedback has been fabricated by the preparation scripts.

## Reproduce automated checks and measurements

```powershell
python -m unittest discover -s tests -v
python -m library validate
python scripts/benchmark.py --sizes 100 500 1000 1700 --repeats 5 --output reports/final-results
python scripts/http_benchmark.py --clients 1 2 4 --requests 24
```

The engine benchmark builds independent subset indexes and excludes HTTP/network latency. The HTTP benchmark starts its own temporary local server and includes connection handling, search, and JSON output. It reports rejected requests explicitly: the application accepts two active searches and returns 503 when those slots are occupied.

With the normal app server running, `node scripts/browser_check.cjs` exercises the actual interface if the optional local Playwright/Chrome test tools are available. These are development tools, not dependencies needed to run the app.

## Five-minute video

Target 5:00 and remain between 4:30 and 5:30. Show team/goals, justified technologies and architecture, the verified corpus/index/regex/Jaccard/PageRank design, actual evaluation results, and a clear screen recording of the working demo. End with limitations and perspectives. Use `docs/video-plan.md` to rehearse.
