"""Provider-neutral text embedding clients."""

from app.embeddings.fake import DeterministicFakeEmbeddingClient
from app.embeddings.openai import OpenAIEmbeddingClient
from app.embeddings.protocol import EmbeddingClient

__all__ = [
    "DeterministicFakeEmbeddingClient",
    "EmbeddingClient",
    "OpenAIEmbeddingClient",
]
