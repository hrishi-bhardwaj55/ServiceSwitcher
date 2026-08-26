"""Machine-readable labels for synthetic reconciliation cases."""

from decimal import Decimal
from typing import Annotated, Literal

from pydantic import Field, model_validator

from app.schemas.mortgage import CanonicalModel

FindingType = Literal[
    "ESCROW_BALANCE_MISMATCH",
    "PROPERTY_TAX_PROJECTION_MISMATCH",
    "ESCROW_SHORTAGE_CALCULATION_ERROR",
    "DUPLICATE_TAX_DISBURSEMENT",
    "UNEXPLAINED_PAYMENT_INCREASE",
]
CaseBucket = Literal["faulted", "clean", "clean_but_tricky"]
TrickyCondition = Literal[
    "LEGITIMATE_TAX_REASSESSMENT",
    "LEGITIMATE_INSURANCE_PREMIUM_JUMP",
    "DISTINCT_TAX_AUTHORITIES_CLOSE_TOGETHER",
    "FULLY_EXPLAINED_PAYMENT_INCREASE",
]
GroundTruthMoney = Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=2)]


class GroundTruthCase(CanonicalModel):
    case_id: str = Field(pattern=r"^CASE-\d{4}$")
    account_id: str = Field(pattern=r"^SS-\d{4}$")
    bucket: CaseBucket
    expected_findings: list[FindingType] = Field(max_length=1)
    expected_impact_total: GroundTruthMoney
    expected_monthly_impact: GroundTruthMoney
    evidence_documents: list[str]
    tricky_condition: TrickyCondition | None = None

    @model_validator(mode="after")
    def validate_bucket_label(self) -> "GroundTruthCase":
        if self.bucket == "faulted" and len(self.expected_findings) != 1:
            raise ValueError("faulted cases require exactly one expected finding")
        if self.bucket != "faulted" and self.expected_findings:
            raise ValueError("clean cases cannot carry expected findings")
        if self.bucket == "clean_but_tricky" and self.tricky_condition is None:
            raise ValueError("clean-but-tricky cases require a condition label")
        if self.bucket != "clean_but_tricky" and self.tricky_condition is not None:
            raise ValueError("only clean-but-tricky cases carry a condition label")
        return self
