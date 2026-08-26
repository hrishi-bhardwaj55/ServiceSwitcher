from decimal import Decimal
from pathlib import Path

from reportlab.pdfgen.canvas import Canvas

from app.agents.documents import FallbackPdfDocumentProcessor
from app.agents.models import DocumentRef
from app.llm import DeterministicFakeLLM, LLMExtractionResponse, LLMFieldCandidate


def _write_unclassified_statement(path: Path) -> None:
    canvas = Canvas(str(path))
    canvas.drawString(72, 720, "Account snapshot")
    canvas.drawString(72, 690, "Principal $250,000.00")
    canvas.drawString(72, 670, "Rate 5.25%")
    canvas.drawString(72, 650, "Payment $2,100.00")
    canvas.drawString(72, 630, "Escrow $1,250.00")
    canvas.save()


def test_fallback_processor_classifies_once_and_preserves_page_only_provenance(tmp_path):
    path = tmp_path / "held-out.pdf"
    _write_unclassified_statement(path)
    fake = DeterministicFakeLLM(
        [
            LLMExtractionResponse(
                document_type="OLD_SERVICER_STATEMENT",
                classification_confidence=0.98,
                fields=[
                    LLMFieldCandidate(
                        field_name="principal_balance",
                        raw_value="$250,000.00",
                        page=1,
                        confidence=0.96,
                    ),
                    LLMFieldCandidate(
                        field_name="interest_rate",
                        raw_value="5.25%",
                        page=1,
                        confidence=0.96,
                    ),
                    LLMFieldCandidate(
                        field_name="monthly_payment",
                        raw_value="$2,100.00",
                        page=1,
                        confidence=0.96,
                    ),
                    LLMFieldCandidate(
                        field_name="escrow_balance",
                        raw_value="$1,250.00",
                        page=1,
                        confidence=0.96,
                    ),
                ],
            )
        ]
    )
    processor = FallbackPdfDocumentProcessor(fake)
    document = DocumentRef(audit_id="CASE-1", document_id="doc-old", path=path)

    classification = processor.classify(document)
    extraction = processor.extract(document)

    assert classification.document_type == "OLD_SERVICER_STATEMENT"
    assert extraction.document_type == classification.document_type
    assert extraction.model_fallback_triggered is True
    assert extraction.field_map()["principal_balance"].value == Decimal("250000.00")
    assert extraction.field_map()["principal_balance"].page == 1
    assert extraction.field_map()["principal_balance"].bounding_box is None
    assert fake.call_count == 1
    fake.assert_exhausted()
