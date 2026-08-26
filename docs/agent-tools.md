# Audit-scoped agent tools

C10 exposes exactly eight operations to the investigator agent. C11 connects the
framework-neutral contracts to the bounded LangGraph investigation loop.

| Tool | Data boundary |
|---|---|
| `get_extracted_field` | One extracted field with page, bounding box, source text, and confidence |
| `get_escrow_ledger` | Inclusive date slice of the bound account's escrow ledger |
| `get_payment_history` | Inclusive date slice of the bound account's payments |
| `calculate_escrow_continuity` | Escrow-continuity findings from the deterministic engine |
| `calculate_payment_breakdown` | Payment decomposition from the deterministic engine |
| `compare_tax_projection` | Tax-projection findings from the deterministic engine |
| `search_regulations` | The measured C9 hybrid retrieval path and source metadata |
| `mark_information_missing` | Append-only record that a required document is absent |

## Security boundary

`build_agent_tools` binds every tool to one audit identifier supplied by the
framework. Model-visible Pydantic schemas never contain `audit_id`; they reject it
as an extra field if a model attempts to provide one. Invocation also receives a
trusted framework context, and execution stops before parsing or dependency access
when that context does not match the bound audit. Document ownership is checked by
the data source as a second boundary.

There is no general SQL, filesystem, URL-fetch, or arbitrary calculator tool. The
three financial operations can only call the typed reconciliation endpoint. Tool
responses are serialized through one output boundary and capped at 8,000
characters. Truncated responses end with an explicit `...[TRUNCATED]` marker.
The financial tools also derive the servicing-transfer date from the trusted bound
account; the model cannot supply or alter it.

## Configuration and verification

The engine proxy reads `ENGINE_API_BASE`, defaulting to
`http://127.0.0.1:8080` for host-side development. Docker Compose supplies
`http://engine:8080` to the AI container.

Run the dedicated acceptance suite with:

```bash
make test-tools
```

The suite covers all eight happy paths and, for every tool, strict rejection of a
model-supplied audit ID, rejection of an out-of-scope framework audit, and bounded
output with the truncation marker. It also covers cross-audit document ownership,
reversed date ranges, strict engine responses, data-source ownership, and sink
behavior. Tests use typed fakes; they do not turn fake responses into accuracy
claims.
