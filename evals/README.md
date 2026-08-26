# Evaluation workspace

ServicerSwitch evaluates deterministic reconciliation, document extraction,
retrieval, the investigator agent, the naive baseline, and adversarial resilience.
Harnesses land only in their specified chunks so reported metrics always reflect
working code and recorded ground truth.

## Deterministic engine baseline

`evals/runners/engine_eval.py` sends canonical structured accounts directly to
`POST /reconcile`. It intentionally bypasses PDFs, extraction, retrieval, and AI.
Run it through the repository target:

```bash
make eval-engine
```

The target regenerates and validates the fixed 300-case corpus, runs the five-case
harness test, packages an engine JAR, starts it on an available loopback port, and
writes the stable report at `evals/reports/engine.md`. The runner exits nonzero when
the C5 acceptance target is missed.

Metrics use finding type as the classification label. A wrong type therefore counts
as both a false positive and a false negative. The false-positive rate is the share
of all 100 `clean` and `clean_but_tricky` cases with at least one discrepancy finding.
Financial-impact accuracy is the per-case mean absolute error between the labeled
total and the sum of returned non-`EXPLAINED` finding differences.

To evaluate an already running engine instead, use:

```bash
python -m evals.runners.engine_eval --engine-url http://127.0.0.1:8080
```
