FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /service

COPY apps/ai/pyproject.toml ./
COPY apps/ai/app ./app
COPY apps/ai/alembic.ini ./
COPY apps/ai/alembic ./alembic
COPY knowledge-base/chunks.jsonl ./knowledge-base/chunks.jsonl
COPY knowledge-base/demo-embeddings.jsonl ./knowledge-base/demo-embeddings.jsonl

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
