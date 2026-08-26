# Deterministic PDF extraction

The C7 extractor establishes a non-AI baseline for document understanding. It uses
PyMuPDF word coordinates, fixed document signatures, strict value normalizers, and
label proximity. It has no model client, network call, prompt, or probabilistic
fallback.

## Pipeline

1. PyMuPDF reads every page as plain text for classification and as word tuples for
   field location. Word tuples carry the text bounding box and block/line indexes.
2. A keyword-signature classifier selects one of the five supported document types.
   It requires a unique winning signature set and rejects ambiguous text.
3. Each document type supplies only its expected field labels. The matcher groups
   words into visual lines and searches for typed values either on the same row to
   the right or immediately below an exact label alias.
4. Property-tax due dates use a column matcher below the `Due Date` table header, so
   annual, semiannual, and quarterly schedules remain a single typed field.
5. Currency, percentages, and dates are parsed by strict normalizers. Values that do
   not match an allowed syntax are rejected rather than guessed.

PyMuPDF documents the `Page.get_text("words")` representation as
`(x0, y0, x1, y1, word, block, line, word)` tuples; the implementation converts
those coordinates into stable one-based page and bounding-box provenance. See the
[official text-extraction appendix](https://pymupdf.readthedocs.io/en/latest/app1.html).

## Typed output

Every extracted field contains:

- a constrained field name;
- a `Decimal`, `date`, text value, or tuple of dates as appropriate;
- a one-based PDF page;
- the value's `x0`, `y0`, `x1`, and `y1` bounding box;
- a confidence in the closed interval from 0 to 1;
- the exact source text passed to the normalizer.

Money remains `Decimal` and percentages normalize to fractional form. For example,
`6.3496%` becomes `Decimal("0.063496")`, matching the canonical account schema.

## Development-set evaluation

Run:

```bash
make eval-extraction-deterministic
```

The target regenerates and validates the 1,500-PDF corpus, runs extraction tests,
then evaluates only the 240 development-layout accounts: 120 Family A and 120
Family B accounts, containing 1,200 documents and 4,080 labeled fields.

The recorded floor is 99% document classification, 98% field extraction, and 100%
provenance coverage. The current report passes all three at 100% for both families,
including every individual field. Results are written to
`evals/reports/extraction_deterministic.md`.

The held-out layouts are not used by this runner or by extractor tests. The existing
source isolation check continues to prevent their name from appearing anywhere
under `apps/ai/`.
