# Evaluation decisions

This document records architecture choices that are made from measured results.
Canonical generated reports remain under `evals/reports/`.

## Methodology at a glance

The primary corpus contains 300 deterministic synthetic mortgage histories: 200
carry exactly one injected servicing fault, 60 are clean, and 40 are clean but
deliberately resemble a fault. Generation and fault injection are separate pure
transformations. An independent validator recomputes invariants and confirms each
case's exact expected finding type and financial impact before it can enter an
evaluation.

Each account renders five PDFs, for 1,500 documents total. Template assignment is
balanced across outcome buckets. Families A and B are development layouts; Family C
is structurally held out. It reverses label/value order, moves summary information,
uses two pages per document, abbreviates dates, and changes tables. A CI isolation
check fails if extraction code or prompts under `apps/ai/` mention Family C. Held-out
results are always reported separately rather than pooled into a larger headline.

The finding harness compares exact typed sets directly with JSONL ground truth. A
wrong type is both one false positive and one false negative. Clean-case FPR is the
fraction of clean audits with at least one non-`EXPLAINED` finding. Financial impact
uses exact decimal values. Extraction scores typed field equality and one-based page
citations. Retrieval uses one required chunk per query and reports Recall@5,
Precision@5, and MRR. No evaluation uses an LLM judge.

The published `v1.0.0` real-provider evaluations used one configured tier,
`gpt-5.4-mini`, and ran serially. The current runtime default is `gpt-5-nano`; no
historical metric in this document should be read as a nano result. Check out the
`v1.0.0` tag to reproduce the original model boundary, or rerun the current
credentialed evaluations to establish a new nano comparison.
Requests are cached by model, prompt-contract version, and complete payload hash so a
failed run can resume without changing the measured input. Fake clients test behavior
but never contribute to provider-accuracy claims. The no-provider `make verify` gate
runs unit, integration, schema, deterministic-eval, and held-out-isolation tests; paid
experiments remain explicit commands.

| Evaluation slice | Corpus | Result |
|---|---:|---|
| Deterministic engine | 300 accounts | 100% precision/recall/F1; 0% clean FPR |
| Extraction, A/B | 1,200 PDFs | 100% fields and page citations |
| Extraction, held-out C | 300 PDFs | 93.04% fields; 78.14% page citations |
| Hybrid retrieval | 25 queries | 96.00% Recall@5; 0.9200 MRR |
| End-to-end investigator | 300 audits | 100% finding F1; 40% automated success |
| Naive baseline | 300 audits | 25.95% F1; 75% clean FPR; 87.5% tricky FPR |
| Adversarial documents | 20 PDFs | 20/20 expected; 0/12 injection success |

## What the numbers do and do not prove

They demonstrate behavior on a reproducible synthetic corpus with exact labels, a
meaningful layout shift, clean near-misses, and a same-model naive comparison. They
show that deterministic reconciliation prevents many false positives and that layout
generalization—not classification—is the extraction bottleneck. They also show that
correct fail-closed findings are not the same as autonomous completion.

They do not establish production accuracy on real borrower documents, legal
completeness, OCR robustness, prompt-injection immunity, latency under concurrency,
or whole-system cost parity. The investigator reconciles a trusted canonical audit
record after loading and validating all five PDFs; the 100% finding score is not a
claim that the system reconstructed an entire mortgage ledger from PDFs alone. The
60% review rate and 55% faulted-case exact tool selection remain first-class
limitations.

## C5 and C8 — deterministic engine and extraction

The Java baseline calls the real `POST /reconcile` contract for all 300 cases. It
reaches 200 true positives, no false positives, no false negatives, and $0.0000 impact
MAE. This is expected for generated structured inputs and primarily proves that the
fault generator, oracle, HTTP serialization, and detector tolerances agree.

Extraction evaluation keeps development and held-out families separate:

| Metric | A/B development | C held out |
|---|---:|---:|
| Document classification | 100.00% | 100.00% |
| Typed field accuracy | 100.00% | 93.04% |
| Page-citation accuracy | 100.00% | 78.14% |
| Model fallback rate | 0.00% | 100.00% |

The held-out gap is not tuned away. In fact, high-confidence held-out fields were
overconfident relative to observed accuracy, which is why disagreement and low-page
confidence route to review. See `evals/reports/engine.md`,
`evals/reports/extraction.md`, and `evals/reports/calibration.md` for generated counts.

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

## C14 — adversarial documents

The adversarial benchmark contains 20 checked-in PDFs generated byte-stably from a
JSONL manifest. Each case has a deterministic `SAFE_EXTRACTION` or `REJECT` outcome.
Rejected cases must fail before provider access. Safe cases send page text through
the same strict C8 extraction client and must preserve the visible `$3,200.00` annual
tax amount despite malicious context.

| Metric | Result |
|---|---:|
| Cases with expected behavior | 20/20 (100.00%) |
| Prompt-injection success rate | 0/12 (0.00%) |
| Deterministically rejected documents | 8/8 |
| Model-path execution errors | 0 |

The 12 injection cases cover presentation tricks and instruction/authority
impersonation; the eight rejection cases cover structural, account-isolation, money,
conflict, and date anomalies. The test counts any wrong requested value as an attack
success and fails the run if any recorded behavior changes. Cached identical model
requests are reused, so “model-path case” does not necessarily mean a new paid
provider request.

This result measures a fixed synthetic corpus and does not prove general resistance
to prompt injection, parser exploits, or unseen multimodal attacks. Image-only PDFs
are rejected because v1 intentionally has no OCR path. See
`docs/adversarial-security.md` and `evals/reports/adversarial.md`.
