import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from app.llm import DeterministicFakeLLM, LLMExtractionResponse, LLMFieldCandidate

from data.generator.generate import generate_accounts
from data.render.content import DOCUMENT_TYPES, TemplateFamily
from data.render.ground_truth import (
    expected_extraction_fields,
    expected_extraction_pages,
)
from data.render.render import render_account
from evals.runners.extraction_eval import (
    HELD_OUT,
    IN_DISTRIBUTION,
    evaluate,
    render_calibration,
    render_report,
)


def test_hybrid_eval_keeps_development_and_heldout_metrics_separate(tmp_path: Path):
    generated = generate_accounts(count=5)
    accounts = [json.loads(generated[index].model_dump_json()) for index in (0, 2, 4)]
    for account in accounts:
        render_account(account, tmp_path)

    held_out_account = accounts[-1]
    responses = []
    for document_type in DOCUMENT_TYPES:
        extraction_type = document_type.value.upper()
        expected = expected_extraction_fields(held_out_account, extraction_type)
        pages = expected_extraction_pages(extraction_type, TemplateFamily.C)
        responses.append(
            LLMExtractionResponse(
                document_type=extraction_type,
                classification_confidence=0.97,
                fields=[
                    LLMFieldCandidate(
                        field_name=field_name,
                        raw_value=_raw_value(field_name, value),
                        page=pages[field_name],
                        confidence=0.96,
                    )
                    for field_name, value in expected.items()
                ],
            )
        )
    fake = DeterministicFakeLLM(responses)

    metrics = evaluate(accounts, tmp_path, fake)

    development = metrics[IN_DISTRIBUTION]
    held_out = metrics[HELD_OUT]
    assert len(development.accounts) == 2
    assert development.documents == 10
    assert development.classification_accuracy == Decimal(1)
    assert development.field_accuracy == Decimal(1)
    assert development.citation_accuracy == Decimal(1)
    assert development.fallback_rate == Decimal(0)
    assert len(held_out.accounts) == 1
    assert held_out.documents == 5
    assert held_out.classification_accuracy == Decimal(1)
    assert held_out.field_accuracy == Decimal(1)
    assert held_out.citation_accuracy == Decimal(1)
    assert held_out.fallback_rate == Decimal(1)
    assert "In-distribution (A/B)" in render_report(metrics, "fake")
    assert "Held-out (Family C)" in render_calibration(metrics, "fake")
    fake.assert_exhausted()


def _raw_value(field_name: str, value) -> str:
    if isinstance(value, tuple):
        return "; ".join(item.strftime("%b %d, %Y") for item in value)
    if isinstance(value, date):
        return value.strftime("%b %d, %Y")
    if isinstance(value, Decimal):
        if field_name == "interest_rate":
            return f"{value * Decimal(100)}%"
        return f"${value:,.2f}"
    return str(value)
