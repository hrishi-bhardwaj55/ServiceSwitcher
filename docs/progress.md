# Implementation progress

This ledger records completed specification gates and durable implementation
decisions. A chunk is marked complete only after its acceptance commands pass and it
is merged to `main`.

| Chunk | Status | Acceptance evidence |
|---|---|---|
| C0 — domain model | Complete | Hand-computable escrow and payment examples documented; tag `c0-done` |
| C1 — repository skeleton | Complete | Full local verification passed; four Compose services healthy; tag `c1-done` |
| C2–C16 | Not started | Mandatory chunk order preserved |

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
