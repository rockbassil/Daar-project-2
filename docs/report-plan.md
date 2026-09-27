# Report and presentation working plan

This is an outline, not a finished academic report. Fill it with your decisions,
measurements and analysis. Do not invent user feedback or test results.

## Suggested 12-page report allocation

1. Goals, team, assignment constraints, user stories and initial wireframes (1 page).
2. Architecture and justified technology comparison (1 page).
3. Dataset sourcing, sampling, cleaning, word counts and duplicates (1 page).
4. Index design and keyword algorithm; alternatives and complexity (1 page).
5. Regex grammar, Thompson construction, simulation and alternatives (1.5 pages).
6. Jaccard representation, exact calculation and threshold choice (1 page).
7. PageRank definition, convergence and worked real-book examples (1 page).
8. Recommendation method and its limitations (0.5 page).
9. Correctness, performance and user evaluation methodology (1 page).
10. Results with plots, interpretation and threats to validity (1.5 pages).
11. Conclusion, future work and bibliography (1.5 pages).

Adjust for your institution's handling of title pages and references. Stay within
15 total pages, because the brief says pages 16 onward will not be read.

## Relevance evaluation protocol

- Recruit several real testers and record anonymous participant IDs.
- Define tasks before viewing results: e.g. sea travel, scientific discovery,
  detective stories, or a specific character. Distinguish topic queries from
  exact-word queries and note the limitations of lexical matching.
- Each tester inspects the first five results for each task, marks relevant/not
  relevant, and rates usefulness of recommendations on an agreed scale.
- Compare PageRank and frequency ordering with randomized presentation order.
- Record precision@5, task completion, comments and sample size. Explain how
  relevance judgments were made and whether you have agreement between testers.
- Report negative outcomes and limitations, including the small/biased participant
  sample. Use only the actual responses collected.

Suggested CSV fields:
`participant,task,query,mode,ranking,rank,book_id,relevant,recommendation_rating,comment`.

## Performance evaluation

Use `scripts/benchmark.py`. Retain raw samples, environment metadata, corpus IDs
and graph threshold. Include 100, 500, 1,000 and the full corpus. Explain warm-up,
number of repetitions and aggregation. Plot index time, graph time, keyword and
regex latency. Add HTTP concurrency measurements for a stress-test section, and
measure resource usage on the actual test machine. Do not confuse engine latency
with end-to-end browser latency or database file size with peak process memory.

## Live presentation: maximum 20 minutes

- Introduction (~7 min): team, goals, stories, wireframes, technology comparison,
  and task organization. Show actual original sketches if available.
- Technical section (~10 min): architecture; frontend; corpus/index/graph storage;
  algorithms; correctness, performance and relevance results.
- Demo and conclusion (~3 min): keyword, regex, ranking, recommendations, and
  simultaneous access from two distinct clients. Rehearse with the actual LAN.

Aim for 18–22 slides. The brief schedules live presentations for 16 November 2026,
10:45–12:45; the order is to be determined in TME5/TME6.

## Video alternative

Target exactly five minutes (allowed 4:30–5:30). Include the essential project and
technical points, measured results, and a clear working demonstration. Do not
replace the demo with slides or screenshots alone.
