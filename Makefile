PYTHON ?= python3

.PHONY: up down verify lint-ai test-engine test-ai test-extraction test-retrieval test-tools test-agent test-data test-faults test-render test-evals test-web generate-accounts validate-accounts inject-faults validate-ground-truth eval-engine render-documents validate-documents check-heldout-isolation eval-extraction-deterministic eval-extraction db-migrate ingest-kb eval-rag run-audit eval-all eval-baseline

up:
	docker compose up --build -d

down:
	docker compose down

verify: lint-ai test-engine test-ai test-data test-faults test-render test-evals test-web check-heldout-isolation
	@echo "VERIFY OK"

lint-ai:
	$(PYTHON) -m ruff check apps/ai data/generator data/faults data/render evals

test-engine:
	cd apps/engine && ./mvnw -B -ntp test

test-ai:
	$(PYTHON) -W error -m pytest -p no:cacheprovider -m "not llm" apps/ai

test-extraction:
	$(PYTHON) -W error -m pytest -p no:cacheprovider -m "not llm" apps/ai/tests/extraction

test-retrieval:
	$(PYTHON) -W error -m pytest -p no:cacheprovider apps/ai/tests/retrieval

test-tools:
	$(PYTHON) -W error -m pytest -p no:cacheprovider apps/ai/tests/tools

test-agent:
	$(PYTHON) -W error -m pytest -p no:cacheprovider apps/ai/tests/agents

db-migrate:
	$(PYTHON) -m alembic -c apps/ai/alembic.ini upgrade head

ingest-kb: db-migrate test-retrieval
	$(PYTHON) -m app.retrieval.ingest --corpus knowledge-base/chunks.jsonl

eval-rag: ingest-kb test-evals
	$(PYTHON) -m evals.runners.rag_eval

run-audit: validate-documents test-agent
	@test -n "$(CASE)" || (echo "CASE is required, for example CASE=CASE-0042" && exit 2)
	docker compose up -d --wait postgres engine
	$(PYTHON) -m alembic -c apps/ai/alembic.ini upgrade head
	$(PYTHON) -m app.agents.cli --case $(CASE)

eval-all: validate-documents test-agent test-evals
	docker compose up -d --wait postgres engine
	$(PYTHON) -m alembic -c apps/ai/alembic.ini upgrade head
	$(PYTHON) -m evals.runners.agent_eval

eval-baseline: validate-documents test-evals
	$(PYTHON) -m evals.runners.baseline_eval

generate-accounts:
	$(PYTHON) -m data.generator.generate --output data/accounts --count 300 --seed 20250825

validate-accounts:
	$(PYTHON) -m data.generator.validate --input data/accounts --expected-count 300

test-data: generate-accounts validate-accounts
	$(PYTHON) -W error -m pytest -p no:cacheprovider data/generator/tests

inject-faults: generate-accounts
	$(PYTHON) -m data.faults.inject --input data/accounts --output data/accounts --ground-truth data/ground_truth/cases.jsonl

validate-ground-truth: inject-faults
	$(PYTHON) -m data.faults.validate --accounts data/accounts --ground-truth data/ground_truth/cases.jsonl

test-faults: validate-ground-truth
	$(PYTHON) -W error -m pytest -p no:cacheprovider data/faults/tests

test-render:
	$(PYTHON) -W error -m pytest -p no:cacheprovider data/render/tests

test-evals:
	$(PYTHON) -W error -m pytest -p no:cacheprovider evals/tests

eval-engine: validate-ground-truth test-evals
	cd apps/engine && ./mvnw -B -ntp package -DskipTests
	$(PYTHON) -m evals.runners.engine_eval --engine-jar apps/engine/target/engine-0.1.0.jar

render-documents: validate-ground-truth check-heldout-isolation
	$(PYTHON) -m data.render.render --accounts data/accounts --output data/documents --expected-count 300

validate-documents: render-documents
	$(PYTHON) -m data.render.validate --accounts data/accounts --documents data/documents --expected-count 300

check-heldout-isolation:
	$(PYTHON) -m data.render.check_heldout --ai-root apps/ai

eval-extraction-deterministic: validate-documents test-extraction
	$(PYTHON) -m evals.runners.deterministic_extraction_eval --accounts data/accounts --documents data/documents

eval-extraction: validate-documents test-extraction
	$(PYTHON) -m evals.runners.extraction_eval --accounts data/accounts --documents data/documents

test-web:
	npm --prefix apps/web run typecheck
	npm --prefix apps/web test
	npm --prefix apps/web run build
