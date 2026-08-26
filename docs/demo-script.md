# Three-minute demo script

The committed video follows the measured `CASE-0042` tax-projection scenario. Lines
prefixed with `>` are the timed narration/caption script; the bullets describe the
matching screen action. The WebM is intentionally silent because the local Windows
speech runtime was not reliable enough to produce a reproducible audio track.

## 0:00–0:18 — choose a measured scenario

- Show the picker, the four scenarios, and the memory-only upload boundary.
- Select **Tax projection error** and start the audit.

> ServicerSwitch audits mortgage-servicing transfers, but it does not ask a model to
> do mortgage accounting. This picker offers four reproducible synthetic cases and a
> memory-only PDF path. I am choosing the measured tax-projection error. The interface
> is explicit that custom files stay in this browser session and are never persisted.

## 0:18–0:30 — bounded processing

- Show the seven live stages and the completed transition.

> Processing follows seven bounded stages: load, classify, extract and validate,
> reconcile, investigate, validate evidence, and report. This is workflow status, not
> chain-of-thought. Financial reconciliation crosses into a separate stateless Java
> service; only an ambiguous finding can enter the agentic investigation node.

## 0:30–1:08 — understand the payment change

- Hold on the result hero, then scroll through the payment decomposition.
- Stop at the finding and its monthly impact.

> The result is meant to be understandable in under a minute. The servicer projected
> twelve thousand one hundred sixty-five dollars and seventeen cents in annual tax,
> while the issued county bill shows eleven thousand five hundred fifty-two dollars.
> The six hundred thirteen dollar and seventeen cent difference becomes fifty-one
> dollars and ten cents per month. The decomposition proves that principal, interest,
> insurance, and shortage did not change. All of the increase sits in the property-tax
> reserve. That arithmetic is exact decimal code, never model output.

## 1:08–1:28 — inspect the trust record

- Show the finding, high-severity count, documents checked, and trust record.
- Open the finding evidence.

> The dashboard separates the deterministic calculation from the audit finding. It
> reports one high-severity item, the potential impact, and all five checked documents.
> The trust record shows which bounded subsystems ran. Opening evidence moves from a
> summary claim to the source that supports it.

## 1:28–2:13 — verify the source PDFs

- Show the tax-bill page and highlighted `$11,552.00` value.
- Switch to the escrow analysis and its highlighted `$12,165.17` projection.
- Return to the bill.

> This is the actual synthetic PDF page, not re-created model prose. The orange box is
> positioned from page-level extraction coordinates, and the original PDF stays
> linked. The county bill cites eleven thousand five hundred fifty-two dollars. The
> second tab shows the annual escrow analysis and its twelve thousand one hundred
> sixty-five dollar and seventeen cent projection. Every displayable claim carries a
> document, page, field, and typed value. If deterministic and model extraction
> disagree, both alternatives remain and the audit requires review.

## 2:13–2:42 — guidance and a user-controlled action

- Scroll through the Regulation X and CFPB links.
- Show the editable request and copy control.

> Relevant guidance links go to primary CFPB sources. The language says the mismatch
> deserves review; it does not claim that a law was violated. The suggested servicer
> request uses only the cited values. It is editable, and copying it does not send
> anything. The homeowner remains in control of the next action.

## 2:42–3:00 — close on the evidence contract

- Return to the highlighted value and finish on the finding title.

> The central design choice is simple: models handle document ambiguity, while code
> owns arithmetic, tolerances, and finding reproduction. On three hundred labeled
> audits that boundary produced zero clean-case false positives, compared with
> seventy-five percent for one naive long-context call. The full methodology and its
> limits are linked from the numbers-first README.
