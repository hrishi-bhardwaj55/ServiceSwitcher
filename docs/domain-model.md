# Mortgage and escrow domain model

This document defines the financial model used by ServicerSwitch. It is the
reference for synthetic data, deterministic reconciliation, PDF extraction, and
evaluation. Monetary calculations use decimal arithmetic, round to cents using
half-up rounding, and never use binary floating point.

ServicerSwitch audits supplied records for internal consistency. It does not make
legal compliance determinations or provide individualized legal advice.

## Source hierarchy and conventions

The implementation follows the project's deliberately simplified model, grounded
in these primary sources:

- [12 CFR § 1024.17](https://www.consumerfinance.gov/rules-policy/regulations/1024/17/)
  governs escrow limits, aggregate analysis, transfers, shortages, and surpluses.
- [CFPB mortgage-servicing FAQs](https://www.consumerfinance.gov/compliance/compliance-resources/mortgage-resources/mortserv/mortgage-servicing-faqs/)
  summarize the required statement fields and analysis concepts.
- [12 CFR § 1024.33](https://www.consumerfinance.gov/rules-policy/regulations/1024/33/)
  governs servicing-transfer notices and payment treatment around a transfer.

The regulation or mortgage documents may require a cushion lower than the maximum.
Version 1 uses the maximum permitted cushion specified by the build specification:
one-sixth of estimated annual escrow disbursements. The engine's result is therefore
an audit comparison under this declared model, not a legal conclusion.

Dates are ISO 8601 (`YYYY-MM-DD`). Amounts are signed from the escrow account's
perspective: deposits are positive and tax or insurance disbursements are negative.
Unless a calculation says otherwise, round only its final result to cents.

## Mortgage balance and principal-and-interest payment

A level-payment, fully amortizing mortgage separates the monthly payment into:

- principal, which reduces the outstanding balance;
- interest, the cost for the current month's outstanding principal; and
- escrow, money collected for scheduled property charges.

For original principal `P`, nominal annual rate `annual_rate`, and term `n` in
months, define the monthly rate `r` and monthly principal-and-interest payment `M`:

```text
r = annual_rate / 12
M = P × r × (1 + r)^n / ((1 + r)^n - 1)
```

Round `M` to cents, half-up. For a zero-rate loan, use `M = P / n` to avoid division
by zero. Each scheduled month uses:

```text
interest_t = round(opening_principal_t × annual_rate / 12, 2)
principal_t = M - interest_t
closing_principal_t = opening_principal_t - principal_t
```

The final scheduled principal component absorbs any cent-level rounding remainder.
For example, a $300,000, 30-year loan at 6.00% has:

```text
r = 0.06 / 12 = 0.005
n = 360
M = 300000 × 0.005 × 1.005^360 / (1.005^360 - 1)
  = 1798.651575...
  = $1,798.65 per month
```

## Escrow account

An escrow account holds the part of a borrower's payment intended for property
taxes, insurance premiums, and other allowed property charges. ServicerSwitch v1
models property tax and homeowners insurance only.

### Annual estimate and base monthly escrow

Let `D` be the estimated disbursements during the next 12-month computation year:

```text
D = estimated annual property tax + estimated annual insurance
base_monthly_escrow = round(D / 12, 2)
permitted_cushion = round(D / 6, 2)
```

The one-twelfth collection limit and one-sixth maximum cushion come from
[12 CFR § 1024.17(c)(1)(ii) and (c)(5)](https://www.consumerfinance.gov/rules-policy/regulations/1024/17/).
The one-sixth cushion is equivalent to two months of the unrounded annual estimate.

### Aggregate trial-balance projection

Aggregate accounting analyzes the escrow account as a whole, as required by
[12 CFR § 1024.17(c)(4) and (d)](https://www.consumerfinance.gov/rules-policy/regulations/1024/17/).
Starting with the current balance, project 12 chronological monthly balances:

1. Add the base monthly escrow deposit.
2. Subtract every estimated disbursement due in that month.
3. Record the resulting month-end balance.
4. Let `L` be the lowest of the 12 recorded balances.

For v1, a disbursement is applied in its due month and monthly deposits precede
same-month disbursements. Generated data and the engine use this ordering
consistently. The regulation requires estimated disbursements on or before the
deadline that avoids a penalty and prohibits pre-accrual; see
[12 CFR § 1024.17(d)(1) and (k)](https://www.consumerfinance.gov/rules-policy/regulations/1024/17/).

### Shortage, surplus, and deficiency

The v1 comparison model derives shortage or surplus from the projected low point:

```text
if L < permitted_cushion:
    shortage = permitted_cushion - L
    surplus = 0
elif L > permitted_cushion:
    shortage = 0
    surplus = L - permitted_cushion
else:
    shortage = 0
    surplus = 0
```

A shortage means the current balance is below its target at analysis time; a
surplus means it is above its target. A deficiency is distinct: it is an actual
negative escrow balance. These definitions are summarized in the
[CFPB mortgage-servicing FAQs](https://www.consumerfinance.gov/compliance/compliance-resources/mortgage-resources/mortserv/mortgage-servicing-faqs/).

ServicerSwitch defaults to repaying a shortage over 12 months:

```text
shortage_monthly = round(shortage / 12, 2)
new_monthly_payment =
    principal_and_interest + base_monthly_escrow + shortage_monthly
```

When equal rounded installments do not sum exactly to the shortage, the final
installment absorbs the remaining cents. Regulation X permits at least a 12-month
repayment schedule for the shortage cases described in
[12 CFR § 1024.17(f)(3)](https://www.consumerfinance.gov/rules-policy/regulations/1024/17/).
The regulation also permits other treatment in some cases; the 12-month convention
is the declared v1 comparison baseline.

For a current borrower, a surplus of at least $50 is refunded within 30 days of the
analysis. A surplus under $50 may be refunded or credited to the next year's escrow
payments under
[12 CFR § 1024.17(f)(2)](https://www.consumerfinance.gov/rules-policy/regulations/1024/17/).

### Worked example 1: cushion and shortage

Assume the account begins the computation year with $1,200.00. Estimated annual tax
is $4,800.00, paid as $2,400.00 installments in June and December. Estimated annual
insurance is $1,200.00, paid in March.

```text
D = 4800.00 + 1200.00 = $6,000.00
base monthly escrow = 6000.00 / 12 = $500.00
permitted cushion = 6000.00 / 6 = $1,000.00
```

The projected trial balance is:

| Month | Opening | Deposit | Disbursement | Ending |
|---|---:|---:|---:|---:|
| January | $1,200.00 | $500.00 | $0.00 | $1,700.00 |
| February | $1,700.00 | $500.00 | $0.00 | $2,200.00 |
| March | $2,200.00 | $500.00 | -$1,200.00 insurance | $1,500.00 |
| April | $1,500.00 | $500.00 | $0.00 | $2,000.00 |
| May | $2,000.00 | $500.00 | $0.00 | $2,500.00 |
| June | $2,500.00 | $500.00 | -$2,400.00 tax | $600.00 |
| July | $600.00 | $500.00 | $0.00 | $1,100.00 |
| August | $1,100.00 | $500.00 | $0.00 | $1,600.00 |
| September | $1,600.00 | $500.00 | $0.00 | $2,100.00 |
| October | $2,100.00 | $500.00 | $0.00 | $2,600.00 |
| November | $2,600.00 | $500.00 | $0.00 | $3,100.00 |
| December | $3,100.00 | $500.00 | -$2,400.00 tax | $1,200.00 |

The lowest projected balance `L` is $600.00:

```text
shortage = 1000.00 - 600.00 = $400.00
shortage repayment = 400.00 / 12 = $33.33 per month, rounded
```

Eleven payments of $33.33 plus a final payment of $33.37 repay exactly $400.00. If
principal and interest is $1,510.10, the usual new monthly payment is:

```text
$1,510.10 + $500.00 + $33.33 = $2,043.43
```

This example is sufficient to reproduce the v1 engine's monthly escrow, cushion,
trial low, shortage, and ordinary shortage installment by hand.

## Servicing transfer continuity

A servicing transfer changes the company administering the loan, not the underlying
loan terms. The new servicer must treat transferred escrow shortages, surpluses, and
deficiencies under the same escrow procedures; see
[12 CFR § 1024.17(e)](https://www.consumerfinance.gov/rules-policy/regulations/1024/17/).
Transfer notices also state that the transfer does not change loan terms other than
terms directly related to servicing under
[12 CFR § 1024.33(b)(4)(vi)](https://www.consumerfinance.gov/rules-policy/regulations/1024/33/).

The audit therefore treats the escrow ledger as continuous:

```text
expected_new_opening_balance =
    old_servicer_closing_balance
    + deposits after the old closing timestamp and through the new opening timestamp
    + disbursements and adjustments in that same interval
```

Because disbursements are negative, the single addition formula handles both money
in and money out. The new servicer's reported opening balance is compared with this
expected balance. Timing evidence matters: a tax payment between statements can
legitimately explain a different displayed balance.

## Payment-change decomposition

An observed payment change is decomposed into independently supported components:

```text
payment_change = new_total_payment - old_total_payment
pi_change = new_principal_and_interest - old_principal_and_interest
tax_change_monthly = (new_annual_tax - old_annual_tax) / 12
insurance_change_monthly =
    (new_annual_insurance - old_annual_insurance) / 12
shortage_change_monthly = new_shortage_repayment_monthly

residual = payment_change
           - pi_change
           - tax_change_monthly
           - insurance_change_monthly
           - shortage_change_monthly
```

Each component is rounded to cents, half-up, before calculating the residual. The
engine preserves the full decomposition even when the residual is explained.

### Worked example 2: fully explained payment increase

Assume a fixed-rate loan with monthly principal and interest of $1,450.00. Annual
property tax increases from $6,000.00 to $9,000.00 after a reassessment, annual
insurance increases from $1,200.00 to $1,440.00, and the new analysis collects a
$480.00 shortage over 12 months.

| Component | Old monthly | New monthly | Change |
|---|---:|---:|---:|
| Principal and interest | $1,450.00 | $1,450.00 | $0.00 |
| Property tax escrow | $500.00 | $750.00 | $250.00 |
| Insurance escrow | $100.00 | $120.00 | $20.00 |
| Shortage repayment | $0.00 | $40.00 | $40.00 |
| **Total payment** | **$2,050.00** | **$2,360.00** | **$310.00** |

```text
residual = 310.00 - 0.00 - 250.00 - 20.00 - 40.00 = $0.00
```

The increase is fully explained by documented components. A large increase is not,
by itself, a discrepancy; the unexplained residual is what matters.

## Audit findings

All finding calculations are deterministic once the structured inputs are known.
The stated tolerances are product rules designed to avoid false positives.

| Finding | Deterministic comparison | Fires when |
|---|---|---|
| `ESCROW_BALANCE_MISMATCH` | Expected continuous balance versus new-servicer opening balance | Absolute difference is greater than $1.00 |
| `PROPERTY_TAX_PROJECTION_MISMATCH` | Projected annual tax versus tax-bill annual amount | Absolute difference is greater than the greater of $25.00 or 1% of the tax-bill amount |
| `ESCROW_SHORTAGE_CALCULATION_ERROR` | Recomputed shortage versus stated shortage | Absolute difference is greater than $10.00 |
| `DUPLICATE_TAX_DISBURSEMENT` | Two tax disbursements with the same payee and type, no more than 45 days apart | Amounts differ by no more than 2% |
| `UNEXPLAINED_PAYMENT_INCREASE` | Payment-change residual from the decomposition above | Residual is greater than the greater of $10.00 or 2% of the payment increase |

Exactly-on-tolerance differences do not fire. A payment residual within tolerance
produces an explicit `EXPLAINED` outcome with the full decomposition.

Severity is derived from impact, not document language:

- `HIGH`: monthly impact is at least $100 or total impact is at least $1,000;
- `MEDIUM`: monthly impact is at least $25 and neither high condition applies;
- `LOW`: all smaller impacts.

## Document structures

Every extracted field carries `document_id`, one-based PDF page, field name, value,
bounding box, and extraction confidence. The five supported document types provide
different views of the same account.

### Old servicer statement

Purpose: establish the last known state before transfer.

Expected structure:

- statement identity: document title, servicer name, account identifier, statement
  date, payment due date;
- loan summary: current principal, annual interest rate, total payment due;
- payment breakdown: principal, interest, escrow, and total;
- escrow summary or transaction activity: deposits, tax/insurance disbursements,
  payees, dates, and closing escrow balance;
- transaction history sufficient to locate legitimate activity near transfer.

The closing escrow balance and dated activity are the primary continuity evidence.

### New servicer statement

Purpose: establish the state accepted by the new servicer and the post-transfer
payment.

Expected structure:

- statement identity and new-servicer name;
- current principal and interest rate;
- opening or earliest reported escrow balance;
- current principal, interest, escrow, shortage-repayment, and total payment amounts;
- dated post-transfer transactions and their application.

The opening balance is compared only after adjusting for documented interim ledger
activity.

### Transfer notice

Purpose: establish who transferred servicing and when.

Expected structure:

- old and new servicer names and contact information;
- effective transfer date;
- last date the old servicer accepts payments and first date the new servicer
  accepts payments;
- account identifier and required transfer disclosures.

The effective date anchors the continuity window and assigns transactions to the
correct servicing period.

### Escrow analysis

Purpose: explain the servicer's projection and proposed payment.

Expected structure:

- servicer and analysis date;
- projected annual property tax and insurance;
- current escrow balance and 12-month projected trial balance;
- selected cushion or target low balance;
- stated shortage, surplus, or deficiency and its treatment;
- base monthly escrow, monthly shortage installment, and new total payment;
- anticipated disbursement amounts, payees, and due dates.

Regulation X's required initial-statement concepts include the payment, escrow
portion, itemized anticipated disbursements, dates, selected cushion, and trial
balance; see
[12 CFR § 1024.17(g)(1)](https://www.consumerfinance.gov/rules-policy/regulations/1024/17/).

### Property tax bill

Purpose: provide the taxing authority's amount and schedule independently of the
servicer projection.

Expected structure:

- authority and parcel/account identifier;
- tax year;
- annual amount due;
- installment amounts and due dates;
- adjustments, exemptions, or reassessment notes when present.

The annual amount is the comparison value. Installment lines provide timing evidence
and help distinguish duplicate payments from distinct legitimate disbursements.

## Canonical relationships and invariants

The structured account must preserve these relationships:

- each payment total equals principal plus interest plus escrow;
- interest equals outstanding principal times annual rate divided by 12, rounded to
  cents;
- principal follows the amortization schedule;
- each ledger balance equals its predecessor plus the signed transaction amount;
- payment escrow components match corresponding ledger deposits;
- tax and insurance disbursements match known due dates;
- the escrow ledger remains continuous through servicing transfer;
- an escrow analysis can be reproduced from its balance, estimates, and dates;
- every conclusion cites the source document page, field, and value.

These invariants are stricter than extraction confidence. Low-confidence or
conflicting document values are surfaced for correction or investigation rather
than silently forced to fit the model.
