import pytest

from app.extraction.classifier import UnclassifiedDocumentError, classify_document


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("FINAL MORTGAGE STATEMENT\nRECENT ESCROW ACTIVITY", "OLD_SERVICER_STATEMENT"),
        (
            "MONTHLY LOAN ACCOUNT STATEMENT\nPOST-TRANSFER ESCROW ACTIVITY",
            "NEW_SERVICER_STATEMENT",
        ),
        ("NOTICE OF SERVICING TRANSFER\nEFFECTIVE TRANSFER DATE", "TRANSFER_NOTICE"),
        (
            "ANNUAL ESCROW ACCOUNT ANALYSIS\n12-MONTH PROJECTED TRIAL BALANCE",
            "ESCROW_ANALYSIS",
        ),
        ("REAL PROPERTY TAX ASSESSMENT\nTOTAL TAX LEVY", "PROPERTY_TAX_BILL"),
    ],
)
def test_keyword_classifier(text, expected):
    result = classify_document(text)

    assert result.document_type == expected
    assert 0 <= result.confidence <= 1
    assert result.matched_signatures


def test_classifier_rejects_unknown_text():
    with pytest.raises(UnclassifiedDocumentError, match="unique keyword signature"):
        classify_document("unrelated correspondence")
