import os
from decimal import Decimal

import pytest

from app.agents.investigator import InvestigationRequest, OpenAIInvestigatorModel
from app.tools.engine import EngineFinding


@pytest.mark.llm
def test_real_nano_provider_returns_one_schema_validated_action():
    if not os.getenv("LLM_API_KEY") or os.getenv("LLM_MODEL") != "gpt-5-nano":
        pytest.skip("LLM_API_KEY and LLM_MODEL=gpt-5-nano are required")
    model = OpenAIInvestigatorModel.from_env()
    request = InvestigationRequest(
        audit_id="CASE-NANO-SMOKE",
        finding=EngineFinding(
            finding_type="PROPERTY_TAX_PROJECTION_MISMATCH",
            severity="MEDIUM",
            confidence=1.0,
            actual_value=Decimal("11552.00"),
            servicer_value=Decimal("12165.17"),
            difference=Decimal("613.17"),
            monthly_impact=Decimal("51.10"),
            explanation="The projected annual tax exceeds the issued tax bill.",
            evidence=[],
            relevant_sources=["REG_X_1024_17"],
            recommended_action="Review the tax projection against the issued bill.",
        ),
        retrieved_rules=[],
        observations=[],
    )

    decision = model.decide(request, {})

    assert (decision.tool_call is None) != (decision.resolution is None)
    assert decision.usage.input_tokens > 0
    assert decision.usage.output_tokens > 0
    assert decision.usage.cost_usd > 0
