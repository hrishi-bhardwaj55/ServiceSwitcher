import json
from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.extraction.models import BoundingBox, ExtractedField, ExtractionResult
from app.retrieval import RuleChunk, SearchResult
from app.schemas.mortgage import MortgageAccount
from app.tools import (
    TOOL_NAMES,
    AuditScopeError,
    ToolDependencies,
    ToolInvocationContext,
    build_agent_tools,
)
from app.tools.core import TRUNCATION_MARKER
from app.tools.dependencies import (
    AuditRecord,
    InMemoryAuditDataSource,
    InMemoryMissingInformationSink,
    StoredExtraction,
)
from app.tools.engine import (
    EngineEvidence,
    EngineFinding,
    PaymentDecomposition,
    ReconciliationResult,
)

AUDIT_ID = "audit-a"
CONTEXT = ToolInvocationContext(AUDIT_ID)
HAPPY_ARGUMENTS = {
    "get_extracted_field": {
        "document_id": "old-servicer-statement",
        "field_name": "escrow_balance",
    },
    "get_escrow_ledger": {"start_date": "2024-06-01", "end_date": "2024-06-30"},
    "get_payment_history": {"start_date": "2024-05-01", "end_date": "2024-06-01"},
    "calculate_escrow_continuity": {"transfer_date": "2024-06-01"},
    "calculate_payment_breakdown": {"transfer_date": "2024-06-01"},
    "compare_tax_projection": {"transfer_date": "2024-06-01"},
    "search_regulations": {"query": "escrow transfer balance", "limit": 2},
    "mark_information_missing": {
        "document_type": "PROPERTY_TAX_BILL",
        "reason": "The current property tax bill was not uploaded.",
    },
}


class FakeEngine:
    def __init__(self) -> None:
        self.calls = []

    def reconcile(self, account, transfer_date):
        self.calls.append((account.account_id, transfer_date))
        return _engine_result()


class FakeRegulations:
    def __init__(self) -> None:
        self.calls = []

    def hybrid(self, query, *, limit=5):
        self.calls.append((query, limit))
        return [
            SearchResult(
                chunk=RuleChunk(
                    id="regx-17-test",
                    source="12 CFR § 1024.17",
                    section="§ 1024.17(k)",
                    title="Timely escrow disbursements",
                    url="https://www.consumerfinance.gov/rules-policy/regulations/1024/17/",
                    content=(
                        "A servicer must make covered escrow disbursements on time and "
                        "before the applicable penalty deadline when the rule applies."
                    ),
                ),
                score=0.03,
            )
        ][:limit]


def _account() -> MortgageAccount:
    return MortgageAccount.model_validate(
        {
            "account_id": "SS-TOOLS",
            "original_principal": "200000.00",
            "current_principal": "190000.00",
            "annual_rate": "0.05",
            "term_months": 360,
            "origination_date": "2024-01-01",
            "servicing_periods": [
                {
                    "servicer_id": "OLD",
                    "start_date": "2024-01-01",
                    "end_date": "2024-05-31",
                },
                {
                    "servicer_id": "NEW",
                    "start_date": "2024-06-01",
                    "end_date": None,
                },
            ],
            "payments": [
                {
                    "date": "2024-05-01",
                    "total": "1500.00",
                    "principal": "500.00",
                    "interest": "700.00",
                    "escrow": "300.00",
                },
                {
                    "date": "2024-06-01",
                    "total": "1600.00",
                    "principal": "505.00",
                    "interest": "695.00",
                    "escrow": "400.00",
                },
            ],
            "escrow_ledger": [
                {
                    "date": "2024-05-01",
                    "type": "DEPOSIT",
                    "amount": "300.00",
                    "payee": "OLD",
                    "balance_after": "1200.00",
                },
                {
                    "date": "2024-06-01",
                    "type": "ADJUSTMENT",
                    "amount": "0.00",
                    "payee": "SERVICING_TRANSFER:OLD->NEW",
                    "balance_after": "1200.00",
                },
                {
                    "date": "2024-06-15",
                    "type": "TAX_DISBURSEMENT",
                    "amount": "-900.00",
                    "payee": "County",
                    "balance_after": "300.00",
                },
            ],
            "tax_bills": [
                {
                    "authority": "County",
                    "tax_year": 2024,
                    "annual_amount": "2400.00",
                    "due_dates": ["2024-12-01"],
                }
            ],
            "insurance_policies": [],
            "escrow_analyses": [],
        }
    )


def _stored_extraction(audit_id: str, document_id: str) -> StoredExtraction:
    return StoredExtraction(
        audit_id=audit_id,
        document_id=document_id,
        extraction=ExtractionResult(
            document_type="OLD_SERVICER_STATEMENT",
            classification_confidence=1.0,
            fields=[
                ExtractedField(
                    field_name="escrow_balance",
                    value=Decimal("1200.00"),
                    page=1,
                    bounding_box=BoundingBox(x0=10, y0=20, x1=80, y1=32),
                    confidence=0.99,
                    source_text="Escrow balance $1,200.00",
                )
            ],
        ),
    )


def _finding(finding_type: str) -> EngineFinding:
    return EngineFinding(
        finding_type=finding_type,
        severity="MEDIUM",
        confidence=1.0,
        actual_value=Decimal("1200.00"),
        servicer_value=Decimal("1300.00"),
        difference=Decimal("100.00"),
        monthly_impact=Decimal("8.33"),
        explanation=f"Deterministic {finding_type} explanation.",
        evidence=[
            EngineEvidence(
                document_id="old-servicer-statement",
                page=1,
                field="escrow_balance",
                value=Decimal("1200.00"),
            )
        ],
        relevant_sources=["REG_X_1024_17"],
        recommended_action="Review the source documents.",
    )


def _engine_result() -> ReconciliationResult:
    return ReconciliationResult(
        findings=[
            _finding("ESCROW_BALANCE_MISMATCH"),
            _finding("PROPERTY_TAX_PROJECTION_MISMATCH"),
        ],
        payment_decomposition=PaymentDecomposition(
            payment_change=Decimal("100.00"),
            principal_interest_change=Decimal("0.00"),
            tax_change_monthly=Decimal("100.00"),
            insurance_change_monthly=Decimal("0.00"),
            shortage_monthly=Decimal("0.00"),
            residual=Decimal("0.00"),
            tolerance=Decimal("10.00"),
            outcome="EXPLAINED",
        ),
        engine_version="1.0.0",
    )


def _harness(*, max_output_chars=8_000):
    engine = FakeEngine()
    regulations = FakeRegulations()
    missing = InMemoryMissingInformationSink()
    source = InMemoryAuditDataSource(
        [AuditRecord(audit_id=AUDIT_ID, account=_account())],
        [
            _stored_extraction(AUDIT_ID, "old-servicer-statement"),
            _stored_extraction("audit-b", "foreign-statement"),
        ],
    )
    dependencies = ToolDependencies(
        audit_data=source,
        engine=engine,
        regulations=regulations,
        missing_information=missing,
    )
    tools = build_agent_tools(
        AUDIT_ID,
        dependencies,
        max_output_chars=max_output_chars,
    )
    return tools, engine, regulations, missing


def _invoke(tools, name):
    return tools[name].invoke(HAPPY_ARGUMENTS[name], CONTEXT)


def test_registry_exposes_exactly_eight_strict_documented_tools():
    tools, _, _, _ = _harness()

    assert tuple(tools) == TOOL_NAMES
    assert len(tools) == 8
    for tool in tools.values():
        assert tool.description
        assert "audit_id" not in str(tool.argument_schema())
        assert tool.argument_schema()["additionalProperties"] is False


def test_get_extracted_field_returns_value_and_complete_provenance():
    tools, _, _, _ = _harness()

    result = json.loads(_invoke(tools, "get_extracted_field").content)

    assert result["field"]["value"] == "1200.00"
    assert result["field"]["page"] == 1
    assert result["field"]["bounding_box"] == {"x0": 10.0, "x1": 80.0, "y0": 20.0, "y1": 32.0}
    assert result["field"]["source_text"] == "Escrow balance $1,200.00"


def test_ledger_and_payment_tools_filter_inclusive_date_ranges():
    tools, _, _, _ = _harness()

    ledger = json.loads(_invoke(tools, "get_escrow_ledger").content)
    payments = json.loads(_invoke(tools, "get_payment_history").content)

    assert ledger["count"] == 2
    assert [entry["date"] for entry in ledger["entries"]] == ["2024-06-01", "2024-06-15"]
    assert payments["count"] == 2
    assert [payment["date"] for payment in payments["payments"]] == [
        "2024-05-01",
        "2024-06-01",
    ]


def test_engine_tools_return_only_their_deterministic_slice():
    tools, engine, _, _ = _harness()

    continuity = json.loads(_invoke(tools, "calculate_escrow_continuity").content)
    breakdown = json.loads(_invoke(tools, "calculate_payment_breakdown").content)
    tax = json.loads(_invoke(tools, "compare_tax_projection").content)

    assert [item["finding_type"] for item in continuity["findings"]] == [
        "ESCROW_BALANCE_MISMATCH"
    ]
    assert breakdown["payment_decomposition"]["outcome"] == "EXPLAINED"
    assert [item["finding_type"] for item in tax["findings"]] == [
        "PROPERTY_TAX_PROJECTION_MISMATCH"
    ]
    assert engine.calls == [("SS-TOOLS", "2024-06-01")] * 3


def test_regulation_and_missing_information_tools_use_narrow_dependencies():
    tools, _, regulations, missing = _harness()

    search = json.loads(_invoke(tools, "search_regulations").content)
    receipt = json.loads(_invoke(tools, "mark_information_missing").content)

    assert search["results"][0]["chunk"]["id"] == "regx-17-test"
    assert regulations.calls == [("escrow transfer balance", 2)]
    assert receipt["record_id"] == "missing-000001"
    assert missing.records[0].audit_id == AUDIT_ID


@pytest.mark.parametrize("name", TOOL_NAMES)
def test_every_tool_rejects_model_supplied_audit_id(name):
    tools, _, _, _ = _harness()
    malformed = {**HAPPY_ARGUMENTS[name], "audit_id": "audit-b"}

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        tools[name].invoke(malformed, CONTEXT)


@pytest.mark.parametrize("name", TOOL_NAMES)
def test_every_tool_rejects_out_of_scope_framework_audit(name):
    tools, _, _, _ = _harness()

    with pytest.raises(AuditScopeError, match="different audit"):
        tools[name].invoke(HAPPY_ARGUMENTS[name], ToolInvocationContext("audit-b"))


@pytest.mark.parametrize("name", TOOL_NAMES)
def test_every_tool_marks_oversized_responses(name):
    tools, _, _, _ = _harness(max_output_chars=48)

    output = tools[name].invoke(HAPPY_ARGUMENTS[name], CONTEXT)

    assert output.truncated is True
    assert output.content.endswith(TRUNCATION_MARKER)
    assert len(output.content) == 48


@pytest.mark.parametrize("name", ["get_escrow_ledger", "get_payment_history"])
def test_date_range_tools_reject_reversed_ranges(name):
    tools, _, _, _ = _harness()

    with pytest.raises(ValidationError, match="end_date must not be before"):
        tools[name].invoke(
            {"start_date": date(2024, 7, 1), "end_date": date(2024, 6, 1)},
            CONTEXT,
        )


def test_document_reference_cannot_cross_audits():
    tools, _, _, _ = _harness()

    with pytest.raises(AuditScopeError, match="different audit"):
        tools["get_extracted_field"].invoke(
            {"document_id": "foreign-statement", "field_name": "escrow_balance"},
            CONTEXT,
        )
