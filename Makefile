PYTHON ?= python3

.PHONY: up down verify lint-ai test-engine test-ai test-data test-faults test-web generate-accounts validate-accounts inject-faults validate-ground-truth

up:
	docker compose up --build -d

down:
	docker compose down

verify: lint-ai test-engine test-ai test-data test-faults test-web
	@echo "VERIFY OK"

lint-ai:
	$(PYTHON) -m ruff check apps/ai data/generator data/faults

test-engine:
	cd apps/engine && ./mvnw -B -ntp test

test-ai:
	$(PYTHON) -W error -m pytest -p no:cacheprovider apps/ai

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

test-web:
	npm --prefix apps/web run typecheck
	npm --prefix apps/web test
	npm --prefix apps/web run build
