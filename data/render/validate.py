"""Validate page counts and extractable canonical values in rendered PDFs."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from data.render.content import (
    DOCUMENT_TYPES,
    DocumentType,
    TemplateFamily,
    build_content,
    expected_page_count,
    family_for_account,
)
from data.render.render import EXPECTED_ACCOUNT_COUNT, load_accounts


def validate_document(
    account: dict,
    document_type: DocumentType,
    family: TemplateFamily,
    path: Path,
) -> list[str]:
    errors: list[str] = []
    if not path.is_file():
        return [f"missing {path}"]
    try:
        reader = PdfReader(path)
    except (OSError, PdfReadError) as error:
        return [f"cannot open {path}: {error}"]

    expected_pages = expected_page_count(family, document_type)
    if len(reader.pages) != expected_pages:
        errors.append(f"{path}: expected {expected_pages} pages; found {len(reader.pages)}")
    if reader.is_encrypted:
        errors.append(f"{path}: generated PDF must not be encrypted")

    subject = (reader.metadata or {}).get("/Subject")
    expected_subject = f"ServicerSwitch template family {family.value}"
    if subject != expected_subject:
        errors.append(f"{path}: expected subject {expected_subject!r}; found {subject!r}")

    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    if not text.strip():
        errors.append(f"{path}: contains no extractable text")
        return errors
    content = build_content(account, document_type, family)
    for expected in content.required_values:
        if expected not in text:
            errors.append(f"{path}: missing extractable value {expected!r}")
    return errors


def validate_account_documents(account: dict, documents: Path) -> list[str]:
    family = family_for_account(account["account_id"])
    account_path = documents / account["account_id"]
    errors: list[str] = []
    for document_type in DOCUMENT_TYPES:
        errors.extend(
            validate_document(
                account,
                document_type,
                family,
                account_path / document_type.filename,
            )
        )
    return errors


def validate_corpus(accounts: list[dict], documents: Path) -> tuple[list[str], Counter]:
    errors: list[str] = []
    counts: Counter[TemplateFamily] = Counter()
    expected_paths: set[Path] = set()
    for account in accounts:
        family = family_for_account(account["account_id"])
        counts[family] += 1
        errors.extend(validate_account_documents(account, documents))
        expected_paths.update(
            documents / account["account_id"] / document_type.filename
            for document_type in DOCUMENT_TYPES
        )
    actual_paths = set(documents.glob("SS-*/*.pdf"))
    for unexpected in sorted(actual_paths - expected_paths):
        errors.append(f"unexpected generated PDF {unexpected}")
    return errors, counts


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--accounts", type=Path, default=Path("data/accounts"))
    parser.add_argument("--documents", type=Path, default=Path("data/documents"))
    parser.add_argument("--expected-count", type=int, default=EXPECTED_ACCOUNT_COUNT)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    accounts = load_accounts(args.accounts)
    if len(accounts) != args.expected_count:
        raise ValueError(f"expected {args.expected_count} accounts; found {len(accounts)}")
    errors, counts = validate_corpus(accounts, args.documents)
    if errors:
        preview = "\n".join(f"- {error}" for error in errors[:25])
        remainder = len(errors) - 25
        if remainder > 0:
            preview += f"\n- ... and {remainder} more"
        raise SystemExit(f"document validation failed with {len(errors)} errors:\n{preview}")
    total = len(accounts) * len(DOCUMENT_TYPES)
    distribution = ", ".join(f"Family {family.value}: {counts[family]}" for family in TemplateFamily)
    print(f"Validated {total}/{total} PDFs across {len(accounts)} accounts")
    print(distribution)


if __name__ == "__main__":
    main()
