from pathlib import Path

from app.llm import (
    CachedLLMClient,
    DeterministicFakeLLM,
    LLMExtractionRequest,
    LLMExtractionResponse,
    LLMPage,
)


def test_cached_client_resumes_without_calling_provider(tmp_path: Path):
    request = LLMExtractionRequest(
        document_type="TRANSFER_NOTICE",
        requested_fields=[],
        pages=[LLMPage(page=1, text="Servicing transfer notice")],
    )
    response = LLMExtractionResponse(
        document_type="TRANSFER_NOTICE",
        classification_confidence=0.95,
        fields=[],
    )
    cache_path = tmp_path / "responses.jsonl"
    first_fake = DeterministicFakeLLM([response])
    first = CachedLLMClient(first_fake, cache_path, namespace="test-v1")

    assert first.extract(request) == response
    assert first.hits == 0
    assert first.misses == 1
    first_fake.assert_exhausted()

    second_fake = DeterministicFakeLLM([])
    resumed = CachedLLMClient(second_fake, cache_path, namespace="test-v1")
    assert resumed.extract(request) == response
    assert resumed.hits == 1
    assert resumed.misses == 0
    assert second_fake.call_count == 0
