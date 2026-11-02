# Final implementation and measured results

The prepared corpus contains 1,700 distinct Gutenberg books, 133,587,611 normalized word tokens and 522,166 indexed terms. The shortest book has 10,021 words. Every saved text has Gutenberg wrapper markers and a canonical content hash matching its index metadata. `reports/final-results/corpus.csv` records the exact corpus; `corpus-verification.json` records the file checks.

All 27 automated tests passed. Full-database validation passed all 11 checks, covering corpus size, SQLite integrity, index counts, foreign keys, the course graph definition, edge consistency and finite normalized PageRank coverage. Final Chrome checks passed keyword and regex searches, malformed expressions, frequency ordering, pagination, recommendations and a 390-pixel mobile viewport. These checks do not replace physical-device or human relevance testing.

## Scaling measurements

| Books | Index seconds | Graph seconds | Edges | Database MiB | Keyword median ms | Regex median ms |
|---:|---:|---:|---:|---:|---:|---:|
| 100 | 22.33 | 3.48 | 980 | 20.97 | 0.77 | 16.17 |
| 500 | 90.97 | 58.18 | 31,715 | 92.80 | 2.81 | 49.21 |
| 1,000 | 205.75 | 244.79 | 105,010 | 189.51 | 5.26 | 73.11 |
| 1,700 | 417.90 | 721.68 | 310,714 | 304.89 | 11.55 | 94.76 |

Raw measurements, environment details and standalone SVG charts are in `reports/final-results/`. Search measurements use one warmup and five repetitions per query. Keyword queries are `sea`, `love` and `science`; regex queries are `sea|ocean`, `adventur.*` and `lov(e|ing)`. Table medians aggregate the measurements for each mode. These are engine timings, excluding HTTP and browser rendering.

Index times were reused from the actual independent fresh-index runs in `reports/set-jaccard-results/scaling.csv`: the corpus and indexing implementation did not change when the graph formula was corrected. The final experiment assembled identical logical subsets from the prepared index, separately recording assembly times of 5.14, 14.90, 32.15 and 59.37 seconds. Graphs for the first three sizes were recomputed with the corrected formula. The full graph uses the recorded 721.68-second CLI run that built the final database graph. This avoids presenting reused phases as newly timed work. Environment metadata records the reuse sources.

Pairwise graph construction grows roughly quadratically with corpus size. The index and selected queries scale more gently, but these measurements cover one machine and a small fixed query set. Broad regex patterns can scan much more of the vocabulary than patterns with a finite initial-character range. No general latency guarantee follows from these medians.

## Course graph and threshold analysis

The implementation follows [Lecture 3, pages 10–12](https://perso.lip6.fr/binh-minh.bui-xuan/files/daar2026/daar3.pdf). For shared words C, let m be the sum of the smaller occurrence count and M the sum of the larger occurrence count. Similarity is m/M; distance is (M−m)/M. The summation domain is shared words, as printed in the lecture. With no shared words, the implementation assigns similarity zero and distance one. An edge exists only when distance is strictly below 0.50, equivalently similarity strictly above 0.50.

| Minimum similarity, strict | Edges | Mean degree | Isolated books | Components | Largest component |
|---:|---:|---:|---:|---:|---:|
| 0.50 | 310,714 | 365.55 | 11 | 16 | 1,664 |
| 0.55 | 160,186 | 188.45 | 26 | 33 | 1,644 |
| 0.60 | 55,620 | 65.44 | 116 | 135 | 1,520 |
| 0.65 | 9,380 | 11.04 | 421 | 492 | 947 |

The 0.50 default keeps most books in one connected component. Stricter cutoffs reduce density and increase fragmentation. Connectivity alone does not demonstrate meaningful recommendations or establish an optimal threshold. Actual relevance feedback remains necessary. Details are in `reports/final-results/graph/`.

For the actual indexed editions of *Frankenstein* (Gutenberg 84) and *Pride and Prejudice* (1342), 3,652 distinct words are shared. The shared-word minimum sum is 57,924 and maximum sum is 125,860. Similarity is 0.46022565 and distance 0.53977435, so this pair has no edge at the default threshold.

PageRank uses an unweighted undirected graph, damping 0.85, uniform teleportation and redistributed dangling-node mass. It converged in 77 iterations at an L1 tolerance of 1e-10. For Alice (11), degree 288, the final update is approximately 0.00008823529412 teleportation + 0.00000048797800 dangling share + 0.00040929414568 incoming contributions = 0.00049801741781. Its stored rank is 0.00049801741784; the tiny difference is the convergence residual. Other actual-book calculations are saved in `graph/analysis.json`.

## HTTP and browser evidence

The fixed HTTP mix includes keyword and regex searches, with 24 requests at each concurrency level. One client completed 24/24 successfully, with a 61.08 ms successful-request median. Two clients completed 24/24 successfully, with a 208.58 ms median. Four clients completed two requests successfully and received 22 expected HTTP 503 busy responses because only two search slots are allowed. There were no other errors. Rejection throughput is not successful search capacity. Raw requests, timing summaries and environment information are in `reports/final-results/http/`.

The HTTP experiment ran on loopback. Chrome mobile checks emulate a viewport. Neither proves operation on two physical machines. Use `docs/testing-guide.md` to test actual LAN clients and record real relevance judgments in `docs/relevance-feedback.csv`. The original report and recorded presentation remain team deliverables; `docs/video-plan.md` provides the selected five-minute structure.
