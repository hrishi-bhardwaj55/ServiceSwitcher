# Deterministic reconciliation engine

C4 implements the financial trust boundary as a stateless Java 21 / Spring Boot 3
service. It accepts a canonical account, applies exact `BigDecimal` calculations,
and returns evidence-shaped findings without calling an LLM or storing data.

## HTTP contract

The engine exposes one audit endpoint in addition to health:

```http
POST /reconcile
Content-Type: application/json

{
  "account": { "...": "canonical MortgageAccount" },
  "transfer_date": "2024-06-01"
}
```

The response is:

```json
{
  "findings": [],
  "payment_decomposition": {
    "payment_change": "310.00",
    "principal_interest_change": "0.00",
    "tax_change_monthly": "250.00",
    "insurance_change_monthly": "20.00",
    "shortage_monthly": "40.00",
    "residual": "0.00",
    "tolerance": "10.00",
    "outcome": "EXPLAINED"
  },
  "engine_version": "1.0.0"
}
```

Jackson uses snake-case field names and accepts the decimal strings emitted by the
Python generator as `BigDecimal`. All money outputs are scaled to cents with
`RoundingMode.HALF_UP`.

## Calculation flow

For each request, the service:

1. identifies the old and new analyses around the supplied transfer date;
2. rebuilds the new analysis's 12-month aggregate escrow trial balance;
3. calculates base escrow, projected low balance, cushion, shortage, and monthly
   shortage installment;
4. decomposes the first post-transfer payment against the final pre-transfer
   payment;
5. runs a fixed registry containing one detector for each supported finding type;
6. returns findings, full payment decomposition, and engine version.

Multiple tax authorities are handled proportionally when a servicer projection
differs from the bills and exactly when the projected total matches them. Insurance
uses the applicable annual renewal month. Monthly deposits precede same-month
disbursements, matching the documented generator convention.

## Detectors and boundaries

All comparisons are strict above their tolerance. An exact-boundary difference is
not a finding.

| Detector | Fires when |
|---|---|
| Escrow balance mismatch | Absolute old/new transfer-balance difference is greater than $1.00 |
| Property-tax projection mismatch | Difference is greater than the greater of $25.00 or 1% of billed annual tax |
| Escrow shortage calculation error | Stated versus recomputed shortage differs by more than $10.00 |
| Duplicate tax disbursement | Same payee, within 45 days, and amounts differ by no more than 2% |
| Unexplained payment increase | Decomposition residual is greater than the greater of $10.00 or 2% of the increase |

The payment detector always emits an outcome. A residual inside tolerance produces
`EXPLAINED`, not silence, and the response retains every decomposition component.

Severity is impact-derived: `HIGH` for monthly impact of at least $100 or total
impact of at least $1,000, `MEDIUM` for monthly impact of at least $25, and `LOW`
otherwise.

## Tests and architecture guard

Run:

```bash
make test-engine
make verify
```

The JUnit suite covers a positive, a negative near-miss, and the exact tolerance
boundary for every detector. It also reproduces both hand-worked domain examples,
tests snake-case `POST /reconcile`, and asserts that the runtime dependency path has
no OpenAI, Anthropic, LangChain, or Spring AI client.

A local cross-runtime smoke test submitted representative JSON accounts from every
C3 fault group plus clean and tricky groups. The five fault cases returned their
expected discrepancy and the clean/tricky records returned only `EXPLAINED`.
