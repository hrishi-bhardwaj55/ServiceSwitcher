import json
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
from data.generator.generate import generate_accounts
from data.render.render import render_account
from reportlab.pdfgen.canvas import Canvas

from app.extraction.fallback import extract_with_fallback
from app.extraction.models import BoundingBox, ExtractedField
from app.llm import DeterministicFakeLLM, LLMExtractionResponse, LLMFieldCandidate


def _response(document_type, fields):
    return LLMExtractionResponse(
        document_type=document_type,
        classification_confidence=0.98,
        fields=[
            LLMFieldCandidate(
                field_name=field_name,
                raw_value=value,
                page=page,
                confidence=confidence,
            )
            for field_name, value, page, confidence in fields
        ],
    )


def _write_sparse_statement(path: Path) -> None:
    canvas = Canvas(str(path))
    canvas.drawString(72, 720, "Final Mortgage Statement")
    canvas.drawString(72, 690, "Recent Escrow Activity")
    canvas.save()


def test_high_confidence_deterministic_fields_do_not_trigger_fallback(tmp_path: Path):
    account = json.loads(generate_accounts(count=1)[0].model_dump_json())
    render_account(account, tmp_path)
    fake = DeterministicFakeLLM([])

    result = extract_with_fallback(
        tmp_path / account["account_id"] / "old_servicer_statement.pdf",
        fake,
    )

    assert not result.llm_fallback_triggered
    assert fake.call_count == 0
    assert len(result.fields) == 4
    assert all(field.source == "DETERMINISTIC" for field in result.fields)
    assert not result.requires_review


def test_missing_fields_are_filled_by_fake_client(tmp_path: Path):
    document = tmp_path / "sparse.pdf"
    _write_sparse_statement(document)
    fake = DeterministicFakeLLM(
        [
            _response(
                "OLD_SERVICER_STATEMENT",
                [
                    ("principal_balance", "$250,000.00", 1, 0.92),
                    ("interest_rate", "5.2500%", 1, 0.91),
                    ("monthly_payment", "$2,100.00", 1, 0.90),
                    ("escrow_balance", "$1,250.00", 1, 0.93),
                ],
            )
        ]
    )

    result = extract_with_fallback(document, fake)

    assert result.llm_fallback_triggered
    assert result.field_map()["principal_balance"].value == Decimal("250000.00")
    assert result.field_map()["interest_rate"].value == Decimal("0.0525")
    assert all(field.source == "LLM" for field in result.fields)
    assert not result.missing_fields
    assert not result.requires_review
    assert set(fake.requests[0].requested_fields) == {
        "principal_balance",
        "interest_rate",
        "monthly_payment",
        "escrow_balance",
    }
    fake.assert_exhausted()


def test_disagreement_is_low_confidence_and_requires_review(tmp_path: Path):
    account = json.loads(generate_accounts(count=1)[0].model_dump_json())
    render_account(account, tmp_path)
    expected_principal = account["current_principal"]
    fake = DeterministicFakeLLM(
        [
            _response(
                "OLD_SERVICER_STATEMENT",
                [
                    ("principal_balance", "$1.00", 1, 0.99),
                    ("interest_rate", f"{Decimal(account['annual_rate']) * 100}%", 1, 0.99),
                    ("monthly_payment", account["payments"][4]["total"], 1, 0.99),
                    (
                        "escrow_balance",
                        account["escrow_analyses"][-2]["current_balance"],
                        1,
                        0.99,
                    ),
                ],
            )
        ]
    )

    result = extract_with_fallback(
        tmp_path / account["account_id"] / "old_servicer_statement.pdf",
        fake,
        field_threshold=0.96,
    )

    principal = result.field_map()["principal_balance"]
    assert principal.value == Decimal(expected_principal)
    assert principal.source == "CONFLICT"
    assert principal.confidence <= 0.49
    assert principal.requires_review
    assert len(principal.alternatives) == 2
    assert result.requires_review


def test_invalid_model_value_is_rejected_and_left_missing(tmp_path: Path):
    document = tmp_path / "sparse.pdf"
    _write_sparse_statement(document)
    fake = DeterministicFakeLLM(
        [
            _response(
                "OLD_SERVICER_STATEMENT",
                [("principal_balance", "not money", 4, 0.99)],
            )
        ]
    )

    result = extract_with_fallback(document, fake)

    assert "principal_balance" in result.rejected_fields
    assert "principal_balance" in result.missing_fields
    assert result.requires_review


def test_model_can_classify_when_keyword_classifier_cannot(tmp_path: Path):
    document = tmp_path / "unknown.pdf"
    canvas = Canvas(str(document))
    canvas.drawString(72, 720, "Account correspondence")
    canvas.save()
    fake = DeterministicFakeLLM(
        [
            _response(
                "TRANSFER_NOTICE",
                [
                    ("old_servicer_name", "Atlantic Home", 1, 0.95),
                    ("new_servicer_name", "Harbor Loan", 1, 0.95),
                    ("transfer_date", "June 1, 2024", 1, 0.95),
                ],
            )
        ]
    )

    result = extract_with_fallback(document, fake)

    assert result.document_type == "TRANSFER_NOTICE"
    assert result.classification_source == "LLM"
    assert set(result.field_map()) == {
        "old_servicer_name",
        "new_servicer_name",
        "transfer_date",
    }


def test_low_classification_confidence_requests_no_high_confidence_fields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    document = tmp_path / "classified.pdf"
    _write_sparse_statement(document)
    deterministic = SimpleNamespace(
        document_type="OLD_SERVICER_STATEMENT",
        classification_confidence=0.70,
        field_map=lambda: {
            "principal_balance": ExtractedField(
                field_name="principal_balance",
                value=Decimal("250000.00"),
                page=1,
                bounding_box=BoundingBox(x0=1, y0=1, x1=2, y1=2),
                confidence=0.95,
                source_text="$250,000.00",
            )
        },
    )
    monkeypatch.setattr(
        "app.extraction.fallback.extract_document", lambda _path: deterministic
    )
    fake = DeterministicFakeLLM(
        [
            _response(
                "OLD_SERVICER_STATEMENT",
                [
                    ("interest_rate", "5.2500%", 1, 0.95),
                    ("monthly_payment", "$2,100.00", 1, 0.95),
                    ("escrow_balance", "$1,250.00", 1, 0.95),
                ],
            )
        ]
    )

    result = extract_with_fallback(document, fake)

    assert fake.requests[0].requested_fields == [
        "interest_rate",
        "monthly_payment",
        "escrow_balance",
    ]
    assert result.field_map()["principal_balance"].source == "DETERMINISTIC"


def test_low_confidence_model_only_field_requires_review(tmp_path: Path):
    document = tmp_path / "sparse.pdf"
    _write_sparse_statement(document)
    fake = DeterministicFakeLLM(
        [
            _response(
                "OLD_SERVICER_STATEMENT",
                [("principal_balance", "$250,000.00", 1, 0.40)],
            )
        ]
    )

    result = extract_with_fallback(document, fake)

    principal = result.field_map()["principal_balance"]
    assert principal.requires_review
    assert result.requires_review
