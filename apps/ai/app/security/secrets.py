"""Secret-bearing request values with safe diagnostic representations."""


class RedactedHeaders(dict[str, str]):
    """Preserve real header values while keeping tracebacks safe to display."""

    def __repr__(self) -> str:
        safe = {
            name: "[REDACTED]" if name.casefold() == "authorization" else value
            for name, value in self.items()
        }
        return repr(safe)

    __str__ = __repr__


def authorization_headers(api_key: str) -> RedactedHeaders:
    if not api_key:
        raise ValueError("api_key is required")
    return RedactedHeaders(
        {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
    )
