# Deterministic engine evaluation

This report measures the reconciliation engine directly against structured account
data. It does not include PDF rendering, extraction, retrieval, or AI behavior.

## Corpus

| Cases | Faulted | Clean (including tricky) | Engine version |
|---:|---:|---:|---|
| 300 | 200 | 100 | `1.0.0` |

## Results

| Metric | Result | Target |
|---|---:|---:|
| Precision | 100.00% | 100.00% |
| Recall | 100.00% | 100.00% |
| F1 | 100.00% | 100.00% |
| Clean-case false-positive rate | 0.00% | 0.00% |
| Financial-impact mean absolute error | $0.0000 | < $0.01 |

Counts: 200 true positives, 0 false
positives, 0 false negatives, and
0/100 clean cases with a false
positive.

**Acceptance verdict: PASS.**
