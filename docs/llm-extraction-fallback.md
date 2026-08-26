# Model-backed extraction fallback

C8 adds a provider-neutral fallback around the deterministic C7 extractor. It is
confidence-gated: model calls are made only when document classification is below
its threshold or an expected field is missing or below its field-confidence
threshold.

## Provider boundary

`apps/ai/app/llm/` defines a small synchronous interface around typed
`LLMExtractionRequest` and `LLMExtractionResponse` models. The repository includes:

- a queued deterministic fake that records every request and fails on unexpected
  calls;
- an OpenAI Responses API adapter using strict JSON Schema structured output;
- environment-only configuration through `LLM_API_KEY`, `LLM_MODEL`, and optional
  `LLM_API_BASE`.

The provider adapter sends `store: false`. PDF text is wrapped in an explicit
`UNTRUSTED_DOCUMENT_TEXT` boundary, and system instructions state that document
content is data rather than instructions. The provider must return a one-based page
for each field and may return only explicitly supported values. The implementation
uses the Responses API's JSON Schema output format described in the
[official API reference](https://platform.openai.com/docs/api-reference/responses).

## Fallback and cross-check behavior

The default classification and field thresholds are 0.80 and 0.90. The current A/B
parser clears both, so it makes no fallback calls on the development corpus.

When fallback is needed:

1. only missing or low-confidence field names are requested;
2. model output is validated by Pydantic before use;
3. page numbers outside the source document are rejected;
4. money, rates, dates, and due-date lists pass through the same strict C7
   normalizers;
5. matching deterministic and model values become `CROSS_CHECKED`;
6. disagreements become `CONFLICT`, receive confidence no higher than 0.49, retain
   both alternatives, and set `requires_review`;
7. rejected or still-missing fields also require review.

The unified result records classification source, fallback trigger state, requested
field names, missing and rejected fields, and per-field source/provenance.

## Testing

Normal verification uses only the deterministic fake. Tests prove that:

- high-confidence fields do not call the provider;
- missing fields are filled and normalized;
- disagreements are preserved and surfaced for correction;
- invalid values and pages are rejected;
- unknown document text can be classified through fallback;
- the real adapter sends strict structured-output configuration and untrusted-text
  delimiters through a fake HTTP transport.

One `llm`-marked integration test calls the configured real provider. `make verify`
and `make test-extraction` explicitly exclude this marker.

## Honest evaluation gate

`make eval-extraction` requires real `LLM_API_KEY` and `LLM_MODEL` process
environment variables. (Docker Compose reads `.env`; the local runner does not.) It evaluates
all 300 accounts but reports two separate columns: 240 A/B accounts and 60 held-out
accounts. The report includes document classification, exact field accuracy, page
citation accuracy, and fallback trigger rate. `evals/reports/calibration.md` groups
field confidence into five buckets and compares mean confidence with observed exact
accuracy.

The canonical C8 reports have not been generated because this workspace has no
model credentials. Fake-client test results are deliberately not promoted as model
accuracy. Once credentials are supplied, run:

```bash
make eval-extraction
```

Only after that real run passes and both reports are reviewed should C8 be marked
complete or merged to `main`.
