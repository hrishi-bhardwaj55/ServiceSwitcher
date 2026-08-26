# Synthetic document rendering

ServicerSwitch renders each canonical account as five realistic mortgage PDFs. The
documents are derived from structured account data after fault injection, so later
extraction and agent evaluations see the same discrepancies recorded in ground
truth.

## Output contract

`make render-documents` writes this stable set for every account:

```text
data/documents/<account_id>/
  old_servicer_statement.pdf
  new_servicer_statement.pdf
  transfer_notice.pdf
  escrow_analysis.pdf
  property_tax_bill.pdf
```

The 300-account corpus therefore contains 1,500 PDFs. Generated PDFs remain ignored
by Git and can always be reproduced from the fixed account seed and renderers.

## Template-family assignment

The numeric account identifier is assigned through a five-slot cycle. Slots 1 and 2
use Family A, slots 3 and 4 use Family B, and slot 5 uses Family C. This yields an
exact 120/120/60 split while distributing every consecutive 40-case finding bucket
across all families.

| Family | Accounts | Layout | Date style | Page behavior |
|---|---:|---|---|---|
| A | 120 (40%) | Modern single column; labels left of values | Full month names | Statements and escrow analyses use two pages; notices and tax bills use one |
| B | 120 (40%) | Dense legacy layout; two-column fields and tabular history | Numeric dates | Every document is a compact single page |
| C | 60 (20%) | Detail-first layout; summary box and values above labels | Abbreviated month names | Every document places detail on page 1 and the summary on page 2 |

Family C is the held-out extraction set. Code, prompts, few-shot examples, and
heuristics under `apps/ai/` may not refer to it. `make check-heldout-isolation`
enforces this boundary in CI with a case-insensitive source scan.

## Document contents

- Old-servicer statements identify the final pre-transfer payment, transfer escrow
  balance, and recent escrow activity.
- New-servicer statements identify the first post-transfer payment, received escrow
  balance, shortage installment, and post-transfer activity.
- Transfer notices identify both servicers, the effective transfer date, and the
  payment cutover dates.
- Escrow analyses contain all stated estimates and payment fields plus a 12-month
  projected trial balance.
- Property-tax bills identify the authority, tax year, annual amount, parcel
  reference, and installment due dates.

All PDFs carry a prominent synthetic-document disclaimer and use built-in PDF fonts
so they render consistently without platform font files.

## Validation

Run the full acceptance gate with:

```bash
make validate-documents
```

The validator opens every PDF with pypdf, rejects encryption, checks the exact page
count for its family and document type, verifies the family metadata, extracts text
from every page, and asserts the account's required canonical values are present.
It also rejects unexpected PDF files under generated account directories.

Rendering tests cover one account from each family across all five document types,
the exact corpus split, distinguishable page structures, and both passing and
failing held-out-isolation scans. Representative output from each family is also
rendered to PNG with Poppler and visually reviewed for clipping, collisions,
legibility, and page order before the chunk is accepted.
