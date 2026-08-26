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

## Deterministic extraction baseline

`evals/runners/deterministic_extraction_eval.py` evaluates keyword classification
and label-proximity extraction separately for Families A and B. It reports overall
and per-field accuracy plus page/bounding-box provenance coverage:

```bash
make eval-extraction-deterministic
```

The current 1,200-document, 4,080-field result is recorded in
`evals/reports/extraction_deterministic.md`. The runner excludes the held-out
template set; that comparison begins only with the fallback evaluation chunk.

## Model-backed extraction evaluation

`evals/runners/extraction_eval.py` evaluates the confidence-gated provider fallback
and keeps the development and held-out cohorts separate. It reports classification,
field, page-citation, and fallback-trigger metrics, then writes confidence calibration
by cohort:

```bash
LLM_API_KEY=... LLM_MODEL=... make eval-extraction
```

This command intentionally requires a real configured provider. The deterministic
fake is limited to tests; its scripted output is never written as the canonical
accuracy report.
