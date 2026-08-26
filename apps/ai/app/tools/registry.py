"""Construct the complete, audit-bound C10 tool registry."""

from __future__ import annotations

from collections.abc import Callable

from app.schemas.mortgage import CanonicalModel
from app.tools.core import DEFAULT_MAX_OUTPUT_CHARS, ScopedAgentTool
from app.tools.dependencies import ToolDependencies
from app.tools.handlers import (
    calculate_escrow_continuity,
    calculate_payment_breakdown,
    compare_tax_projection,
    get_escrow_ledger,
    get_extracted_field,
    get_payment_history,
    mark_information_missing,
    search_regulations,
)
from app.tools.schemas import (
    CalculateEscrowContinuityArgs,
    CalculatePaymentBreakdownArgs,
    CompareTaxProjectionArgs,
    GetEscrowLedgerArgs,
    GetExtractedFieldArgs,
    GetPaymentHistoryArgs,
    MarkInformationMissingArgs,
    SearchRegulationsArgs,
)

TOOL_NAMES = (
    "get_extracted_field",
    "get_escrow_ledger",
    "get_payment_history",
    "calculate_escrow_continuity",
    "calculate_payment_breakdown",
    "compare_tax_projection",
    "search_regulations",
    "mark_information_missing",
)


def build_agent_tools(
    audit_id: str,
    dependencies: ToolDependencies,
    *,
    max_output_chars: int = DEFAULT_MAX_OUTPUT_CHARS,
) -> dict[str, ScopedAgentTool]:
    """Bind all eight tools to one trusted framework audit identifier."""
    definitions = (
        ("get_extracted_field", GetExtractedFieldArgs, get_extracted_field),
        ("get_escrow_ledger", GetEscrowLedgerArgs, get_escrow_ledger),
        ("get_payment_history", GetPaymentHistoryArgs, get_payment_history),
        (
            "calculate_escrow_continuity",
            CalculateEscrowContinuityArgs,
            calculate_escrow_continuity,
        ),
        (
            "calculate_payment_breakdown",
            CalculatePaymentBreakdownArgs,
            calculate_payment_breakdown,
        ),
        ("compare_tax_projection", CompareTaxProjectionArgs, compare_tax_projection),
        ("search_regulations", SearchRegulationsArgs, search_regulations),
        ("mark_information_missing", MarkInformationMissingArgs, mark_information_missing),
    )
    tools = {}
    for name, argument_model, handler in definitions:
        tools[name] = ScopedAgentTool(
            name=name,
            bound_audit_id=audit_id,
            argument_model=argument_model,
            handler=_bind(handler, audit_id, dependencies),
            max_output_chars=max_output_chars,
        )
    if tuple(tools) != TOOL_NAMES:
        raise AssertionError("agent tool registry does not match its public contract")
    return tools


def _bind[ArgumentT: CanonicalModel](
    handler: Callable[[ArgumentT, str, ToolDependencies], object],
    audit_id: str,
    dependencies: ToolDependencies,
) -> Callable[[ArgumentT], object]:
    def bound(arguments: ArgumentT) -> object:
        return handler(arguments, audit_id, dependencies)

    bound.__doc__ = handler.__doc__
    return bound
