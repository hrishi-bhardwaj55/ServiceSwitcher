# Regulation retrieval evaluation

Embedding model: `text-embedding-3-small` at 512 dimensions. Corpus: 47 chunks. Dataset:
25 labeled queries. Each metric is the macro average across cases.

| Strategy | Recall@5 | Precision@5 | MRR |
|---|---:|---:|---:|
| Vector only | 96.00% | 19.20% | 0.9000 |
| Hybrid (vector + `tsvector` RRF) | 96.00% | 19.20% | 0.9200 |

Production choice: **hybrid retrieval**. The selection rule prioritizes
Recall@5, then MRR, then Precision@5. See `docs/evals.md` for the decision record and
benchmark limitations.
