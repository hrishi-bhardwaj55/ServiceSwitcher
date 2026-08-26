import json
from decimal import Decimal
from pathlib import Path

from data.generator.generate import generate_accounts
from data.render.content import DOCUMENT_TYPES, TemplateFamily, family_for_account
from data.render.ground_truth import expected_extraction_fields
from data.render.render import render_account

from app.extraction import extract_document

FIELD_ACCURACY_FLOOR = Decimal("0.98")
CLASSIFICATION_ACCURACY_FLOOR = Decimal("0.99")
DOCUMENT_NAMES = {
    document_type: document_type.value.upper() for document_type in DOCUMENT_TYPES
}


def test_deterministic_extraction_accuracy_with_provenance(tmp_path: Path):
    accounts = [
        json.loads(account.model_dump_json())
        for account in generate_accounts(count=25)
        if family_for_account(account.account_id) in {TemplateFamily.A, TemplateFamily.B}
    ]
    correct_classifications = 0
    correct_fields = 0
    total_fields = 0

    for account in accounts:
        render_account(account, tmp_path)
        for document_type in DOCUMENT_TYPES:
            result = extract_document(
                tmp_path / account["account_id"] / document_type.filename
            )
            if result.document_type == DOCUMENT_NAMES[document_type]:
                correct_classifications += 1
            extracted = result.field_map()
            expected = expected_extraction_fields(
                account, DOCUMENT_NAMES[document_type]
            )
            total_fields += len(expected)
            for field_name, expected_value in expected.items():
                field = extracted.get(field_name)
                if field is not None and field.value == expected_value:
                    correct_fields += 1
                if field is not None:
                    assert field.page >= 1
                    assert field.bounding_box.x1 > field.bounding_box.x0
                    assert field.bounding_box.y1 > field.bounding_box.y0
                    assert 0 <= field.confidence <= 1

    document_count = len(accounts) * len(DOCUMENT_TYPES)
    classification_accuracy = Decimal(correct_classifications) / document_count
    field_accuracy = Decimal(correct_fields) / total_fields

    assert classification_accuracy >= CLASSIFICATION_ACCURACY_FLOOR
    assert field_accuracy >= FIELD_ACCURACY_FLOOR
