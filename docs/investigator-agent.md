# Investigator agent

C11 implements the complete PDF-to-finding audit pipeline as a compiled LangGraph
state graph. The model investigates findings already produced by the deterministic
engine; it cannot create a discrepancy or alter the arithmetic behind one.

## Pipeline and ownership

The graph executes this sequence:

```text
load_documents -> classify -> extract -> validate_extraction -> reconcile
  -> retrieve_guidance -> investigate_ambiguous_findings
  -> validate_evidence -> calculate_risk -> prepare_report
```

When reconciliation returns no findings, the graph skips retrieval and model use.
Every node except `investigate_ambiguous_findings` is deterministic. The graph and
all eight tools share one mutable, audit-scoped extraction store, and every document
reference must carry the graph's audit identifier.

`prepare_report` uses a checkpointed LangGraph interrupt whenever evidence,
extraction confidence, a budget stop, or an investigation decision requires human
review. A typed approval resumes the same graph thread.

## Investigator boundary

The model receives one deterministic finding, retrieved rule chunks, previous tool
observations, and only the eight C10 tools. Each provider turn must produce exactly
one strict function call: a tool invocation or `resolve_finding`. Parallel calls and
provider-side response storage are disabled.

The controller enforces all of these limits in code:

- at most 12 attempted tool calls per audit;
- at most 32 model turns as a secondary loop guard;
- a conservative preflight ceiling of $0.25 per audit;
- at least one successful evidence tool before resolution;
- no repeated successful invocation with identical arguments;
- bounded tool observations and trajectory summaries;
- preservation of all remaining findings after any model, budget, or non-progress
  failure.

An `EXPLAINED` answer is fail-closed. It may suppress an
`UNEXPLAINED_PAYMENT_INCREASE` only when a successful deterministic payment
decomposition explicitly reports `EXPLAINED`. No current structured operation can
erase the other four discrepancy types. If the model calls a comparator that
confirms a tax or escrow mismatch and labels that confirmation an explanation, the
controller rejects the resolution, retains the finding, and requests review.

## Configuration

The repository-root `.env` is ignored by Git and is loaded by the audit CLI. The
shared configuration is:

```dotenv
LLM_API_KEY=your-key
LLM_MODEL=gpt-5.4-mini
LLM_API_BASE=https://api.openai.com/v1
```

Optional `AGENT_API_KEY`, `AGENT_MODEL`, and `AGENT_API_BASE` values override the
shared settings. `EMBEDDING_API_KEY` may override the key used to ingest and query
the regulation corpus. The default agent model is `gpt-5.4-mini`; the code rejects
other model families because its token-cost enforcement uses that model's published
pricing. See the official [model page](https://developers.openai.com/api/docs/models/gpt-5.4-mini)
and [Responses API reference](https://developers.openai.com/api/reference/resources/responses/methods/create).

## Running and verifying

Run the focused deterministic suite:

```bash
make test-agent
make test-tools
```

Run the end-to-end acceptance case:

```bash
make run-audit CASE=CASE-0042
```

The CLI binds the five PDFs for the selected ground-truth case, extracts them,
ingests the 47 regulation chunks, invokes the engine and investigator, then prints a
typed JSON result. Tool attempts are appended to
`data/traces/<audit_id>.jsonl` with timestamps, bounded arguments and result
summaries, input/output/cached token counts, per-turn cost, cumulative cost, and
step count.

The regression suite covers the happy path, a no-finding branch, tool-error
recovery, a 12-call stop, cost preflight rejection, resolution-before-evidence,
unsupported model explanations, supported structured explanations, repeated-call
non-progress, trajectory bounds, and checkpointed human-review resume. A live
CASE-0042 run preserved the engine's `PROPERTY_TAX_PROJECTION_MISMATCH` with exact
$613.17 total and $51.10 monthly impact; a repeated comparison was stopped at two
steps and routed to review instead of allowing the model to discard the finding.

LangGraph checkpoint and interrupt behavior follows its official
[interrupt documentation](https://docs.langchain.com/oss/python/langgraph/interrupts).
