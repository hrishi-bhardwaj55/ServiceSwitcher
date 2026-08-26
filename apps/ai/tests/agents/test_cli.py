from pathlib import Path

import pytest

from app.agents.cli import DOCUMENT_IDS, document_refs, load_case
from app.schemas.ground_truth import GroundTruthCase


def test_load_case_selects_exact_ground_truth_record(tmp_path: Path):
    cases_path = tmp_path / "cases.jsonl"
    expected = GroundTruthCase(
        case_id="CASE-0042",
        account_id="SS-0042",
        bucket="clean",
        expected_findings=[],
        expected_impact_total="0.00",
        expected_monthly_impact="0.00",
        evidence_documents=[],
    )
    cases_path.write_text(expected.model_dump_json() + "\n", encoding="utf-8")

    case = load_case(cases_path, "CASE-0042")

    assert case.case_id == "CASE-0042"
    assert case.account_id == "SS-0042"

    with pytest.raises(ValueError, match="found 0"):
        load_case(cases_path, "CASE-9999")


def test_document_refs_bind_all_five_expected_pdfs_to_one_audit(tmp_path):
    references = document_refs(tmp_path, "CASE-0042", "SS-0042")

    assert len(references) == 5
    assert {reference.document_id for reference in references} == set(DOCUMENT_IDS.values())
    assert {reference.audit_id for reference in references} == {"CASE-0042"}
    assert {reference.path.parent for reference in references} == {tmp_path / "SS-0042"}
