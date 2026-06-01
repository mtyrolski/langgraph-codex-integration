SHELL := /usr/bin/env bash
.SHELLFLAGS := -eu -o pipefail -c

UV ?= uv
RUN_REAL_CODEX_ENV := LANGGRAPH_CODEX_RUN_REAL_CODEX=1

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

.PHONY: pylint
pylint: ## Run pylint and require a 10/10 score.
	$(UV) run pylint langgraph_codex examples tests --fail-under=10

.PHONY: lint-fix
lint-fix: ## Run ruff and apply safe lint fixes.
	$(UV) run ruff check . --fix

.PHONY: type
type: ## Run mypy in strict mode.
	$(UV) run mypy

.PHONY: test
test: ## Run the pytest suite.
	$(UV) run pytest

.PHONY: test-codex
test-codex: ## Run opt-in integration tests against real Codex.
	$(RUN_REAL_CODEX_ENV) $(UV) run pytest tests/integration

.PHONY: examples
examples: examples-offline ## Run offline examples that do not require Codex.

.PHONY: examples-offline
examples-offline: ## Run examples that do not require Codex.
	$(UV) run python examples/00_context_only_graph.py
	$(UV) run python examples/01_fake_executor_graph.py

.PHONY: examples-codex
examples-codex: ## Run opt-in examples against real Codex.
	$(UV) run python examples/02_codex_executor_graph.py
	$(UV) run python examples/03_retry_graph.py
	$(UV) run python examples/04_custom_validation.py
	$(UV) run python examples/05_quickstart.py
	$(UV) run python examples/06_customer_feedback_triage.py
	$(UV) run python examples/07_dataset_quality_profile.py
	$(UV) run python examples/08_policy_review_retry.py
	$(UV) run python examples/09_research_digest.py
	$(UV) run python examples/10_service_config_review.py

.PHONY: build
build: ## Build wheel and source distribution.
	$(UV) build

.PHONY: package-check
package-check: build ## Validate built distribution metadata.
	$(UV) run twine check dist/*

.PHONY: check
check: format-check lint pylint type test package-check examples ## Run the full local validation suite.

.PHONY: check-codex
check-codex: examples-codex test-codex ## Run opt-in real Codex examples and integration tests.

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
