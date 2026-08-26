"""Fail when held-out Family C knowledge appears under the AI application."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

FORBIDDEN = re.compile(r"family[\s_-]*c", re.IGNORECASE)
TEXT_SUFFIXES = {".md", ".py", ".txt", ".toml", ".yaml", ".yml", ".json"}


def find_references(root: Path) -> list[str]:
    references: list[str] = []
    for path in sorted(item for item in root.rglob("*") if item.suffix in TEXT_SUFFIXES):
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if FORBIDDEN.search(line):
                references.append(f"{path}:{line_number}")
    return references


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ai-root", type=Path, default=Path("apps/ai"))
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    references = find_references(args.ai_root)
    if references:
        locations = "\n".join(f"- {reference}" for reference in references)
        raise SystemExit(f"held-out template reference found under {args.ai_root}:\n{locations}")
    print(f"Held-out template isolation check passed for {args.ai_root}")


if __name__ == "__main__":
    main()
