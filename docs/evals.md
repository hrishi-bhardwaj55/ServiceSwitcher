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

## C13 — naive long-context baseline

The baseline uses the identical 300 ground-truth cases and five rendered PDFs per
case. PyMuPDF text is concatenated with document IDs and one-based page markers, then
sent in one strict structured-output request to `gpt-5.4-mini`. There is no document
extraction pipeline, canonical audit record, reconciliation engine, retrieval, tool
call, retry of an invalid model result, or LLM judge.

| Metric | Agent | Naive baseline |
|---|---:|---:|
| Finding precision | 100.00% | 20.28% |
| Finding recall | 100.00% | 36.00% |
| Finding F1 | 100.00% | 25.95% |
| Exact finding-set task success | 100.00% | 16.67% |
| All-clean false-positive rate | 0.00% | 75.00% |
| Clean-but-tricky false-positive rate | 0.00% | 87.50% |
| Mean model cost per audit | $0.001730 | $0.003795 |
| Latency p50 / p95 | 2.320s / 5.632s | 3.624s / 7.721s |

**Interpretation:** on this corpus, the deterministic reconciliation boundary earns
its complexity. The naive model both misses expected discrepancy types and invents
discrepancies on clean records. A single full-document call is also 2.19× the
investigator-only token cost and slower at both measured latency percentiles.

The cost columns are not whole-system cost parity: baseline cost covers its sole
full-context request, while agent cost covers investigator calls and excludes
embeddings plus cached C8 extraction. The agent also reconciles the trusted canonical
audit record, so this experiment demonstrates the value of that architecture on the
synthetic corpus; it does not prove the same advantage for a PDF-only production
ledger reconstruction. Results are a single serialized provider pass and may vary
across a fresh stochastic rerun. Full generated reports are in
`evals/reports/baseline.md` and `evals/reports/comparison.md`.
