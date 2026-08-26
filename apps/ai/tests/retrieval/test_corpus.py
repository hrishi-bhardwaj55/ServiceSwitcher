from pathlib import Path

from app.retrieval import load_corpus

CORPUS = Path(__file__).parents[4] / "knowledge-base" / "chunks.jsonl"


def test_curated_corpus_has_required_size_sources_and_metadata():
    chunks = load_corpus(CORPUS)

    assert len(chunks) == 47
    assert all(chunk.section and chunk.title and chunk.url for chunk in chunks)
    assert any(chunk.section.startswith("12 CFR 1024.17") for chunk in chunks)
    assert any(chunk.section.startswith("12 CFR 1024.33") for chunk in chunks)
    assert any("1024.38" in chunk.section or "38(b)" in chunk.section for chunk in chunks)
    assert any(chunk.source == "CFPB Bulletin 2014-01" for chunk in chunks)
    assert all("legal conclusion" not in chunk.content.lower() for chunk in chunks)
