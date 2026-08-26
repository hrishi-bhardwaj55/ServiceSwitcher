from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.mortgage import MortgageAccount
from app.tools.engine import HttpReconciliationEngine, ReconciliationResult


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
            "payments": [],
            "escrow_ledger": [],
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


def _response() -> dict[str, object]:
    return {
        "findings": [
            {
                "finding_type": "PROPERTY_TAX_PROJECTION_MISMATCH",
                "severity": "MEDIUM",
                "confidence": 1.0,
                "actual_value": "2400.00",
                "servicer_value": "2700.00",
                "difference": "300.00",
                "monthly_impact": "25.00",
                "explanation": "The projection exceeds the tax bill.",
                "evidence": [
                    {
                        "document_id": "property_tax_bill",
                        "page": 1,
                        "field": "annual_tax_amount",
                        "value": "2400.00",
                    }
                ],
                "relevant_sources": ["REG_X_1024_17"],
                "recommended_action": "Review the projection.",
            }
        ],
        "payment_decomposition": {
            "payment_change": "100.00",
            "principal_interest_change": "0.00",
            "tax_change_monthly": "25.00",
            "insurance_change_monthly": "0.00",
            "shortage_monthly": "75.00",
            "residual": "0.00",
            "tolerance": "10.00",
            "outcome": "EXPLAINED",
        },
        "engine_version": "1.0.0",
    }


def test_http_engine_sends_canonical_account_and_validates_response():
    requests = []

    def transport(url, payload, timeout):
        requests.append((url, payload, timeout))
        return _response()

    result = HttpReconciliationEngine(
        "http://engine:8080",
        timeout=7,
        transport=transport,
    ).reconcile(_account(), "2024-06-01")

    assert result.engine_version == "1.0.0"
    assert result.findings[0].difference == Decimal("300.00")
    assert requests[0][0] == "http://engine:8080/reconcile"
    assert requests[0][1]["account"]["account_id"] == "SS-TEST"
    assert requests[0][1]["transfer_date"] == "2024-06-01"
    assert requests[0][2] == 7


def test_http_engine_reads_deployment_base_url(monkeypatch):
    monkeypatch.setenv("ENGINE_API_BASE", "http://engine:8080/")

    client = HttpReconciliationEngine.from_env()

    assert client.reconcile_url == "http://engine:8080/reconcile"


def test_engine_response_rejects_unknown_fields_and_nonfinite_confidence():
    response = _response()
    response["unexpected"] = True
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        ReconciliationResult.model_validate(response)

    response = _response()
    response["findings"][0]["confidence"] = float("nan")
    with pytest.raises(ValidationError, match="confidence must be finite"):
        ReconciliationResult.model_validate(response)


def test_engine_response_accepts_null_action_for_explained_outcome():
    response = _response()
    response["findings"][0]["finding_type"] = "EXPLAINED"
    response["findings"][0]["recommended_action"] = None

    result = ReconciliationResult.model_validate(response)

    assert result.findings[0].recommended_action is None
