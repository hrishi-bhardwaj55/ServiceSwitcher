"""Tests for machine-readable reconciliation labels."""

from decimal import Decimal

from app.schemas import GroundTruthCase


def test_clean_but_tricky_case_has_no_finding() -> None:
    case = GroundTruthCase(
        case_id="CASE-0042",
        account_id="SS-0042",
        bucket="clean_but_tricky",
        expected_findings=[],
        expected_impact_total=Decimal("0.00"),
        expected_monthly_impact=Decimal("0.00"),
        evidence_documents=[],
        tricky_condition="LEGITIMATE_TAX_REASSESSMENT",
    )

    assert '"expected_impact_total":"0.00"' in case.model_dump_json()
