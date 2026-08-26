# Synthetic account generation

The C2 generator creates the clean canonical data on which later document, fault,
engine, and evaluation chunks depend. It is deterministic, uses decimal arithmetic
throughout, and emits one JSON file per mortgage account.

## Commands and outputs

From the repository root:

```bash
make generate-accounts
make validate-accounts
```

The first command creates 300 files in `data/accounts/` with seed `20250825`. The
second loads those files through the canonical Pydantic contract and prints:

```text
Validated 300/300 accounts: all invariants hold
```

Both commands accept direct Python equivalents for environments without GNU Make:

```bash
python -m data.generator.generate --output data/accounts --count 300 --seed 20250825
python -m data.generator.validate --input data/accounts --expected-count 300
```

Generated account files are ignored by Git. Repeating the default generation is
idempotent and byte-for-byte stable. The writer uses an atomic replacement for each
file and removes only stale files matching `account-*.json` in the selected output
directory.

## Corpus shape

Every account contains:

- a fixed-rate, fully amortizing 15- or 30-year mortgage;
- exactly 18 monthly payments beginning on January 1, 2024;
- exactly one servicing transfer on payment month 6 through 12;
- a signed, chronologically chained escrow ledger;
- 2024 and 2025 tax bills using annual, semiannual, or quarterly due dates;
- two annual homeowners-insurance policies;
- an origination analysis plus old- and new-servicer transfer analyses.

Across 300 accounts, original principal ranges from $180,000 to $750,000, annual
rate from 3.0% to 7.5%, annual tax from $2,400 to $14,000, and annual insurance from
$900 to $4,200. Exactly 60 accounts—20% of the corpus—contain a legitimate 40%–55%
tax reassessment visible in the 2025 bill. The remaining accounts preserve their
tax projection.

All monetary values are produced with `Decimal`, rounded half-up to cents, and
serialized as JSON strings. Binary floating point is rejected by the generator's
money helper.

## Timeline conventions

Payments post on the first day of each month. Tax installments post on the 15th of
their due months, and insurance posts on April 20. The ledger begins with an
explicit opening-balance adjustment on the day before origination.

The transfer occurs on a payment date. A zero-dollar `ADJUSTMENT` marker is ordered
before that day's deposit. The old-servicer analysis dated the preceding day and
the new-servicer analysis dated on transfer both use the marker's balance. This
makes the continuity requirement explicit while retaining one uninterrupted
ledger.

An analysis on the first of a month projects that month plus the next eleven. An
analysis later in a month begins with the following month. Each projection adds the
base monthly escrow before subtracting that month's tax or insurance disbursements,
matching the domain model.

## Independent validation

The validator does not import the generator's financial helpers. It independently
recomputes and checks:

1. payment component totals;
2. monthly interest and scheduled principal;
3. iterative and closed-form principal balances to the cent;
4. chronological signed ledger chaining;
5. one escrow deposit matching every payment;
6. exact tax and insurance installment dates and amounts;
7. servicing-period and escrow-balance continuity at the single transfer;
8. projected escrow low balance, cushion, shortage, installment, and new payment;
9. required corpus ranges, schedule variants, transfer months, and reassessment
   share.

Hypothesis exercises 250 amortization cases and 250 arbitrary signed ledgers per
test run. Mutation tests also prove that component, balance, due-date, and transfer
corruptions are rejected. These tests and the full 300-account validation run under
`make verify` in CI.
