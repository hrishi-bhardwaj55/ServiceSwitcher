"""Regulatory knowledge ingestion and retrieval."""

from app.retrieval.corpus import load_corpus
from app.retrieval.models import RuleChunk

__all__ = ["RuleChunk", "load_corpus"]
