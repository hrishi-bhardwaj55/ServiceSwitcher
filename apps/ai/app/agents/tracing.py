"""Append-only, bounded trajectory logging for investigator decisions."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from threading import Lock
from typing import Literal

from pydantic import Field

from app.schemas.mortgage import CanonicalModel
from app.tools.core import AUDIT_ID_PATTERN

MAX_RESULT_SUMMARY_CHARS = 500


class TrajectoryEvent(CanonicalModel):
    timestamp: datetime
    audit_id: str
    event: Literal["tool_call", "model_resolution", "budget_exhausted"]
    finding_type: str
    status: Literal["ok", "error", "rejected", "stopped"]
    tool: str | None = None
    arguments: dict[str, object] = Field(default_factory=dict)
    result_summary: str = ""
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    cost_usd: Decimal = Field(default=Decimal("0"), ge=0)
    cumulative_cost_usd: Decimal = Field(default=Decimal("0"), ge=0)
    steps_used: int = Field(ge=0)


class TrajectoryLogger:
    def __init__(self, root: Path, audit_id: str) -> None:
        if not AUDIT_ID_PATTERN.fullmatch(audit_id):
            raise ValueError("trajectory audit_id is invalid")
        self.path = root / f"{audit_id}.jsonl"
        self.audit_id = audit_id
        self._lock = Lock()

    def append(self, **values) -> TrajectoryEvent:
        summary = str(values.get("result_summary", ""))
        if len(summary) > MAX_RESULT_SUMMARY_CHARS:
            summary = summary[: MAX_RESULT_SUMMARY_CHARS - 15] + "...[TRUNCATED]"
        event = TrajectoryEvent(
            timestamp=datetime.now(UTC),
            audit_id=self.audit_id,
            **{**values, "result_summary": summary},
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock, self.path.open("a", encoding="utf-8") as handle:
            handle.write(event.model_dump_json() + "\n")
        return event
