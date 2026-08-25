PYTHON ?= python3

.PHONY: up down verify lint-ai test-engine test-ai test-web

up:
	docker compose up --build -d

down:
	docker compose down

verify: lint-ai test-engine test-ai test-web
	@echo "VERIFY OK"

lint-ai:
	$(PYTHON) -m ruff check apps/ai

test-engine:
	cd apps/engine && ./mvnw -B -ntp test

test-ai:
	$(PYTHON) -W error -m pytest apps/ai

test-web:
	npm --prefix apps/web run typecheck
	npm --prefix apps/web test
	npm --prefix apps/web run build
