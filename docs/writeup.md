# What the model should not decide

ServicerSwitch started with a deliberately narrow question: can an agent help a
homeowner understand a mortgage payment change without letting the model perform the
financial accounting? That constraint shaped the system more than the choice of
model, framework, or vector database. The finished project has three results worth
discussing: the deterministic split, the extraction gap on a held-out document
layout, and the comparison with a naive long-context baseline.

## The deterministic split

Mortgage servicing looks like a document-understanding problem, but its decisive
checks are ordinary accounting. An escrow balance either carried across the transfer,
or it did not. A tax projection either matches the issued bill within a defined
tolerance, or it does not. A shortage can be recomputed from a twelve-month trial
balance. A payment increase can be decomposed into principal and interest, tax,
insurance, and shortage installments. Asking a language model to do those operations
would make repeatability and error analysis unnecessarily difficult.

The project therefore places them in a stateless Java service. It accepts typed JSON,
uses exact decimal arithmetic, and returns a decomposition plus one of five finding
types. The service has no database, filesystem access, or model client. This is more
than a code-organization preference. It is a trust boundary: the same financial
record produces the same result regardless of prompt wording, retrieved text, or
provider availability.

The Python service handles the work for which probabilistic behavior is useful. It
classifies PDFs, extracts typed fields with coordinates, retrieves relevant guidance,
and lets one bounded graph node investigate an ambiguous finding. The agent does not
receive a shell, general SQL, a calculator, or arbitrary URLs. It receives eight
purpose-built tools bound to one audit identifier by the framework. Even the public
tool schemas omit `audit_id`, so the model cannot ask to cross an account boundary.

This split also changes the failure policy. A model cannot erase a deterministic
finding merely by declaring it explained. Suppression requires explicit structured
support for that same condition. Missing evidence, repeated tool calls, transport
failure, and budget exhaustion preserve the finding and request human review. That
choice explains an initially surprising pair of evaluation numbers: finding F1 is
100%, while automated task success is only 40%. The system can be correct because it
fails closed, without pretending to be autonomous.

## The held-out layout gap

Synthetic evaluation is easy to overfit accidentally. If every PDF uses the same
labels in the same order, a parser can look impressive while learning almost nothing
about layout variation. ServicerSwitch renders two development families and a third
family that is structurally held out. Family C moves values above labels, puts detail
before summary, uses two pages, changes tables, and abbreviates dates. A CI check
prevents extraction code and prompts from referring to that family.

The result is more useful than a single pooled accuracy number. Document
classification stays at 100% on all families, so the system knows what kind of
document it is seeing. In-distribution field and page accuracy are also 100%. On the
held-out family, however, typed field accuracy falls to 93.04% and page-citation
accuracy to 78.14%, even though the model fallback runs on every document.

That gap identifies the real weakness: provenance generalization, not high-level
classification. It also exposed overconfidence. Some held-out fields reported high
confidence more often than their observed correctness justified. The project keeps
that result instead of tuning thresholds against the test family. Deterministic/model
disagreements retain both alternatives, confidence is capped below the review
threshold, and weak page provenance cannot quietly become a polished UI citation.

The evidence viewer makes this constraint visible. It renders the actual synthetic
PDF page and overlays the cited bounding box. A finding is not just a paragraph of
model prose; it must carry a document, page, field, value, and source coordinates. The
original PDF remains linked beside the render. This makes a citation inspectable by a
person and testable by code.

## The baseline comparison

The most important architectural claim needed a simpler alternative. The naive
baseline receives text from all five PDFs, with page and document delimiters, in one
structured `gpt-5.4-mini` request. It has no extraction pipeline, reconciliation
engine, retrieval, tools, or LLM judge. Both systems run over the same 300 labeled
audits, including 60 clean and 40 clean-but-tricky cases.

The baseline reaches 20.28% precision, 36% recall, and 25.95% F1. It raises at least
one false finding on 75% of all clean cases and 87.5% of the tricky clean cases. The
bounded system reports no false positives on either clean group and preserves every
expected deterministic finding. The baseline is also slower at both measured latency
percentiles and its single call costs about 2.19 times the investigator-only token
cost.

Those cost columns are not perfect whole-system parity. Investigator cost excludes
embeddings and cached extraction calls, while baseline cost covers its complete
request. The agent also reconciles a trusted canonical mortgage record rather than
rebuilding the entire ledger solely from PDF text. The comparison therefore does not
prove a universal advantage for agents or for this exact stack. It shows something
more specific: on this synthetic servicing task, separating document understanding
from deterministic reconciliation sharply reduces both missed faults and invented
faults.

## What remains honest

The data is synthetic, there is no OCR path, and the adversarial suite has only 20
fixed documents. A 0% injection-success rate on twelve attacks is a regression result,
not a security guarantee. The regulation corpus is small and curated. The system has
no multi-tenant authorization or production storage story, and its serialized latency
numbers are not a load test.

Those limits are part of the result. ServicerSwitch is useful as an evaluated system
design, not as a claim that an AI agent should adjudicate a borrower dispute. Its
central lesson is narrower and more durable: use the model where ambiguity is real,
make arithmetic boring, bind tools to the smallest possible scope, and design the
review path before celebrating autonomy.
