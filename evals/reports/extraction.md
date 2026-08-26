# Extraction evaluation

Model-backed fallback: `gpt-5.4-mini`. Metrics are kept separate for development and
held-out layouts; they are never pooled into a single headline number.

| Metric | In-distribution (A/B) | Held-out (Family C) |
|---|---:|---:|
| Accounts | 240 | 60 |
| Documents | 1200 | 300 |
| Document classification | 100.00% | 100.00% |
| Field extraction | 100.00% | 93.04% |
| Citation (page) accuracy | 100.00% | 78.14% |
| LLM fallback trigger rate | 0.00% | 100.00% |
