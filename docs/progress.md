# Implementation progress

This ledger records completed specification gates and durable implementation
decisions. A chunk is marked complete only after its acceptance commands pass and it
is merged to `main`.

| Chunk | Status | Acceptance evidence |
|---|---|---|
| C0 — domain model | Complete | Hand-computable escrow and payment examples documented; tag `c0-done` |
| C1 — repository skeleton | Complete | Full local verification passed; four Compose services healthy; tag `c1-done` |
| C2 — synthetic account generator | Complete | Deterministic generation and independent validation pass for 300/300 accounts; property and mutation tests pass; tag `c2-done` |
| C3 — fault injection and ground truth | Complete | 200 single-fault, 60 clean, and 40 clean-but-tricky cases validate 300/300; tag `c3-done` |
| C4 — deterministic reconciliation engine | Complete | Five detectors, explicit explained outcome, tolerance boundary tests, and HTTP contract pass; tag `c4-done` |
| C5 — first eval number | Complete | 100% precision/recall/F1, 0/100 clean false positives, and $0.0000 impact MAE across 300 HTTP reconciliations; tag `c5-done` |
| C6 — document rendering | Complete | 1,500/1,500 PDFs pass page-count and extractable-value validation; exact A/B/C split is 120/120/60; tag `c6-done` |
| C7 — deterministic extraction | Complete | A and B each score 100% classification, field accuracy, and provenance coverage across 1,200 PDFs and 4,080 fields; tag `c7-done` |
| C8–C16 | Not started | Mandatory chunk order preserved |

## Durable decisions

- `main` is the integration branch. The repository's original `master` branch is
  retained remotely for history but receives no new work.
- Java builds use the checked-in Apache Maven Wrapper because contributors should
  not need a global Maven installation.
- Dependency majors follow the specification: Java 21 / Spring Boot 3, Python 3.12+
  / FastAPI / Pydantic v2, and Next.js 15 / React 19.
- The database container is pinned to PostgreSQL 16 with pgvector 0.8.6.
- C1 health tests do not require PostgreSQL; service process health and dependency
  readiness remain separate concepts.
- Canonical monetary JSON fields are decimal strings. This preserves exact cents
  across Python `Decimal`, future Java `BigDecimal`, and generated artifacts.
- The C2 corpus uses a fixed seed and atomic per-file replacement. Re-running the
  generator is byte-stable and removes only stale `account-*.json` generator output.
- Clean accounts include an explicit zero-dollar transfer marker. The old- and
  new-servicer analyses use the same marker balance, making transfer continuity
  directly testable without inventing an off-ledger opening balance.
- Every C3 fault injector is a pure transformation. It preserves non-target
  calculations so the structured-data oracle observes exactly one finding with an
  exact total and monthly impact.
- C3 ground truth is JSONL with decimal-string impacts, matching the canonical
  account serialization and avoiding cross-runtime binary-float ambiguity.
- The C4 engine is stateless and constructs its fixed detector registry in process.
  It has no persistence, database access, AI model, LLM client, or outbound HTTP
  dependency.
- `EXPLAINED` is emitted as a first-class payment outcome with the complete
  decomposition. Evaluation of the five discrepancy types can filter this explicit
  non-finding without losing the explanation.
- Engine evaluation is case-aware and type-aware: a wrong finding type contributes
  one false positive and one false negative. Its impact metric is the per-case mean
  absolute error between expected total impact and the sum of non-`EXPLAINED`
  finding differences.
- `make eval-engine` owns an isolated engine process on an available loopback port,
  so evaluation does not depend on a manually started service or a fixed port.
- Template assignment cycles over every five account identifiers instead of using
  contiguous ranges. The exact 40%/40%/20% distribution therefore remains balanced
  across fault types and clean-case buckets.
- Family C is structurally held out: detail precedes summary, every document has two
  pages, values sit above labels, dates are abbreviated, and source scanning rejects
  any Family C reference under `apps/ai/`.
- PDF validation combines pypdf page/text checks across all 1,500 artifacts with
  Poppler-rendered visual inspection of representative documents from each family.
- Deterministic extraction groups PyMuPDF words into visual lines and accepts values
  only when strict type parsing succeeds on the same row or immediately below a
  known label. It does not infer missing values.
- Extracted percentages use the canonical fractional representation, money remains
  exact `Decimal`, and every accepted value carries a one-based page, value bounding
  box, source text, and bounded confidence.
- The development-set accuracy floors are recorded in tests at 99% classification
  and 98% fields; both layouts currently score 100%, with 100% provenance coverage.
