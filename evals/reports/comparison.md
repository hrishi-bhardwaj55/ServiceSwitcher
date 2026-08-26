# Agent versus naive baseline

Both systems use `gpt-5.4-mini` and the same 300 labeled audits. Correctness is
scored directly against ground truth. The baseline makes one long-context call over
PDF text; the agent uses extraction, deterministic reconciliation, retrieval, and
bounded tools.

| Metric | Agent | Naive baseline |
|---|---:|---:|
| Precision | 100.00% | 20.28% |
| Recall | 100.00% | 36.00% |
| F1 | 100.00% | 25.95% |
| Exact finding-set task success | 100.00% | 16.67% |
| Clean-case false-positive rate | 0.00% | 75.00% |
| Clean-but-tricky false-positive rate | 0.00% | 87.50% |
| Mean model cost per audit | $0.001730 | $0.003795 |
| Latency p50 | 2.320s | 3.624s |
| Latency p95 | 5.632s | 7.721s |

The agent cost covers investigator tokens and excludes embeddings and cached C8
extraction calls. Baseline cost covers its single provider call. See the underlying
agent and baseline reports for scope and limitations.
