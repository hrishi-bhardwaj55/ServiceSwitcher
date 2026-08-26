# Naive long-context baseline

Model: `gpt-5.4-mini`. One structured provider call per audit over concatenated text from
all five PDFs. No tools, reconciliation engine, retrieval, or LLM judge are used.

| Metric | Result |
|---|---:|
| Cases | 300 |
| Precision | 20.28% |
| Recall | 36.00% |
| F1 | 25.95% |
| Exact finding-set task success | 16.67% |
| Clean-case false-positive rate | 75.00% |
| Clean-but-tricky false-positive rate | 87.50% |
| Mean model cost per audit | $0.003795 |
| Latency p50 / p95 | 3.624s / 7.721s |
| Execution failures | 0 |
