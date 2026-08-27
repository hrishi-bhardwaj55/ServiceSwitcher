from app.security import authorization_headers


def test_authorization_headers_preserve_value_and_redact_diagnostics():
    headers = authorization_headers("top-secret-key")

    assert headers["Authorization"] == "Bearer top-secret-key"
    assert headers["Content-Type"] == "application/json"
    assert "top-secret-key" not in repr(headers)
    assert "top-secret-key" not in str(headers)
    assert "[REDACTED]" in repr(headers)
