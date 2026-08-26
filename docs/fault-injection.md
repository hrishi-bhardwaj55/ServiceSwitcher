# Fault injection and ground truth

C3 converts the deterministic clean account corpus into a labeled reconciliation
dataset. Every transformation is reproducible and operates on typed canonical
models. Faulted records contain exactly one detectable condition; clean records
contain none.

## Commands

From the repository root:

```bash
make inject-faults
make validate-ground-truth
```

`inject-faults` regenerates the clean 300-account source first, writes the case
accounts back to `data/accounts/`, and writes one label per line to
`data/ground_truth/cases.jsonl`. Both locations are generated and ignored by Git.

The direct Python equivalents are:

```bash
python -m data.generator.generate --output data/accounts --count 300 --seed 20250825
python -m data.faults.inject --input data/accounts --output data/accounts --ground-truth data/ground_truth/cases.jsonl
python -m data.faults.validate --accounts data/accounts --ground-truth data/ground_truth/cases.jsonl
```

Successful validation prints:

```text
Validated 300/300 ground-truth cases: 200 faulted, 60 clean, 40 clean-but-tricky
```

## Bucket assignment

Case and account identifiers remain aligned and stable:

| Cases | Bucket | Condition |
|---|---|---|
| 0001–0040 | Faulted | `ESCROW_BALANCE_MISMATCH` |
| 0041–0080 | Faulted | `PROPERTY_TAX_PROJECTION_MISMATCH` |
| 0081–0120 | Faulted | `ESCROW_SHORTAGE_CALCULATION_ERROR` |
| 0121–0160 | Faulted | `DUPLICATE_TAX_DISBURSEMENT` |
| 0161–0200 | Faulted | `UNEXPLAINED_PAYMENT_INCREASE` |
| 0201–0260 | Clean | No finding |
| 0261–0300 | Clean but tricky | Eight reassessments, ten insurance jumps, ten distinct-authority payments, and twelve fully explained increases |

The tricky cohort is intentionally heterogeneous:

- legitimate property-tax reassessments increase at least 40%;
- legitimate annual insurance premiums increase 60%, with analyses and deposits
  recomputed;
- two scheduled tax payments to different authorities occur exactly 50 days apart,
  outside the 45-day duplicate rule and with different payees;
- documented tax, insurance, and shortage components fully explain a large payment
  increase.

The canonical §6 account has one account-wide `annual_rate` and no rate-history
field. Encoding an adjustable-rate event would therefore require inventing evidence
or weakening the C2 interest invariant. The fourth cohort preserves the intended
false-positive test—a large but fully decomposed payment increase—without extending
the canonical schema. A future rate-history schema can add an ARM variant without
changing the 200/60/40 contract.

## Single-fault isolation and impact

Each injector updates dependent values needed to isolate its target. For example, a
bad tax projection receives a self-consistent shortage analysis and matching later
deposits, so it does not also become a shortage-calculation fault.

| Finding | Injected discrepancy | Total impact | Monthly impact |
|---|---|---:|---:|
| Escrow balance mismatch | New-servicer opening analysis uses a false transfer balance | Absolute balance difference | $0.00 |
| Tax projection mismatch | New projected annual tax differs from 2025 bills | Absolute annual difference | Difference ÷ 12 |
| Shortage calculation error | Stated shortage differs from recomputed shortage | Absolute shortage difference | Difference ÷ 12 |
| Duplicate tax disbursement | Same-payee, same-amount payment repeated after 30 days | Duplicate amount | $0.00 |
| Unexplained payment increase | Undocumented recurring surcharge after transfer | Residual × 12 | Monthly residual |

All calculations use decimal half-up cent rounding. Ground-truth impact fields are
serialized as decimal strings.

## Validation guarantees

The ground-truth validator loads every JSONL record through `GroundTruthCase`, loads
the matching account, and checks:

1. exactly 300 unique cases and accounts;
2. bucket counts of 200 faulted, 60 clean, and 40 clean-but-tricky;
3. exactly 40 labels for each of the five finding types;
4. one oracle finding for every faulted case, with exact total and monthly impact;
5. no oracle findings and full C2 invariant validity for all 100 clean cases;
6. the claimed tricky condition is materially present in every tricky record;
7. faulted cases include the document labels needed for later evidence rendering.

Tests round-trip all 40 variants of every injector, verify source accounts remain
immutable, compare repeated builds byte-for-byte, exercise disk serialization, and
prove a one-cent incorrect label is rejected.
