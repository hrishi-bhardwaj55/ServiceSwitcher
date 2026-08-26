# Deterministic extraction evaluation

This report measures keyword classification and label-proximity field extraction on
the two development template families. No LLM or held-out documents are used.

## Corpus

| Family | Accounts | Documents | Expected fields |
|---|---:|---:|---:|
| A | 120 | 600 | 2040 |
| B | 120 | 600 | 2040 |
| Overall | 240 | 1200 | 4080 |

## Summary

| Metric | Family A | Family B | Overall | Floor |
|---|---:|---:|---:|---:|
| Document classification | 100.00% | 100.00% | 100.00% | 99.00% |
| Field extraction | 100.00% | 100.00% | 100.00% | 98.00% |
| Page and bounding-box provenance coverage | 100.00% | 100.00% | 100.00% | 100.00% |

## Per-field accuracy

| Field | Family A | Family B | Overall |
|---|---:|---:|---:|
| `annual_tax_amount` | 100.00% (120/120) | 100.00% (120/120) | 100.00% (240/240) |
| `due_dates` | 100.00% (120/120) | 100.00% (120/120) | 100.00% (240/240) |
| `escrow_balance` | 100.00% (240/240) | 100.00% (240/240) | 100.00% (480/480) |
| `interest_rate` | 100.00% (240/240) | 100.00% (240/240) | 100.00% (480/480) |
| `monthly_payment` | 100.00% (240/240) | 100.00% (240/240) | 100.00% (480/480) |
| `new_servicer_name` | 100.00% (120/120) | 100.00% (120/120) | 100.00% (240/240) |
| `old_servicer_name` | 100.00% (120/120) | 100.00% (120/120) | 100.00% (240/240) |
| `principal_balance` | 100.00% (240/240) | 100.00% (240/240) | 100.00% (480/480) |
| `projected_annual_insurance` | 100.00% (120/120) | 100.00% (120/120) | 100.00% (240/240) |
| `projected_annual_tax` | 100.00% (120/120) | 100.00% (120/120) | 100.00% (240/240) |
| `stated_shortage` | 100.00% (120/120) | 100.00% (120/120) | 100.00% (240/240) |
| `tax_authority` | 100.00% (120/120) | 100.00% (120/120) | 100.00% (240/240) |
| `transfer_date` | 100.00% (120/120) | 100.00% (120/120) | 100.00% (240/240) |

**Acceptance verdict: PASS.**
