# ServicerSwitch

ServicerSwitch is a demoable mortgage-servicing transfer auditor. It combines a
deterministic financial reconciliation engine with a tool-using AI investigator,
and requires document-level evidence for every AI-assisted claim.

> Status: C8 complete — confidence-gated model fallback preserves 100% A/B field
> accuracy and measures 93.04% exact fields plus 78.14% page citations on the
> held-out layout. See the
> [implementation ledger](docs/progress.md).

## Project principles

- Financial arithmetic, comparisons, and duplicate detection are deterministic.
- AI is reserved for document understanding, ambiguity resolution, and explanation.
- Findings cite a document, page, field, and value.
- Synthetic ground truth and held-out document layouts measure false positives as
  well as recall.
- The product provides audit information, not legal conclusions.

## Documentation

- [Build specification](servicerswitch_v1_spec.md)
- [Mortgage and escrow domain model](docs/domain-model.md)
- [Synthetic account generation](docs/synthetic-data.md)
- [Fault injection and ground truth](docs/fault-injection.md)
- [Deterministic reconciliation engine](docs/reconciliation-engine.md)
- [Deterministic engine evaluation](evals/reports/engine.md)
- [Synthetic document rendering](docs/document-rendering.md)
- [Deterministic PDF extraction](docs/deterministic-extraction.md)
- [Model-backed extraction fallback](docs/llm-extraction-fallback.md)
- [Model-backed extraction evaluation](evals/reports/extraction.md)
- [Extraction confidence calibration](evals/reports/calibration.md)
- [Implementation progress](docs/progress.md)

## Services

- `apps/engine`: stateless Java 21 / Spring Boot 3 reconciliation service on port
  `8080`, exposing `POST /reconcile`
- `apps/ai`: Python 3.12 / FastAPI extraction and investigation service on port
  `8000`
- `apps/web`: Next.js 15 audit interface on port `3000`
- `postgres`: PostgreSQL 16 with pgvector on port `5432`

## Quickstart

Docker is the only runtime prerequisite for the service foundation:

```bash
cp .env.example .env
docker compose up --build -d
curl -fsS http://localhost:3000
curl -fsS http://localhost:8080/health
curl -fsS http://localhost:8000/health
```

The API health endpoints return typed JSON such as
`{"service":"engine","status":"ok"}`. Stop the stack without removing its database
volume:

```bash
docker compose down
```

## Verification

Install Java 21, Python 3.12 or 3.13, Node.js 22, and GNU Make, then install the two
dependency sets:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e "./apps/ai[dev]"
npm ci --prefix apps/web
make verify
```

On Windows PowerShell, activate with `.\.venv\Scripts\Activate.ps1` and run
`make PYTHON=.venv/Scripts/python.exe verify` when GNU Make is available. The same
verification gate runs on every push and pull request.

## Synthetic accounts

Generate the deterministic 300-account corpus and independently validate every
financial invariant:

```bash
make generate-accounts
make validate-accounts
```

The generated JSON is written to `data/accounts/` and intentionally ignored by Git.
The default seed is stable, so repeated generation produces byte-identical files.

Build and validate the labeled reconciliation corpus:

```bash
make inject-faults
make validate-ground-truth
```

This produces 200 single-fault cases, 60 clean cases, and 40 clean-but-tricky cases,
with exact labels in `data/ground_truth/cases.jsonl`.

## Deterministic engine evaluation

Run the structured-data baseline before any document extraction or AI processing:

```bash
make eval-engine
```

The target is strict: 100% precision, recall, and F1; zero false positives across
the 100 clean cases; and financial-impact mean absolute error below $0.01. The
runner packages and starts an isolated engine process, evaluates all 300 cases over
`POST /reconcile`, writes `evals/reports/engine.md`, and exits nonzero if any target
is missed.

## Synthetic PDFs

Render and validate the five-document set for every account:

```bash
make render-documents
make validate-documents
```

The output contains 1,500 PDFs under `data/documents/<account_id>/`, split 40%, 40%,
and 20% across modern, legacy, and held-out layouts. Validation checks every page
count and required extractable value. CI also prevents the held-out family from
being referenced by extraction code or prompts under `apps/ai/`.

## Deterministic extraction

Measure the plain-parser baseline on the permitted development layouts:

```bash
make eval-extraction-deterministic
```

The extractor uses keyword signatures and label proximity over PyMuPDF word
coordinates. It returns typed money, rate, date, text, and due-date fields with a
one-based page, bounding box, source text, and confidence. The stable report is
written to `evals/reports/extraction_deterministic.md`.

## Model-backed fallback

Export real provider credentials into the process environment before running the
local evaluator:

```bash
LLM_API_KEY=... LLM_MODEL=... make eval-extraction
```

PowerShell users can set `$env:LLM_API_KEY` and `$env:LLM_MODEL`, then run the same
Make target. A repository `.env` file is consumed by Docker Compose, not implicitly
by the local Python runner.

The fallback requests only missing or low-confidence fields, schema-validates every
response, rejects invalid pages and values, and surfaces deterministic/model
disagreements for review. The real evaluation intentionally reports development and
held-out layouts in separate columns. With `gpt-5.4-mini`, A/B scores 100% exact
fields and pages without fallback; held-out Family C scores 93.04% exact fields and
78.14% page citations with fallback on every document. See the
[evaluation report](evals/reports/extraction.md) and
[calibration report](evals/reports/calibration.md).
