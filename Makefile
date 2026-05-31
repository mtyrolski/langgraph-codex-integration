SHELL := /usr/bin/env bash
.SHELLFLAGS := -eu -o pipefail -c

UV ?= uv

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show available make targets.
	@awk 'BEGIN {FS = ":.*##"; printf "Available targets:\n"} /^[a-zA-Z0-9_.-]+:.*##/ {printf "  %-18s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.PHONY: sync
sync: ## Install the project and development dependencies with uv.
	$(UV) sync --extra dev

.PHONY: lock
lock: ## Refresh uv.lock without installing packages.
	$(UV) lock

.PHONY: format
format: ## Format source, examples, and tests.
	$(UV) run ruff format .

.PHONY: format-check
format-check: ## Check formatting without modifying files.
	$(UV) run ruff format --check .

.PHONY: lint
lint: ## Run ruff lint checks.
	$(UV) run ruff check .

.PHONY: lint-fix
lint-fix: ## Run ruff and apply safe lint fixes.
	$(UV) run ruff check . --fix

.PHONY: type
type: ## Run mypy in strict mode.
	$(UV) run mypy

.PHONY: test
test: ## Run the pytest suite.
	$(UV) run pytest

.PHONY: examples
examples: ## Run examples that do not require Codex.
	$(UV) run python examples/00_context_only_graph.py
	$(UV) run python examples/01_fake_backend_graph.py
	$(UV) run python examples/04_custom_validation.py
	$(UV) run python examples/03_retry_graph.py
	$(UV) run python examples/05_quickstart.py

.PHONY: build
build: ## Build wheel and source distribution.
	$(UV) build

.PHONY: check
check: format-check lint type test build examples ## Run the full local validation suite.

.PHONY: ci
ci: check ## Alias for the full CI validation suite.

.PHONY: clean
clean: ## Remove generated local artifacts and caches.
	rm -rf build dist *.egg-info
	rm -rf .mypy_cache .pytest_cache .ruff_cache htmlcov .coverage
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type f -name '*.py[co]' -delete

.PHONY: publish
publish: build ## Publish built distributions with uv. Requires PyPI credentials or trusted publishing.
	$(UV) publish
