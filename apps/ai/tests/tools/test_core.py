import pytest
from pydantic import Field, ValidationError

from app.schemas.mortgage import CanonicalModel
from app.tools import AuditScopeError, ScopedAgentTool, ToolInvocationContext
from app.tools.core import TRUNCATION_MARKER


class ExampleArgs(CanonicalModel):
    value: str = Field(min_length=1)


def _echo(arguments: ExampleArgs) -> dict[str, str]:
    """Echo one value for contract testing."""
    return {"value": arguments.value}


def test_tool_schema_is_strict_and_hides_framework_audit_id():
    tool = ScopedAgentTool(
        name="example_tool",
        bound_audit_id="audit-a",
        argument_model=ExampleArgs,
        handler=_echo,
    )

    schema = tool.argument_schema()

    assert "audit_id" not in str(schema)
    assert schema["additionalProperties"] is False
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        tool.invoke(
            {"value": "safe", "audit_id": "audit-b"},
            ToolInvocationContext("audit-a"),
        )


def test_tool_rejects_framework_scope_mismatch_before_handler_runs():
    calls = []

    def handler(arguments: ExampleArgs):
        """Record a call that must not occur across an audit boundary."""
        calls.append(arguments)
        return {}

    tool = ScopedAgentTool(
        name="example_tool",
        bound_audit_id="audit-a",
        argument_model=ExampleArgs,
        handler=handler,
    )

    with pytest.raises(AuditScopeError, match="different audit"):
        tool.invoke({"value": "safe"}, ToolInvocationContext("audit-b"))

    assert calls == []


def test_tool_bounds_oversized_output_with_explicit_marker():
    tool = ScopedAgentTool(
        name="example_tool",
        bound_audit_id="audit-a",
        argument_model=ExampleArgs,
        handler=_echo,
        max_output_chars=64,
    )

    output = tool.invoke({"value": "x" * 200}, ToolInvocationContext("audit-a"))

    assert output.truncated is True
    assert output.content.endswith(TRUNCATION_MARKER)
    assert output.truncation_marker == TRUNCATION_MARKER.strip()
    assert len(output.content) == 64
