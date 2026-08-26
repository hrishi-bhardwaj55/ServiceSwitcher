"""Strict client boundary for deterministic reconciliation-engine tools."""

from __future__ import annotations

import json
import math
from collections.abc import Callable, Mapping
from decimal import Decimal
from typing import Literal, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import Field, field_validator

from app.schemas.mortgage import CanonicalModel, MortgageAccount

DEFAULT_ENGINE_URL = "http://127.0.0.1:8080"
DEFAULT_ENGINE_TIMEOUT_SECONDS = 10

FindingType = Literal[
    "ESCROW_BALANCE_MISMATCH",
    "PROPERTY_TAX_PROJECTION_MISMATCH",
    "ESCROW_SHORTAGE_CALCULATION_ERROR",
    "DUPLICATE_TAX_DISBURSEMENT",
    "UNEXPLAINED_PAYMENT_INCREASE",
    "EXPLAINED",
]
JsonObject = dict[str, object]
Transport = Callable[[str, JsonObject, int], Mapping[str, object]]


class EngineEvidence(CanonicalModel):
    document_id: str = Field(min_length=1)
    page: int = Field(ge=1)
    field: str = Field(min_length=1)
    value: Decimal | str | int | bool | None


class EngineFinding(CanonicalModel):
    finding_type: FindingType
    severity: Literal["LOW", "MEDIUM", "HIGH"]
    confidence: float = Field(ge=0, le=1)
    actual_value: Decimal | None
    servicer_value: Decimal | None
    difference: Decimal | None
    monthly_impact: Decimal | None
    explanation: str = Field(min_length=1)
    evidence: list[EngineEvidence]
    relevant_sources: list[str]
    recommended_action: str = Field(min_length=1)

    @field_validator("confidence", mode="before")
    @classmethod
    def confidence_must_be_finite(cls, value: object) -> object:
        if isinstance(value, (int, float)) and not math.isfinite(value):
            raise ValueError("confidence must be finite")
        return value


class PaymentDecomposition(CanonicalModel):
    payment_change: Decimal
    principal_interest_change: Decimal
    tax_change_monthly: Decimal
    insurance_change_monthly: Decimal
    shortage_monthly: Decimal
    residual: Decimal
    tolerance: Decimal = Field(ge=0)
    outcome: FindingType


class ReconciliationResult(CanonicalModel):
    findings: list[EngineFinding]
    payment_decomposition: PaymentDecomposition
    engine_version: str = Field(min_length=1)


class ReconciliationEngine(Protocol):
    def reconcile(
        self,
        account: MortgageAccount,
        transfer_date: str,
    ) -> ReconciliationResult: ...


class HttpReconciliationEngine:
    """Call only the engine's typed `/reconcile` endpoint."""

    def __init__(
        self,
        base_url: str = DEFAULT_ENGINE_URL,
        *,
        timeout: int = DEFAULT_ENGINE_TIMEOUT_SECONDS,
        transport: Transport | None = None,
    ) -> None:
        if not base_url.startswith(("http://", "https://")):
            raise ValueError("engine base_url must be HTTP(S)")
        if timeout < 1:
            raise ValueError("engine timeout must be positive")
        self.reconcile_url = f"{base_url.rstrip('/')}/reconcile"
        self.timeout = timeout
        self.transport = transport or _post_json

    def reconcile(
        self,
        account: MortgageAccount,
        transfer_date: str,
    ) -> ReconciliationResult:
        payload: JsonObject = {
            "account": account.model_dump(mode="json"),
            "transfer_date": transfer_date,
        }
        try:
            response = self.transport(self.reconcile_url, payload, self.timeout)
        except Exception as error:
            raise RuntimeError(f"reconciliation engine request failed: {error}") from error
        return ReconciliationResult.model_validate(response)


def _post_json(url: str, payload: JsonObject, timeout: int) -> Mapping[str, object]:
    request = Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            result = json.load(response)
    except HTTPError as error:
        body = error.read(1_000).decode(errors="replace")
        raise RuntimeError(f"engine returned HTTP {error.code}: {body}") from error
    except URLError as error:
        raise RuntimeError(f"cannot reach reconciliation engine: {error}") from error
    if not isinstance(result, Mapping):
        raise TypeError("reconciliation engine response is not a JSON object")
    return result
