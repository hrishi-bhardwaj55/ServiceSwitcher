"""Local response cache for resumable model-backed evaluations."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from threading import Lock

from app.llm.models import LLMExtractionRequest, LLMExtractionResponse
from app.llm.protocol import LLMClient


class CachedLLMClient:
    def __init__(self, delegate: LLMClient, path: Path, *, namespace: str) -> None:
        self.delegate = delegate
        self.path = path
        self.namespace = namespace
        self.hits = 0
        self.misses = 0
        self._responses = self._load()
        self._lock = Lock()

    def extract(self, request: LLMExtractionRequest) -> LLMExtractionResponse:
        key = self._key(request)
        with self._lock:
            cached = self._responses.get(key)
            if cached is not None:
                self.hits += 1
                return cached

        response = self.delegate.extract(request)
        with self._lock:
            cached = self._responses.get(key)
            if cached is not None:
                self.hits += 1
                return cached
            self.misses += 1
            self.path.parent.mkdir(parents=True, exist_ok=True)
            record = {
                "key": key,
                "response": response.model_dump(mode="json"),
            }
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, sort_keys=True) + "\n")
                handle.flush()
            self._responses[key] = response
        return response

    def _key(self, request: LLMExtractionRequest) -> str:
        material = f"{self.namespace}\0{request.model_dump_json()}".encode()
        return hashlib.sha256(material).hexdigest()

    def _load(self) -> dict[str, LLMExtractionResponse]:
        if not self.path.exists():
            return {}
        responses: dict[str, LLMExtractionResponse] = {}
        with self.path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                try:
                    record = json.loads(line)
                    responses[record["key"]] = LLMExtractionResponse.model_validate(
                        record["response"]
                    )
                except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
                    raise ValueError(
                        f"invalid model cache record at {self.path}:{line_number}"
                    ) from error
        return responses
