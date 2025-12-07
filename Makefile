SHELL := /bin/bash
COMPOSE ?= docker compose
COMPOSE_FILE ?= docker-compose.yml
PYTHON ?= python3

.PHONY: help setup deps precommit migrate seed up up-build down lint format test

help: ## Display available targets
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*## "}; {printf "  %-12s %s\n", $$1, $$2}'

setup: deps precommit migrate seed ## Bootstrap the local environment

deps: ## Install Python dependencies into the active environment
	$(PYTHON) -m pip install -r requirements.txt

precommit: ## Install git hooks for lint/format enforcement
	@if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then \
		pre-commit install; \
	else \
		echo "Skipping pre-commit install (not inside a git repository)."; \
	fi

migrate: ## Apply the latest Alembic migrations
	bash ./infra/scripts/run_migrations.sh

seed: ## Seed the database with baseline TODO data
	$(PYTHON) scripts/seed_data.py

up: ## Start the Docker Compose stack (API + PostgreSQL)
	$(COMPOSE) -f $(COMPOSE_FILE) up -d

up-build: ## Rebuild images and start the Docker Compose stack
	$(COMPOSE) -f $(COMPOSE_FILE) up --build -d

down: ## Stop the Docker Compose stack
	$(COMPOSE) -f $(COMPOSE_FILE) down

lint: ## Run Ruff checks
	./scripts/lint.sh

format: ## Run isort followed by Black
	./scripts/format.sh

test: ## Execute pytest suite
	./scripts/test.sh
