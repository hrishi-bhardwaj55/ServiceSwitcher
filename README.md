# ServicerSwitch

ServicerSwitch is a demoable mortgage-servicing transfer auditor. It combines a
deterministic financial reconciliation engine with a tool-using AI investigator,
and requires document-level evidence for every AI-assisted claim.

> Status: C0 complete — the mortgage and escrow model is documented. C1 adds the
> runnable service skeleton, tests, containers, and CI.

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

## Planned services

- `apps/engine`: stateless Java 21 / Spring Boot reconciliation service
- `apps/ai`: Python 3.12 / FastAPI extraction and investigation service
- `apps/web`: Next.js 15 audit interface

Setup and verification instructions will be added in C1, when the runnable service
skeleton and CI pipeline land.
