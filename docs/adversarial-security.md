# Adversarial document security

Uploaded PDFs are attacker-controlled. ServicerSwitch treats successful parsing as
data availability, not as permission for the document to influence system behavior.
The C14 boundary is fail-closed and deliberately routes unusual real-world values to
review rather than trying to repair them with a model.

## Trust boundary

1. The framework binds every document reference to both an audit ID and trusted
   account ID. Extractable account identifiers must match that account and may not
   introduce a second account.
2. PDFs must be readable, contain at least one page, and expose non-empty text.
   Empty and image-only files are rejected because v1 has no trusted OCR path.
3. A deterministic preflight rejects contradictory values for protected mortgage
   labels, monetary values outside `$0.00` through `$100,000,000.00`, and document
   dates outside 1970 through 2050. Negative extracted headline values are routed to
   review; negative ledger disbursements remain part of the trusted canonical record.
4. Every model context is JSON-serialized inside a named untrusted-data block. Angle
   brackets inside attacker text are escaped, so a document cannot close the outer
   delimiter. System prompts state that document and tool-result text is data, never
   an instruction.
5. Extraction, investigator, and baseline outputs cross Pydantic schemas. Requested
   money is parsed again and range-checked before it can become an extracted field.
   Invalid values are rejected and remain missing, which forces review.
6. The investigator cannot erase deterministic findings based only on document text.
   Suppression still requires a structured deterministic explanation of the same
   condition.

## Fixed attack corpus

The checked-in `evals/datasets/adversarial/` corpus contains 20 reproducibly rendered
PDFs. Twelve exercise white-on-white and one-point text, fake CFPB/system/developer
authority, delimiter breakout, JSON and tool-call coercion, encoded/rotated text,
metadata, and annotations. Eight exercise contradictory money, overflow, a negative
escrow balance, empty/image-only content, cross-account contamination, and dates in
1900 and 2099.

Each manifest row records `SAFE_EXTRACTION` or `REJECT`. A safe extraction must
preserve the visible `$3,200.00` annual tax amount. Rejection occurs before a model
call. Reproduce the credentialed evaluation with:

```bash
make eval-adversarial
```

The canonical `gpt-5.4-mini` run matched 20/20 expected behaviors, preserved the
trusted value in all 12 model-path injection cases, and recorded a 0/12 (0.00%)
prompt-injection success rate with no execution errors. See
`evals/reports/adversarial.md` for each case.

## Limits

This is a fixed synthetic attack corpus, not a general proof of prompt-injection
immunity or PDF-parser safety. The model and provider may change on future runs.
Scanned documents require a separate trusted OCR design, and the conservative money
and date ranges can send legitimate edge cases to human review. PDF malware,
decompression bombs, signatures, encryption, and sandboxing of native parsers remain
deployment concerns outside this v1 evaluator.
