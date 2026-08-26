"""Canonical schemas shared by data generation and the AI service."""

from app.schemas.ground_truth import GroundTruthCase
from app.schemas.mortgage import (
    EscrowAnalysis,
    EscrowTransaction,
    InsurancePolicy,
    MortgageAccount,
    Payment,
    Servicer,
    ServicingPeriod,
    TaxBill,
)

__all__ = [
    "EscrowAnalysis",
    "EscrowTransaction",
    "GroundTruthCase",
    "InsurancePolicy",
    "MortgageAccount",
    "Payment",
    "Servicer",
    "ServicingPeriod",
    "TaxBill",
]
