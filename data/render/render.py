"""Render every canonical account into five PDFs using its assigned family."""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from pathlib import Path
from typing import Any

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen.canvas import Canvas

from data.render import family_a, family_b, family_c
from data.render.content import (
    DOCUMENT_TYPES,
    DocumentType,
    TemplateFamily,
    build_content,
    family_for_account,
)

EXPECTED_ACCOUNT_COUNT = 300
RENDERERS = {
    TemplateFamily.A: family_a.render,
    TemplateFamily.B: family_b.render,
    TemplateFamily.C: family_c.render,
}


def load_accounts(path: Path) -> list[dict[str, Any]]:
    files = sorted(path.glob("account-*.json"))
    accounts = [json.loads(file.read_text(encoding="utf-8")) for file in files]
    if not accounts:
        raise ValueError(f"no account JSON files found in {path}")
    return accounts


def render_document(
    account: dict[str, Any],
    document_type: DocumentType,
    family: TemplateFamily,
    output: Path,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.tmp")
    canvas = Canvas(
        str(temporary),
        pagesize=letter,
        pageCompression=1,
        invariant=1,
    )
    content = build_content(account, document_type, family)
    canvas.setAuthor("ServicerSwitch Synthetic Data Generator")
    canvas.setCreator("ServicerSwitch data.render")
    canvas.setTitle(f"{content.title} - {content.account_id}")
    canvas.setSubject(f"ServicerSwitch template family {family.value}")
    RENDERERS[family](canvas, content)
    canvas.save()
    os.replace(temporary, output)


def render_account(account: dict[str, Any], output: Path) -> TemplateFamily:
    family = family_for_account(account["account_id"])
    account_output = output / account["account_id"]
    for document_type in DOCUMENT_TYPES:
        render_document(
            account,
            document_type,
            family,
            account_output / document_type.filename,
        )
    return family


def render_corpus(accounts: list[dict[str, Any]], output: Path) -> Counter[TemplateFamily]:
    counts: Counter[TemplateFamily] = Counter()
    for account in accounts:
        counts[render_account(account, output)] += 1
    return counts


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--accounts", type=Path, default=Path("data/accounts"))
    parser.add_argument("--output", type=Path, default=Path("data/documents"))
    parser.add_argument("--expected-count", type=int, default=EXPECTED_ACCOUNT_COUNT)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    accounts = load_accounts(args.accounts)
    if len(accounts) != args.expected_count:
        raise ValueError(f"expected {args.expected_count} accounts; found {len(accounts)}")
    counts = render_corpus(accounts, args.output)
    rendered = len(accounts) * len(DOCUMENT_TYPES)
    distribution = ", ".join(f"Family {family.value}: {counts[family]}" for family in TemplateFamily)
    print(f"Rendered {rendered} PDFs for {len(accounts)} accounts in {args.output}")
    print(distribution)


if __name__ == "__main__":
    main()
