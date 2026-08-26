"""LangGraph audit pipeline with one budgeted agentic investigation node."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Literal

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from app.agents.documents import DocumentProcessor
from app.agents.investigator import (
    InvestigationRequest,
    InvestigatorModel,
    ToolObservation,
)
from app.agents.models import AuditState, HumanReviewDecision
from app.agents.tracing import TrajectoryLogger
from app.extraction.extractor import FIELD_RULES
from app.extraction.models import ExtractionResult
from app.tools import ToolInvocationContext, build_agent_tools
from app.tools.core import ToolError
from app.tools.dependencies import MutableAuditDataSource, StoredExtraction, ToolDependencies
from app.tools.engine import EngineFinding

MAX_TOOL_CALLS = 12
MAX_MODEL_TURNS = 32
MAX_AUDIT_COST_USD = Decimal("0.25")
OBSERVATION_LIMIT = 2_000
FINDING_QUERIES = {
    "ESCROW_BALANCE_MISMATCH": "escrow balance continuity servicing transfer",
    "PROPERTY_TAX_PROJECTION_MISMATCH": "property tax projection escrow analysis",
    "ESCROW_SHORTAGE_CALCULATION_ERROR": "escrow shortage aggregate analysis",
    "DUPLICATE_TAX_DISBURSEMENT": "duplicate escrow tax disbursement transfer",
    "UNEXPLAINED_PAYMENT_INCREASE": "mortgage payment increase servicing transfer",
}


@dataclass(frozen=True)
class AgentDependencies:
    tools: ToolDependencies
    document_store: MutableAuditDataSource
    documents: DocumentProcessor
    investigator: InvestigatorModel
    trace_root: Path

    def __post_init__(self) -> None:
        if self.tools.audit_data is not self.document_store:
            raise ValueError("graph and tool registry must share one audit data source")


class AuditNodes:
    def __init__(self, dependencies: AgentDependencies) -> None:
        self.dependencies = dependencies

    def load_documents(self, state: AuditState) -> dict[str, object]:
        seen: set[str] = set()
        for document in state["documents"]:
            if document.audit_id != state["audit_id"]:
                raise ValueError("document crossed the graph audit boundary")
            if document.document_id in seen:
                raise ValueError("document ids must be unique")
            seen.add(document.document_id)
            self.dependencies.documents.validate(document)
        return {"extracted_values": {}}

    def classify(self, state: AuditState) -> dict[str, object]:
        values: dict[str, dict[str, object]] = {}
        for document in state["documents"]:
            classification = self.dependencies.documents.classify(document)
            values[document.document_id] = {
                "document_type": classification.document_type,
                "classification_confidence": classification.confidence,
                "matched_signatures": list(classification.matched_signatures),
            }
        return {"extracted_values": values}

    def extract(self, state: AuditState) -> dict[str, object]:
        values: dict[str, dict[str, object]] = {}
        review = state["requires_review"]
        missing = list(state["missing_information"])
        for document in state["documents"]:
            extraction = self.dependencies.documents.extract(document)
            classified = state["extracted_values"][document.document_id]
            if extraction.document_type != classified["document_type"]:
                review = True
                missing.append(f"{document.document_id}: classification changed during extraction")
            values[document.document_id] = extraction.model_dump(mode="python")
            self.dependencies.document_store.store_extraction(
                StoredExtraction(
                    audit_id=state["audit_id"],
                    document_id=document.document_id,
                    extraction=extraction,
                )
            )
        return {
            "extracted_values": values,
            "requires_review": review,
            "missing_information": missing,
        }

    def validate_extraction(self, state: AuditState) -> dict[str, object]:
        review = state["requires_review"]
        missing = list(state["missing_information"])
        for document_id, raw in state["extracted_values"].items():
            extraction = ExtractionResult.model_validate(raw)
            expected = {rule.field_name for rule in FIELD_RULES[extraction.document_type]}
            fields = extraction.field_map()
            absent = sorted(expected - fields.keys())
            if absent:
                review = True
                missing.append(f"{document_id}: missing extracted fields {', '.join(absent)}")
            if extraction.classification_confidence < 0.80:
                review = True
                missing.append(f"{document_id}: low-confidence classification")
            low_confidence = sorted(
                name for name, field in fields.items() if field.confidence < 0.90
            )
            if low_confidence:
                review = True
                missing.append(
                    f"{document_id}: low-confidence fields {', '.join(low_confidence)}"
                )
        return {"requires_review": review, "missing_information": missing}

    def reconcile(self, state: AuditState) -> dict[str, object]:
        account = self.dependencies.tools.audit_data.get_account(state["audit_id"])
        if len(account.servicing_periods) < 2:
            raise ValueError("account has no servicing transfer")
        transfer_date = account.servicing_periods[1].start_date.isoformat()
        result = self.dependencies.tools.engine.reconcile(account, transfer_date)
        findings = [
            finding for finding in result.findings if finding.finding_type != "EXPLAINED"
        ]
        return {
            "deterministic_findings": findings,
            "ambiguous_findings": findings,
            "final_findings": findings,
        }

    def retrieve_guidance(self, state: AuditState) -> dict[str, object]:
        chunks = {}
        missing = list(state["missing_information"])
        review = state["requires_review"]
        try:
            for finding in state["ambiguous_findings"]:
                query = FINDING_QUERIES[finding.finding_type]
                for result in self.dependencies.tools.regulations.hybrid(query, limit=5):
                    chunks[result.chunk.id] = result.chunk
        except Exception as error:
            review = True
            missing.append(f"regulation retrieval failed: {type(error).__name__}")
        return {
            "retrieved_rules": list(chunks.values()),
            "requires_review": review,
            "missing_information": missing,
        }

    def investigate_ambiguous_findings(self, state: AuditState) -> dict[str, object]:
        audit_id = state["audit_id"]
        tools = build_agent_tools(audit_id, self.dependencies.tools)
        context = ToolInvocationContext(audit_id)
        logger = TrajectoryLogger(self.dependencies.trace_root, audit_id)
        final: list[EngineFinding] = []
        review = state["requires_review"]
        steps = state["steps_used"]
        cost = state["cost_usd"]
        model_turns = 0
        ambiguous = state["ambiguous_findings"]

        for finding_index, finding in enumerate(ambiguous):
            observations: list[ToolObservation] = []
            successful_tools = 0
            while True:
                request = InvestigationRequest(
                    audit_id=audit_id,
                    finding=finding,
                    retrieved_rules=state["retrieved_rules"],
                    observations=observations,
                )
                estimate = self.dependencies.investigator.estimate_max_cost(request, tools)
                if (
                    steps >= MAX_TOOL_CALLS
                    or model_turns >= MAX_MODEL_TURNS
                    or cost + estimate > MAX_AUDIT_COST_USD
                ):
                    review = True
                    final.extend(ambiguous[finding_index:])
                    logger.append(
                        event="budget_exhausted",
                        finding_type=finding.finding_type,
                        status="stopped",
                        result_summary="tool-call, model-turn, or cost budget exhausted",
                        cumulative_cost_usd=cost,
                        steps_used=steps,
                    )
                    return _investigation_update(final, review, steps, cost)

                try:
                    decision = self.dependencies.investigator.decide(request, tools)
                except Exception as error:
                    review = True
                    final.extend(ambiguous[finding_index:])
                    logger.append(
                        event="model_resolution",
                        finding_type=finding.finding_type,
                        status="error",
                        result_summary=f"model error: {type(error).__name__}",
                        cumulative_cost_usd=cost,
                        steps_used=steps,
                    )
                    return _investigation_update(final, review, steps, cost)

                model_turns += 1
                turn_cost = decision.usage.cost_usd
                if turn_cost > estimate:
                    raise RuntimeError("model usage exceeded its preflight cost upper bound")
                cost += turn_cost

                if decision.resolution is not None:
                    if successful_tools == 0:
                        observations.append(
                            ToolObservation(
                                tool="resolve_finding",
                                arguments={},
                                result_summary=(
                                    "Resolution rejected: use at least one evidence tool first."
                                ),
                                is_error=True,
                            )
                        )
                        continue
                    resolution = decision.resolution
                    logger.append(
                        event="model_resolution",
                        finding_type=finding.finding_type,
                        status="ok",
                        result_summary=f"{resolution.outcome}: {resolution.explanation}",
                        input_tokens=decision.usage.input_tokens,
                        output_tokens=decision.usage.output_tokens,
                        cost_usd=turn_cost,
                        cumulative_cost_usd=cost,
                        steps_used=steps,
                    )
                    if resolution.outcome != "EXPLAINED":
                        final.append(finding)
                    if resolution.outcome == "REQUIRES_REVIEW":
                        review = True
                    break

                tool_call = decision.tool_call
                steps += 1
                status: Literal["ok", "error"] = "ok"
                try:
                    if tool_call.name not in tools:
                        raise ToolError(f"unknown tool {tool_call.name}")
                    output = tools[tool_call.name].invoke(tool_call.arguments, context)
                    summary = output.content
                    successful_tools += 1
                except Exception as error:
                    status = "error"
                    summary = f"{type(error).__name__}: {error}"
                summary = _bounded_observation(summary)
                observations.append(
                    ToolObservation(
                        tool=tool_call.name,
                        arguments=tool_call.arguments,
                        result_summary=summary,
                        is_error=status == "error",
                    )
                )
                logger.append(
                    event="tool_call",
                    finding_type=finding.finding_type,
                    status=status,
                    tool=tool_call.name,
                    arguments=tool_call.arguments,
                    result_summary=summary,
                    input_tokens=decision.usage.input_tokens,
                    output_tokens=decision.usage.output_tokens,
                    cost_usd=turn_cost,
                    cumulative_cost_usd=cost,
                    steps_used=steps,
                )

        return _investigation_update(final, review, steps, cost)

    def validate_evidence(self, state: AuditState) -> dict[str, object]:
        deterministic = state["deterministic_findings"]
        document_ids = {document.document_id for document in state["documents"]}
        missing = list(state["missing_information"])
        review = state["requires_review"]
        for finding in state["final_findings"]:
            if finding not in deterministic:
                raise ValueError("agent attempted to introduce a non-deterministic finding")
            if not finding.evidence:
                review = True
                missing.append(f"{finding.finding_type}: no document evidence")
            for evidence in finding.evidence:
                if evidence.document_id not in document_ids:
                    review = True
                    missing.append(
                        f"{finding.finding_type}: missing evidence {evidence.document_id}"
                    )
        return {"requires_review": review, "missing_information": missing}

    def calculate_risk(self, state: AuditState) -> dict[str, object]:
        review = state["requires_review"]
        missing = list(state["missing_information"])
        for finding in state["final_findings"]:
            expected = _severity(finding)
            if finding.severity != expected:
                review = True
                missing.append(
                    f"{finding.finding_type}: engine severity {finding.severity} "
                    f"does not match {expected}"
                )
        return {"requires_review": review, "missing_information": missing}

    def prepare_report(self, state: AuditState) -> dict[str, object]:
        if not state["requires_review"]:
            return {"requires_review": False}
        raw = interrupt(
            {
                "audit_id": state["audit_id"],
                "message": "Human review is required before preparing the report.",
                "finding_types": [
                    finding.finding_type for finding in state["final_findings"]
                ],
                "missing_information": state["missing_information"],
            }
        )
        decision = HumanReviewDecision.model_validate(raw)
        return {"requires_review": not decision.approved}


def build_audit_graph(dependencies: AgentDependencies, *, checkpointer=None):
    nodes = AuditNodes(dependencies)
    builder = StateGraph(AuditState)
    builder.add_node("load_documents", nodes.load_documents)
    builder.add_node("classify", nodes.classify)
    builder.add_node("extract", nodes.extract)
    builder.add_node("validate_extraction", nodes.validate_extraction)
    builder.add_node("reconcile", nodes.reconcile)
    builder.add_node("retrieve_guidance", nodes.retrieve_guidance)
    builder.add_node(
        "investigate_ambiguous_findings",
        nodes.investigate_ambiguous_findings,
    )
    builder.add_node("validate_evidence", nodes.validate_evidence)
    builder.add_node("calculate_risk", nodes.calculate_risk)
    builder.add_node("prepare_report", nodes.prepare_report)
    builder.add_edge(START, "load_documents")
    builder.add_edge("load_documents", "classify")
    builder.add_edge("classify", "extract")
    builder.add_edge("extract", "validate_extraction")
    builder.add_edge("validate_extraction", "reconcile")
    builder.add_conditional_edges(
        "reconcile",
        _route_after_reconcile,
        {
            "retrieve_guidance": "retrieve_guidance",
            "validate_evidence": "validate_evidence",
        },
    )
    builder.add_edge("retrieve_guidance", "investigate_ambiguous_findings")
    builder.add_edge("investigate_ambiguous_findings", "validate_evidence")
    builder.add_edge("validate_evidence", "calculate_risk")
    builder.add_edge("calculate_risk", "prepare_report")
    builder.add_edge("prepare_report", END)
    return builder.compile(
        checkpointer=checkpointer or InMemorySaver(),
        name="servicerswitch_audit",
    )


def _route_after_reconcile(
    state: AuditState,
) -> Literal["retrieve_guidance", "validate_evidence"]:
    return "retrieve_guidance" if state["ambiguous_findings"] else "validate_evidence"


def _bounded_observation(value: str) -> str:
    if len(value) <= OBSERVATION_LIMIT:
        return value
    marker = "...[TRUNCATED]"
    return value[: OBSERVATION_LIMIT - len(marker)] + marker


def _investigation_update(
    final: list[EngineFinding],
    review: bool,
    steps: int,
    cost: Decimal,
) -> dict[str, object]:
    return {
        "final_findings": final,
        "requires_review": review,
        "steps_used": steps,
        "cost_usd": cost,
    }


def _severity(finding: EngineFinding) -> Literal["LOW", "MEDIUM", "HIGH"]:
    total = abs(finding.difference or Decimal("0"))
    monthly = abs(finding.monthly_impact or Decimal("0"))
    if monthly >= Decimal("100") or total >= Decimal("1000"):
        return "HIGH"
    if monthly >= Decimal("25"):
        return "MEDIUM"
    return "LOW"
