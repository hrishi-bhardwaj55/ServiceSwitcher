# Model configuration and cost boundary

ServicerSwitch defaults to `gpt-5-nano` for model-backed extraction, the bounded
investigator, and future baseline runs. OpenAI documents it as its fastest,
lowest-cost GPT-5 model and lists support for the Responses API, function calling,
and structured outputs, which are the capabilities used by this repository.

As verified against the official model page on 2026-08-27, standard text-token
pricing per one million tokens is $0.05 input, $0.005 cached input, and $0.40 output.
The investigator uses those values for its preflight and measured cost guards. See
the official [`gpt-5-nano` model page](https://developers.openai.com/api/docs/models/gpt-5-nano)
for current pricing, availability, and limits.

## Local configuration

Keep credentials only in the ignored repository-root `.env` file:

```dotenv
LLM_API_KEY=your-key
LLM_MODEL=gpt-5-nano
LLM_API_BASE=https://api.openai.com/v1

# Optional overrides; empty values reuse the shared settings.
AGENT_API_KEY=
AGENT_MODEL=gpt-5-nano
AGENT_API_BASE=https://api.openai.com/v1

EMBEDDING_API_KEY=
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=512
EMBEDDING_API_BASE=https://api.openai.com/v1
```

The embedding model remains `text-embedding-3-small`. It serves a different API
contract and produces the 512-dimensional vectors expected by the PostgreSQL
schema. Do not replace it with the text-generation model.

`make demo` seeds checked-in regulation vectors and displays prebuilt browser
scenarios, so it makes no model call. Credentialed extraction, audit, adversarial,
and baseline commands can call the configured provider and incur charges.

## Why the code restricts the model family

The audit graph enforces a $0.25 preflight ceiling using explicit input, cached-input,
and output prices. The investigator and baseline clients therefore reject model
families whose prices are not represented by the current accounting constants. This
prevents a model-name change from silently underestimating cost.

Supporting another model requires updating the pricing boundary, its unit tests,
and the documentation, followed by credentialed extraction and agent evaluations.
Changing only `.env` to an unsupported family is intentionally rejected.

## Evaluation provenance

The checked-in `v1.0.0` extraction, agent, adversarial, and naive-baseline reports
were measured with `gpt-5.4-mini`. They remain historical artifacts and are not
renamed or recalculated when the runtime default changes. In particular, their
accuracy, tool-selection, citation, latency, and cost figures do not establish the
performance of `gpt-5-nano`.

Use these commands to produce new nano measurements deliberately:

```bash
make eval-extraction
make eval-all
make eval-baseline
make eval-adversarial
```

Provider responses are cached under ignored `data/traces/` files. Preserve the
model name, prompt version, dataset revision, and generated report together when
comparing runs.
