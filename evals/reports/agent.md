# End-to-end investigator evaluation

Model: `gpt-5.4-mini`. Dataset: 300 synthetic audits (200
faulted, 100 clean including 40 clean-but-tricky).
Correctness is scored directly against ground truth; no LLM judge is used.

## Finding quality

| Metric | Result |
|---|---:|
| Precision | 100.00% |
| Recall | 100.00% |
| F1 | 100.00% |
| Task success (exact finding set) | 100.00% |
| Automated task success (exact set, no review) | 40.00% |
| Clean-case false-positive rate | 0.00% |
| Clean-but-tricky false-positive rate | 0.00% |

Counts: 200 true positives, 0 false
positives, 0 false negatives, and 0
execution failures.

## Agent behavior and operations

| Metric | Result |
|---|---:|
| Exact tool-set accuracy | 70.00% |
| Exact tool-set accuracy, faulted cases | 55.00% |
| Unnecessary tool calls per run | 0.983 |
| Average / p95 steps | 1.460 / 4 |
| Failure recovery rate | 100.00% (13/13) |
| Fail-closed model-error cases | 0 |
| Human-review rate | 60.00% |
| Model cost per audit (mean) | $0.001730 |
| Latency p50 / p95 | 2.320s / 5.632s |

Model cost includes investigator input/output tokens priced by the C11 boundary;
embedding calls are not included. A tool call is unnecessary when it is outside the
expected category set or repeats a tool already credited for that run.

## Interpretation and limitations

Finding correctness and automated completion are deliberately separate. The graph
retains deterministic findings whenever evidence, model behavior, or extraction
confidence requires review, so fail-closed cases can be correct without being
autonomous.

Each audit loads all five rendered PDFs and evaluates extraction and evidence, while
the deterministic engine reconciles the synthetic canonical audit record. The
finding metrics therefore evaluate end-to-end orchestration around a trusted
structured record; they do not measure reconstruction of the complete mortgage
ledger from PDFs alone. The canonical run is serialized to avoid provider-concurrency
errors. Latency is local wall time with cached C8 extraction responses and is not a
production load test.
