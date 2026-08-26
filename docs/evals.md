# Evaluation decisions

This document records architecture choices that are made from measured results.
Canonical generated reports remain under `evals/reports/`.

## C9 — regulation retrieval

The retrieval evaluation uses 25 labeled questions against 47 curated chunks from
12 CFR §§ 1024.17, 1024.33, and 1024.38 plus CFPB Bulletin 2014-01. Each question
has one required chunk. Both strategies use `text-embedding-3-small` at 512
dimensions and return five results.

| Strategy | Recall@5 | Precision@5 | MRR |
|---|---:|---:|---:|
| Vector only | 96.00% | 19.20% | 0.9000 |
| Hybrid: vector + PostgreSQL `tsvector` with RRF | 96.00% | 19.20% | 0.9200 |

**Production choice: hybrid retrieval.** Coverage and precision are tied, while
hybrid raises mean reciprocal rank by 0.0200. It therefore places the first required
source earlier without sacrificing top-five coverage. Reciprocal rank fusion uses a
fixed `k=60`; there is no reranker or third retrieval strategy.

Because every case has exactly one required source, perfect Precision@5 is 20.00%.
The reported 19.20% precision and 96.00% recall both mean that 24 of 25 required
chunks appeared in the first five results. This benchmark measures retrieval over a
small curated corpus; it is not a legal-completeness evaluation and is not an
independent held-out corpus.

Reproduce the result with configured PostgreSQL and embedding credentials:

```bash
make ingest-kb
make eval-rag
```

The labeled cases are in `evals/datasets/rag.jsonl`; the generated result is in
`evals/reports/rag.md`.
