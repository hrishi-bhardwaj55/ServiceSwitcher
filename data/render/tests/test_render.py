import json
import random
from collections import Counter
from pathlib import Path

from pypdf import PdfReader

from data.generator.generate import generate_account
from data.render.check_heldout import find_references
from data.render.content import DOCUMENT_TYPES, TemplateFamily, family_for_account
from data.render.render import render_account
from data.render.validate import validate_account_documents


def _account(index: int) -> dict:
    return json.loads(generate_account(index, random.Random(index)).model_dump_json())


def test_family_assignment_is_stable_and_balanced():
    counts = Counter(family_for_account(f"SS-{number:04d}") for number in range(1, 301))

    assert counts == {
        TemplateFamily.A: 120,
        TemplateFamily.B: 120,
        TemplateFamily.C: 60,
    }


def test_each_family_renders_five_valid_documents(tmp_path: Path):
    accounts = [_account(index) for index in (0, 2, 4)]

    for account in accounts:
        render_account(account, tmp_path)
        assert validate_account_documents(account, tmp_path) == []

    assert len(list(tmp_path.glob("SS-*/*.pdf"))) == len(accounts) * len(DOCUMENT_TYPES)


def test_families_are_visibly_and_structurally_distinct(tmp_path: Path):
    accounts = [_account(index) for index in (0, 2, 4)]
    paths = []
    for account in accounts:
        render_account(account, tmp_path)
        paths.append(tmp_path / account["account_id"] / "old_servicer_statement.pdf")

    family_a = PdfReader(paths[0])
    family_b = PdfReader(paths[1])
    family_c = PdfReader(paths[2])

    assert len(family_a.pages) == 2
    assert len(family_b.pages) == 1
    assert len(family_c.pages) == 2
    assert "LOAN OVERVIEW" in family_a.pages[0].extract_text()
    assert "ACCOUNT SNAPSHOT / PAYMENT DATA" in family_b.pages[0].extract_text()
    assert "DETAIL SCHEDULE" in family_c.pages[0].extract_text()
    assert "ACCOUNT SUMMARY" in family_c.pages[1].extract_text()


def test_heldout_checker_detects_ai_reference(tmp_path: Path):
    ai_root = tmp_path / "apps" / "ai"
    ai_root.mkdir(parents=True)
    (ai_root / "safe.py").write_text("TEMPLATE = 'development'\n", encoding="utf-8")
    assert find_references(ai_root) == []

    leaked = ai_root / "prompt.md"
    leaked.write_text("Use family_c labels.\n", encoding="utf-8")
    assert find_references(ai_root) == [f"{leaked}:1"]
