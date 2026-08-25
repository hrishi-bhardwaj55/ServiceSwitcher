"""FastAPI application entry point."""

from fastapi import FastAPI
from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Stable health-check response shared with tests and container probes."""

    service: str
    status: str


app = FastAPI(title="ServicerSwitch AI", version="0.1.0")


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    """Report process health without touching external dependencies."""

    return HealthResponse(service="ai", status="ok")
