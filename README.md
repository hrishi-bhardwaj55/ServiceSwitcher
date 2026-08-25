# ServicerSwitch

ServicerSwitch is a demoable mortgage-servicing transfer auditor. It combines a
deterministic financial reconciliation engine with a tool-using AI investigator,
and requires document-level evidence for every AI-assisted claim.

> Status: C1 complete — all three service shells, local orchestration, tests, and
> CI are present. See the [implementation ledger](docs/progress.md).

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
- [Implementation progress](docs/progress.md)

## Services

- `apps/engine`: stateless Java 21 / Spring Boot 3 reconciliation service on port
  `8080`
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
