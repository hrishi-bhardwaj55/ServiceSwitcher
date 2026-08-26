from pathlib import Path

import pytest

from app.agents import DocumentRef, initial_audit_state


def _document(audit_id="audit-a", document_id="statement"):
    return DocumentRef(
        audit_id=audit_id,
        document_id=document_id,
        path=Path("statement.pdf"),
    )


def test_initial_state_has_exact_zeroed_budget_and_result_fields():
    state = initial_audit_state("audit-a", [_document()])

    assert state["audit_id"] == "audit-a"
    assert state["extracted_values"] == {}
    assert state["deterministic_findings"] == []
    assert state["ambiguous_findings"] == []
    assert state["retrieved_rules"] == []
    assert state["final_findings"] == []
    assert state["missing_information"] == []
    assert state["requires_review"] is False
    assert state["steps_used"] == 0
    assert str(state["cost_usd"]) == "0"


def test_initial_state_rejects_empty_cross_audit_and_duplicate_documents():
    with pytest.raises(ValueError, match="at least one"):
        initial_audit_state("audit-a", [])
    with pytest.raises(ValueError, match="belong"):
        initial_audit_state("audit-a", [_document("audit-b")])
    with pytest.raises(ValueError, match="unique"):
        initial_audit_state("audit-a", [_document(), _document()])
