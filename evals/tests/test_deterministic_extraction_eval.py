import json
from decimal import Decimal
from pathlib import Path

from data.generator.generate import generate_accounts
from data.render.content import TemplateFamily
from data.render.render import render_account
from evals.runners.deterministic_extraction_eval import evaluate, render_report


def test_evaluation_scores_both_development_layouts(tmp_path: Path):
    generated = generate_accounts(count=3)
    accounts = [
        json.loads(generated[index].model_dump_json())
        for index in (0, 2)
    ]
    for account in accounts:
        render_account(account, tmp_path)

    metrics = evaluate(accounts, tmp_path)

    for family in (TemplateFamily.A, TemplateFamily.B):
        result = metrics[family]
        assert result.accounts == 1
        assert result.documents == 5
        assert result.total_fields == 17
        assert result.classification_accuracy == Decimal(1)
        assert result.field_accuracy == Decimal(1)
        assert result.provenance_coverage == Decimal(1)
        assert result.meets_floor
    assert "**Acceptance verdict: PASS.**" in render_report(metrics)
