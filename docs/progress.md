# Development checkpoint — 27 September 2026

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
