"""OpenAI embeddings implementation."""

from __future__ import annotations

import json
import math
import os
from collections.abc import Callable, Mapping
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_API_BASE = "https://api.openai.com/v1"
DEFAULT_MODEL = "text-embedding-3-small"
DEFAULT_DIMENSIONS = 512
DEFAULT_TIMEOUT_SECONDS = 60
JsonObject = dict[str, Any]
Transport = Callable[[str, Mapping[str, str], JsonObject, int], Mapping[str, Any]]


class OpenAIEmbeddingClient:
    def __init__(
        self,
        *,
        api_key: str,
        model: str = DEFAULT_MODEL,
        dimensions: int = DEFAULT_DIMENSIONS,
        api_base: str = DEFAULT_API_BASE,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
        transport: Transport | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("api_key is required")
        if not model:
            raise ValueError("model is required")
        if dimensions < 1:
            raise ValueError("dimensions must be positive")
        self.api_key = api_key
        self.model = model
        self.dimensions = dimensions
        self.api_base = api_base.rstrip("/")
        self.timeout = timeout
        self.transport = transport or _post_json

    @classmethod
    def from_env(cls) -> OpenAIEmbeddingClient:
        api_key = os.getenv("EMBEDDING_API_KEY") or os.getenv("LLM_API_KEY", "")
        if not api_key:
            raise RuntimeError("EMBEDDING_API_KEY or LLM_API_KEY is required")
        return cls(
            api_key=api_key,
            model=os.getenv("EMBEDDING_MODEL", DEFAULT_MODEL),
            dimensions=int(os.getenv("EMBEDDING_DIMENSIONS", str(DEFAULT_DIMENSIONS))),
            api_base=os.getenv("EMBEDDING_API_BASE", DEFAULT_API_BASE),
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts or any(not text.strip() for text in texts):
            raise ValueError("embedding input must contain non-empty texts")
        payload = {
            "input": texts,
            "model": self.model,
            "dimensions": self.dimensions,
            "encoding_format": "float",
        }
        failure = None
        try:
            response = self.transport(
                f"{self.api_base}/embeddings",
                {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                payload,
                self.timeout,
            )
        except Exception as error:
            failure = str(error).replace(self.api_key, "[REDACTED]")
        if failure is not None:
            raise RuntimeError(f"embedding provider request failed: {failure}")
        return _parse_embeddings(response, len(texts), self.dimensions)


def _parse_embeddings(
    response: Mapping[str, Any], expected_count: int, dimensions: int
) -> list[list[float]]:
    data = response.get("data")
    if not isinstance(data, list) or len(data) != expected_count:
        raise ValueError("embedding provider returned an unexpected result count")
    ordered = sorted(data, key=lambda item: item.get("index", -1))
    result: list[list[float]] = []
    for expected_index, item in enumerate(ordered):
        if not isinstance(item, Mapping) or item.get("index") != expected_index:
            raise ValueError("embedding provider returned invalid indexes")
        vector = item.get("embedding")
        if not isinstance(vector, list) or len(vector) != dimensions:
            raise ValueError("embedding provider returned invalid dimensions")
        converted = [float(value) for value in vector]
        if not all(math.isfinite(value) for value in converted):
            raise ValueError("embedding provider returned a non-finite value")
        result.append(converted)
    return result


def _post_json(
    url: str,
    headers: Mapping[str, str],
    payload: JsonObject,
    timeout: int,
) -> Mapping[str, Any]:
    request = Request(
        url,
        data=json.dumps(payload).encode(),
        headers=dict(headers),
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            result = json.load(response)
    except HTTPError as error:
        body = error.read().decode(errors="replace")
        raise RuntimeError(f"embedding provider returned HTTP {error.code}: {body}") from error
    except URLError as error:
        raise RuntimeError(f"cannot reach embedding provider: {error}") from error
    if not isinstance(result, Mapping):
        raise TypeError("embedding provider response is not a JSON object")
    return result
