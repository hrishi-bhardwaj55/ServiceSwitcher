import json
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from langgraph.types import Command

from app.agents import AgentDependencies, DocumentRef, build_audit_graph, initial_audit_state
from app.agents.investigator import (
    FindingResolution,
    InvestigatorDecision,
    InvestigatorToolCall,
    ModelUsage,
    ScriptedInvestigatorModel,
)
from app.extraction.classifier import Classification
from app.extraction.models import BoundingBox, ExtractedField, ExtractionResult
from app.retrieval import RuleChunk, SearchResult
from app.schemas.mortgage import MortgageAccount
from app.tools import ToolDependencies
from app.tools.dependencies import (
    AuditRecord,
    InMemoryAuditDataSource,
    InMemoryMissingInformationSink,
)
from app.tools.engine import (
    EngineEvidence,
    EngineFinding,
    PaymentDecomposition,
    ReconciliationResult,
)

AUDIT_ID = "CASE-TEST"
DOCUMENT_ID = "doc_old_servicer_statement"


class FakeDocuments:
    def __init__(self, extraction=None) -> None:
        self.validated = []
        self.extraction = extraction or _extraction()

    def validate(self, document):
        self.validated.append(document.document_id)

    def classify(self, document):
        return Classification(
            document_type="OLD_SERVICER_STATEMENT",
            confidence=0.99,
            matched_signatures=("final mortgage statement",),
        )

    def extract(self, document):
        return self.extraction


class FakeEngine:
    def __init__(self, findings):
        self.findings = findings
        self.calls = []

    def reconcile(self, account, transfer_date):
        self.calls.append((account.account_id, transfer_date))
        return ReconciliationResult(
            findings=self.findings,
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


class FakeRegulations:
    def __init__(self) -> None:
        self.calls = []

    def hybrid(self, query, *, limit=5):
        self.calls.append((query, limit))
        return [
            SearchResult(
                chunk=RuleChunk(
                    id="regx-17-continuity",
                    source="12 CFR § 1024.17",
                    section="§ 1024.17",
                    title="Escrow account transfer continuity",
                    url="https://www.consumerfinance.gov/rules-policy/regulations/1024/17/",
                    content=(
                        "Servicers maintain accurate escrow account records and preserve "
                        "the account information needed during a servicing transfer."
                    ),
                ),
                score=0.03,
            )
        ][:limit]


def _account() -> MortgageAccount:
    return MortgageAccount.model_validate(
        {
            "account_id": "SS-TEST",
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
                }
            ],
            "escrow_ledger": [
                {
                    "date": "2024-05-01",
                    "type": "DEPOSIT",
                    "amount": "300.00",
                    "payee": "OLD",
                    "balance_after": "1200.00",
                }
            ],
            "tax_bills": [],
            "insurance_policies": [],
            "escrow_analyses": [],
        }
    )


def _extraction() -> ExtractionResult:
    fields = [
        ("principal_balance", Decimal("190000.00"), "190,000.00"),
        ("interest_rate", Decimal("0.05"), "5.00%"),
        ("monthly_payment", Decimal("1500.00"), "1,500.00"),
        ("escrow_balance", Decimal("1200.00"), "1,200.00"),
    ]
    return ExtractionResult(
        document_type="OLD_SERVICER_STATEMENT",
        classification_confidence=0.99,
        fields=[
            ExtractedField(
                field_name=name,
                value=value,
                page=1,
                bounding_box=BoundingBox(x0=1, y0=1, x1=2, y1=2),
                confidence=0.99,
                source_text=source,
            )
            for name, value, source in fields
        ],
    )


def _finding(finding_type="ESCROW_BALANCE_MISMATCH") -> EngineFinding:
    return EngineFinding(
        finding_type=finding_type,
        severity="LOW",
        confidence=1.0,
        actual_value=Decimal("1200.00"),
        servicer_value=Decimal("1300.00"),
        difference=Decimal("100.00"),
        monthly_impact=Decimal("0.00"),
        explanation="The new opening balance differs from the transfer balance.",
        evidence=[
            EngineEvidence(
                document_id=DOCUMENT_ID,
                page=1,
                field="escrow_balance",
                value=Decimal("1200.00"),
            )
        ],
        relevant_sources=["REG_X_1024_17"],
        recommended_action="Review both statements.",
    )


def _usage() -> ModelUsage:
    return ModelUsage(input_tokens=100, output_tokens=10)


def _tool(name="get_extracted_field", arguments=None):
    return InvestigatorDecision(
        tool_call=InvestigatorToolCall(
            name=name,
            arguments=(
                arguments
                if arguments is not None
                else {"document_id": DOCUMENT_ID, "field_name": "escrow_balance"}
            ),
        ),
        usage=_usage(),
    )


def _resolve(outcome):
    return InvestigatorDecision(
        resolution=FindingResolution(
            outcome=outcome,
            explanation="The available source evidence supports this bounded resolution.",
        ),
        usage=_usage(),
    )


def _harness(tmp_path: Path, decisions, *, findings=None, documents=None):
    model = ScriptedInvestigatorModel(decisions)
    engine = FakeEngine([_finding()] if findings is None else findings)
    regulations = FakeRegulations()
    source = InMemoryAuditDataSource(
        [AuditRecord(audit_id=AUDIT_ID, account=_account())],
        [],
    )
    tool_dependencies = ToolDependencies(
        audit_data=source,
        engine=engine,
        regulations=regulations,
        missing_information=InMemoryMissingInformationSink(),
    )
    dependencies = AgentDependencies(
        tools=tool_dependencies,
        document_store=source,
        documents=documents or FakeDocuments(),
        investigator=model,
        trace_root=tmp_path,
    )
    graph = build_audit_graph(dependencies)
    state = initial_audit_state(
        AUDIT_ID,
        [
            DocumentRef(
                audit_id=AUDIT_ID,
                document_id=DOCUMENT_ID,
                path=Path("ignored-by-fake.pdf"),
            )
        ],
    )
    config = {"configurable": {"thread_id": str(uuid4())}}
    return graph, state, config, model, engine, regulations


def _events(tmp_path: Path):
    lines = (tmp_path / f"{AUDIT_ID}.jsonl").read_text().splitlines()
    return [json.loads(line) for line in lines]


def test_graph_happy_path_runs_required_nodes_and_preserves_finding(tmp_path):
    graph, state, config, model, engine, regulations = _harness(
        tmp_path,
        [_tool(), _resolve("UNEXPLAINED")],
    )

    result = graph.invoke(state, config)

    assert [finding.finding_type for finding in result["final_findings"]] == [
        "ESCROW_BALANCE_MISMATCH"
    ]
    assert result["requires_review"] is False
    assert result["steps_used"] == 1
    assert result["cost_usd"] == Decimal("0.000018")
    assert engine.calls == [("SS-TEST", "2024-06-01")]
    assert len(regulations.calls) == 1
    assert set(model.tool_names[0]) == {
        "get_extracted_field",
        "get_escrow_ledger",
        "get_payment_history",
        "calculate_escrow_continuity",
        "calculate_payment_breakdown",
        "compare_tax_projection",
        "search_regulations",
        "mark_information_missing",
    }
    events = _events(tmp_path)
    assert [event["event"] for event in events] == ["tool_call", "model_resolution"]


def test_graph_skips_model_and_retrieval_when_engine_has_no_findings(tmp_path):
    graph, state, config, model, engine, regulations = _harness(
        tmp_path,
        [],
        findings=[],
    )

    result = graph.invoke(state, config)

    assert result["final_findings"] == []
    assert result["steps_used"] == 0
    assert model.requests == []
    assert regulations.calls == []
    assert engine.calls == [("SS-TEST", "2024-06-01")]


def test_graph_routes_model_backed_extraction_review_to_interrupt(tmp_path):
    extraction = _extraction().model_copy(
        update={
            "model_fallback_triggered": True,
            "requires_review": True,
            "review_reasons": ("one or more model-backed fields require review",),
        }
    )
    graph, state, config, _, _, _ = _harness(
        tmp_path,
        [],
        findings=[],
        documents=FakeDocuments(extraction),
    )

    result = graph.invoke(state, config)

    assert result["requires_review"] is True
    assert "__interrupt__" in result
    assert any("model-backed fields" in item for item in result["missing_information"])


def test_graph_recovers_from_tool_error_and_accepts_later_resolution(tmp_path):
    graph, state, config, _, _, _ = _harness(
        tmp_path,
        [
            _tool("unknown_tool", {"value": "bad"}),
            _tool(),
            _resolve("UNEXPLAINED"),
        ],
    )

    result = graph.invoke(state, config)

    assert len(result["final_findings"]) == 1
    assert result["requires_review"] is False
    assert result["steps_used"] == 2
    events = _events(tmp_path)
    assert events[0]["status"] == "error"
    assert events[1]["status"] == "ok"
    assert events[2]["result_summary"].startswith("UNEXPLAINED")


def test_graph_stops_at_twelve_tools_and_interrupts_for_review(tmp_path):
    decisions = [
        _tool("search_regulations", {"query": f"query {index}", "limit": 1})
        for index in range(12)
    ]
    graph, state, config, _, _, _ = _harness(tmp_path, decisions)

    result = graph.invoke(state, config)

    assert result["steps_used"] == 12
    assert result["cost_usd"] < Decimal("0.25")
    assert result["requires_review"] is True
    assert "__interrupt__" in result
    events = _events(tmp_path)
    assert len([event for event in events if event["event"] == "tool_call"]) == 12
    assert events[-1]["event"] == "budget_exhausted"


def test_graph_stops_repeated_successful_tool_call_as_non_progress(tmp_path):
    graph, state, config, _, _, _ = _harness(tmp_path, [_tool(), _tool()])

    result = graph.invoke(state, config)

    assert result["steps_used"] == 2
    assert result["requires_review"] is True
    assert "__interrupt__" in result
    events = _events(tmp_path)
    assert events[-1]["status"] == "rejected"
    assert "duplicate successful tool call" in events[-1]["result_summary"]


def test_graph_refuses_a_model_call_that_could_cross_cost_budget(tmp_path):
    graph, state, config, model, _, _ = _harness(tmp_path, [_tool()])
    model.maximum_call_cost = Decimal("0.250001")

    result = graph.invoke(state, config)

    assert result["steps_used"] == 0
    assert result["cost_usd"] == Decimal("0")
    assert result["requires_review"] is True
    assert model.requests == []
    assert _events(tmp_path)[-1]["event"] == "budget_exhausted"


def test_graph_rejects_resolution_until_an_evidence_tool_succeeds(tmp_path):
    graph, state, config, model, _, _ = _harness(
        tmp_path,
        [_resolve("UNEXPLAINED"), _tool(), _resolve("UNEXPLAINED")],
    )

    result = graph.invoke(state, config)

    assert len(result["final_findings"]) == 1
    assert result["steps_used"] == 1
    assert model.requests[1].observations[0].is_error is True
    assert "use at least one evidence tool" in model.requests[1].observations[0].result_summary


def test_graph_rejects_unsupported_explanation_and_preserves_finding(tmp_path):
    graph, state, config, _, _, _ = _harness(
        tmp_path,
        [_tool(), _resolve("EXPLAINED")],
    )

    result = graph.invoke(state, config)

    assert len(result["final_findings"]) == 1
    assert result["requires_review"] is True
    assert "__interrupt__" in result
    assert _events(tmp_path)[-1]["status"] == "rejected"


def test_graph_accepts_explanation_with_structured_engine_support(tmp_path):
    payment_finding = _finding("UNEXPLAINED_PAYMENT_INCREASE")
    graph, state, config, _, _, _ = _harness(
        tmp_path,
        [_tool("calculate_payment_breakdown", {}), _resolve("EXPLAINED")],
        findings=[payment_finding],
    )

    result = graph.invoke(state, config)

    assert result["final_findings"] == []
    assert result["requires_review"] is False
    assert _events(tmp_path)[-1]["status"] == "ok"


def test_human_review_interrupt_resumes_with_checkpointed_decision(tmp_path):
    graph, state, config, _, _, _ = _harness(
        tmp_path,
        [_tool(), _resolve("REQUIRES_REVIEW")],
    )

    interrupted = graph.invoke(state, config)

    assert interrupted["requires_review"] is True
    assert "__interrupt__" in interrupted

    completed = graph.invoke(
        Command(resume={"approved": True, "notes": "Evidence reviewed."}),
        config,
    )

    assert completed["requires_review"] is False
    assert [finding.finding_type for finding in completed["final_findings"]] == [
        "ESCROW_BALANCE_MISMATCH"
    ]
