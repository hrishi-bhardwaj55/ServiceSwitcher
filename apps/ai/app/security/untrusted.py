"""Collision-safe prompt delimiters for attacker-controlled context."""

from __future__ import annotations

import json
import re

TAG_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]{2,63}$")


def wrap_untrusted_json(tag: str, value: object) -> str:
    """Serialize untrusted data so its contents cannot close the outer delimiter."""

    if TAG_PATTERN.fullmatch(tag) is None:
        raise ValueError("untrusted-data tag must be an uppercase identifier")
    encoded = json.dumps(value, ensure_ascii=True, separators=(",", ":"))
    encoded = encoded.replace("<", r"\u003c").replace(">", r"\u003e")
    return f'<{tag} encoding="json">\n{encoded}\n</{tag}>'
