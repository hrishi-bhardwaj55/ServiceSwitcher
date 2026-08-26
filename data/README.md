# Data workspace

All account data in ServicerSwitch is synthetic. The directories in this workspace
are populated incrementally by the build chunks:

- `generator/`: deterministic account generation, validation, and property tests
- `faults/`: five deterministic injectors, tricky-case builders, oracle, and label
  validation
- `render/`: three PDF template families, corpus renderer, validators, and held-out
  isolation check
- `accounts/`: generated canonical account JSON
- `documents/`: generated PDF document sets
- `ground_truth/`: machine-readable expected findings
- `traces/`: server-side investigator trajectories

Generated records, PDFs, labels, and traces are ignored by Git unless a later chunk
explicitly promotes a small fixture into version control.

See [`docs/synthetic-data.md`](../docs/synthetic-data.md) for the generator contract,
commands, and invariant definitions. See
[`docs/fault-injection.md`](../docs/fault-injection.md) for bucket assignments,
impact semantics, and ground-truth validation. See
[`docs/document-rendering.md`](../docs/document-rendering.md) for the five-document
output contract, family split, and PDF validation workflow.
