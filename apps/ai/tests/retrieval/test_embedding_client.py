from app.embeddings import OpenAIEmbeddingClient


def test_openai_embedding_client_batches_and_validates_vectors():
    captured = {}

    def transport(url, headers, payload, timeout):
        captured.update(url=url, headers=headers, payload=payload, timeout=timeout)
        return {
            "data": [
                {"index": 1, "embedding": [0.0, 1.0]},
                {"index": 0, "embedding": [1.0, 0.0]},
            ]
        }

    client = OpenAIEmbeddingClient(
        api_key="test-key",
        model="test-embedding-model",
        dimensions=2,
        transport=transport,
    )

    assert client.embed(["first", "second"]) == [[1.0, 0.0], [0.0, 1.0]]
    assert captured["url"].endswith("/embeddings")
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["payload"]["dimensions"] == 2
    assert captured["payload"]["encoding_format"] == "float"
