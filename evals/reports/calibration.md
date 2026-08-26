# Extraction confidence calibration

Model-backed fallback: `gpt-5.4-mini`. Each row compares mean predicted confidence with
observed exact-value accuracy for expected fields in that confidence bucket.
Missing fields enter the lowest bucket with zero confidence.

| Confidence bucket | In-distribution (A/B) | Held-out (Family C) |
|---|---:|---:|
| 0.0-0.2 | n=0 | n=1; conf 0.00%; acc 0.00% |
| 0.2-0.4 | n=0 | n=0 |
| 0.4-0.6 | n=0 | n=0 |
| 0.6-0.8 | n=0 | n=1; conf 61.00%; acc 0.00% |
| 0.8-1.0 | n=4080; conf 95.14%; acc 100.00% | n=1018; conf 98.22%; acc 93.22% |
