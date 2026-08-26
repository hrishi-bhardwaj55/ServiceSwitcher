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

The canonical `gpt-5.4-mini` run records 100% classification for both cohorts. A/B
retains 100% field and page accuracy with no fallback. Held-out Family C records
93.04% exact fields, 78.14% exact pages, and a 100% fallback rate. Full results are in
`evals/reports/extraction.md` and `evals/reports/calibration.md`.

Successful provider responses are appended to the ignored
`data/traces/extraction_llm_cache.jsonl` file. The cache key covers the provider base,
model, prompt-contract version, and complete typed request, allowing interrupted
evaluations to resume without presenting cached fake output as a real model result.

## Regulation retrieval evaluation

`evals/runners/rag_eval.py` compares the only two C9 retrieval strategies over 25
required-source questions: vector-only search and vector plus PostgreSQL full-text
search fused with reciprocal rank fusion. Configure an embedding key, run the
ingestion, and then evaluate both strategies side by side:

```bash
make ingest-kb
make eval-rag
```

`EMBEDDING_API_KEY` may be omitted when `LLM_API_KEY` is already configured. The
canonical 512-dimensional `text-embedding-3-small` run is recorded in
`evals/reports/rag.md`; the measured production choice is in `docs/evals.md`.

## End-to-end investigator evaluation

`evals/runners/agent_eval.py` runs the complete audit graph over all 300 cases. It
loads five PDFs per case, uses the C8 confidence-gated extraction fallback, queries
the measured hybrid retriever, calls the deterministic engine, and evaluates the
bounded investigator. Correctness is compared directly with ground truth; no LLM
judge is used.

```bash
make eval-all
```

The canonical run is serialized to avoid measuring provider concurrency limits.
Tool expectations in `evals/datasets/agent.jsonl` identify the primary evidence
tool for each finding category. The report includes overall and faulted-only exact
tool-set accuracy, extra calls, steps, tool-error recovery, model-error cases, review
rate, investigator token cost, and latency.

The 300-case `gpt-5.4-mini` result is in `evals/reports/agent.md`. Finding F1 is
100% with zero clean-case false positives, while automated success is 40.00% because
60.00% of cases route to human review. The report explicitly notes that the engine
reconciles the canonical audit record; this is not a PDF-only ledger reconstruction
benchmark.
