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

## C12 — end-to-end investigator

The canonical evaluation runs all 300 audits serially with `gpt-5.4-mini` after PDF
validation and regulation ingestion. Finding labels come directly from the synthetic
ground truth, and tool selection is compared with the primary evidence-tool mapping
in `evals/datasets/agent.jsonl`. No LLM judge is used.

| Metric | Result |
|---|---:|
| Finding precision / recall / F1 | 100.00% / 100.00% / 100.00% |
| Exact finding-set task success | 100.00% |
| Automated task success (no review) | 40.00% |
| Clean / tricky false-positive rate | 0.00% / 0.00% |
| Exact tool-set accuracy, all / faulted | 70.00% / 55.00% |
| Unnecessary calls per run | 0.983 |
| Average / p95 steps | 1.460 / 4 |
| Tool-error recovery | 13/13 (100.00%) |
| Fail-closed model-error cases | 0 |
| Human-review rate | 60.00% |
| Mean investigator cost | $0.001730 per audit |
| Latency p50 / p95 | 2.320s / 5.632s |

**Interpretation:** the architecture protects finding recall and clean-case precision
by retaining deterministic discrepancies when the investigator cannot justify
suppression. That makes the 100% finding score compatible with only 40% autonomous
completion. Tool selection and review rate, not finding F1, are the principal C12
limitations and the clearest optimization targets.

The harness loads all five PDFs and checks extraction/evidence, but reconciliation
uses the synthetic canonical audit record. It therefore measures the orchestration
around trusted structured servicing data rather than reconstructing a complete
mortgage ledger solely from uploaded documents. Latency is local serialized wall
time with the 300 C8 extraction responses already cached; embedding cost is excluded
from the reported investigator token cost.
