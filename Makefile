# Developer shortcuts for Ieogagi. Run `make help` to list the targets.
SHELL := /bin/bash
.DEFAULT_GOAL := help

BACKEND_VENV := backend/.venv
VENV_BIN := $(BACKEND_VENV)/bin

.PHONY: help setup test lint security security-quick semgrep-test secrets-scan dev-backend dev-frontend lock

help: ## Show this list
	@awk -F':.*## ' '/^[a-zA-Z_-]+:.*## /{printf "  %-16s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

setup: ## Create backend venv (hash-pinned install) and install frontend packages
	uv venv --python 3.12 --allow-existing $(BACKEND_VENV)
	uv pip install --python $(VENV_BIN)/python --require-hashes -r backend/requirements-dev.lock
	uv pip install --python $(VENV_BIN)/python --no-deps -e backend
	npm --prefix frontend ci

test: ## Run backend tests (needs IEOGAGI_TEST_DATABASE_URL, see backend/tests)
	cd backend && .venv/bin/pytest

lint: ## ruff (backend) + eslint (frontend)
	$(VENV_BIN)/ruff check backend
	npm --prefix frontend run lint

security: ## Full security scan, reports in security/reports/<date>/
	scripts/security_scan.sh

security-quick: ## Offline scan (ruff, bandit, custom semgrep), for pre-push
	scripts/security_scan.sh --quick

semgrep-test: ## Self-test the custom Semgrep rules
	$(VENV_BIN)/semgrep --metrics=off --disable-version-check --test --config security/semgrep security/semgrep/tests

secrets-scan: ## Scan git history and working tree for leaked secrets (gitleaks)
	gitleaks git --no-banner --redact .
	gitleaks dir --no-banner --redact .

dev-backend: ## Run the API on :8000 with auto-reload (development only)
	cd backend && .venv/bin/uvicorn app.main:create_app --factory --reload --port 8000 --no-server-header --no-access-log --no-proxy-headers

dev-frontend: ## Run the Vite dev server
	npm --prefix frontend run dev

lock: ## Regenerate both hash-pinned lock files from pyproject.toml
	cd backend && uv pip compile pyproject.toml --generate-hashes --python-version 3.12 -o requirements.lock
	cd backend && uv pip compile pyproject.toml --extra dev --generate-hashes --python-version 3.12 -o requirements-dev.lock
	cd backend && printf "setuptools>=70\n" | uv pip compile - --generate-hashes --python-version 3.12 --no-header -o requirements-build.lock
