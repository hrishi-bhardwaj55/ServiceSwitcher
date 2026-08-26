import os

import pytest

from app.llm import LLMExtractionRequest, LLMPage, OpenAIResponsesClient


@pytest.mark.llm
def test_real_provider_returns_schema_validated_fields():
    if not os.getenv("LLM_API_KEY") or not os.getenv("LLM_MODEL"):
        pytest.skip("LLM_API_KEY and LLM_MODEL are not configured")
    client = OpenAIResponsesClient.from_env()

    result = client.extract(
        LLMExtractionRequest(
            document_type="PROPERTY_TAX_BILL",
            requested_fields=["annual_tax_amount"],
            pages=[
                LLMPage(
                    page=1,
                    text="Property Tax Bill\nAnnual Amount Due\n$3,200.00",
                )
            ],
        )
    )

    assert result.document_type == "PROPERTY_TAX_BILL"
    assert result.fields[0].field_name == "annual_tax_amount"
    assert result.fields[0].page == 1
