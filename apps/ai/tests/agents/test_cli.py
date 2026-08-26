from pathlib import Path

import pytest

from app.agents.cli import DOCUMENT_IDS, document_refs, load_case

ROOT = Path(__file__).parents[4]


def test_load_case_selects_exact_ground_truth_record():
    case = load_case(ROOT / "data" / "ground_truth" / "cases.jsonl", "CASE-0042")

    assert case.case_id == "CASE-0042"
    assert case.account_id == "SS-0042"

    with pytest.raises(ValueError, match="found 0"):
        load_case(ROOT / "data" / "ground_truth" / "cases.jsonl", "CASE-9999")


def test_document_refs_bind_all_five_expected_pdfs_to_one_audit(tmp_path):
    references = document_refs(tmp_path, "CASE-0042", "SS-0042")

    assert len(references) == 5
    assert {reference.document_id for reference in references} == set(DOCUMENT_IDS.values())
    assert {reference.audit_id for reference in references} == {"CASE-0042"}
    assert {reference.path.parent for reference in references} == {tmp_path / "SS-0042"}
