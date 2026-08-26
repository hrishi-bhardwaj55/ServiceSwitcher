"""Framework-neutral contracts for safe, audit-scoped agent tools."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel

from app.schemas.mortgage import CanonicalModel

DEFAULT_MAX_OUTPUT_CHARS = 8_000
TRUNCATION_MARKER = "\n...[TRUNCATED]"
AUDIT_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")

type ToolHandler[ArgumentT: CanonicalModel] = Callable[[ArgumentT], object]


class ToolError(RuntimeError):
    """Base error surfaced by the bounded agent tool layer."""


class AuditScopeError(ToolError):
    """Raised before execution when an invocation crosses an audit boundary."""


class InformationNotFoundError(ToolError):
    """Raised when scoped audit data does not contain the requested information."""


@dataclass(frozen=True)
class ToolInvocationContext:
    """Trusted context supplied by the framework, never by the model."""

    audit_id: str

    def __post_init__(self) -> None:
        if not AUDIT_ID_PATTERN.fullmatch(self.audit_id):
            raise ValueError("framework audit_id is invalid")


class ToolOutput(CanonicalModel):
    tool: str
    content: str
    truncated: bool
    truncation_marker: str | None = None


class ScopedAgentTool[ArgumentT: CanonicalModel]:
    """Validate, scope, execute, serialize, and bound one model-visible tool."""

    def __init__(
        self,
        *,
        name: str,
        bound_audit_id: str,
        argument_model: type[ArgumentT],
        handler: ToolHandler[ArgumentT],
        max_output_chars: int = DEFAULT_MAX_OUTPUT_CHARS,
    ) -> None:
        if not re.fullmatch(r"[a-z][a-z0-9_]{1,63}", name):
            raise ValueError("tool name must be lower snake case")
        ToolInvocationContext(bound_audit_id)
        description = (handler.__doc__ or "").strip()
        if not description:
            raise ValueError(f"tool {name} must have a model-facing handler docstring")
        if max_output_chars <= len(TRUNCATION_MARKER):
            raise ValueError("tool output limit must leave room for the truncation marker")
        self.name = name
        self.bound_audit_id = bound_audit_id
        self.argument_model = argument_model
        self.handler = handler
        self.description = description
        self.max_output_chars = max_output_chars

    def argument_schema(self) -> dict[str, object]:
        """Return the strict model-visible JSON Schema; it never contains audit_id."""
        return self.argument_model.model_json_schema()

    def invoke(
        self,
        raw_arguments: Mapping[str, object],
        context: ToolInvocationContext,
    ) -> ToolOutput:
        if context.audit_id != self.bound_audit_id:
            raise AuditScopeError(
                f"tool {self.name} is bound to a different audit than the invocation"
            )
        arguments = self.argument_model.model_validate(raw_arguments)
        rendered = json.dumps(
            self.handler(arguments),
            default=_json_default,
            separators=(",", ":"),
            sort_keys=True,
        )
        if len(rendered) <= self.max_output_chars:
            return ToolOutput(tool=self.name, content=rendered, truncated=False)
        retained = self.max_output_chars - len(TRUNCATION_MARKER)
        return ToolOutput(
            tool=self.name,
            content=rendered[:retained] + TRUNCATION_MARKER,
            truncated=True,
            truncation_marker=TRUNCATION_MARKER.strip(),
        )


def _json_default(value: object) -> object:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    raise TypeError(f"tool output contains unsupported type {type(value).__name__}")
