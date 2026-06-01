# langgraph_codex

`langgraph_codex` is a small infrastructure package for deterministic LangGraph workflows that can optionally delegate one node to Codex.

It is not an agent framework, chat model wrapper, repository automation toolkit, or testing workflow. The package keeps orchestration, state, validation, and routing explicit so applications can use Codex as one execution step without making the rest of the workflow depend on Codex.

```text
LangGraph = orchestration
Deterministic Python nodes = state transformations
Codex = optional executor
Validation = deterministic
Routing = deterministic
State = explicit and inspectable
```

## When To Use It

Use `langgraph_codex` when you want a directed workflow where most steps are deterministic, but one or more steps may need a powerful executor.

Good fits include document processing, data inspection, research workflows, content pipelines, operations runbooks, knowledge-base maintenance, configuration analysis, and software workflows. The package does not assume any of those domains.

## Install

With `uv`:

```bash
uv add langgraph-codex
```

For local development:

```bash
uv sync --extra dev
```

Run checks:

```bash
make check
```

The Makefile wraps the project’s `uv` workflows. Useful targets include `make sync`, `make format`, `make lint`, `make type`, `make test`, `make build`, `make examples`, `make examples-codex`, `make test-codex`, and `make clean`.

`make check` enforces formatting, Ruff, Pylint at `10.00/10`, strict mypy, pytest, wheel/sdist build, Twine package metadata validation, and the offline examples.

Real Codex validation is opt-in. Use `make examples-codex` for examples 02-10, `make test-codex` for real Codex integration tests, or `make check-codex` for both. The integration tests are skipped unless `LANGGRAPH_CODEX_RUN_REAL_CODEX=1` is set.

See [docs/codex-authorization.md](docs/codex-authorization.md) for local `.env`, `OPEN_AI_SECRET_KEY`, `OPEN_AI_KEY_NAME`, `OPEN_AI_MODEL`, CI secrets, and multi-agent safety guidance.

## Quickstart With FakeExecutor

The default development path does not require Codex.

```python
import pathlib

import langgraph_codex.execution
import langgraph_codex.graph


executor = langgraph_codex.execution.FakeExecutor(stdout="completed")
graph = langgraph_codex.graph.build_execution_graph(executor=executor)

result = graph.invoke(
    {
        "workspace_path": pathlib.Path.cwd(),
        "task_title": "Process structured inputs",
        "objective": "Run a graph with explicit state and a fake executor.",
        "context": {"Input": "Any domain-specific context can live here."},
    }
)

print(result["execution_result"].stdout)
print(result["review_result"]["message"])
```

## Context-Only Graph

Prompt rendering and state preparation work without an execution step.

```python
import pathlib

import langgraph_codex.graph


graph = langgraph_codex.graph.build_context_only_graph()
result = graph.invoke(
    {
        "workspace_path": pathlib.Path.cwd(),
        "task_title": "Render context",
        "objective": "Create stable Markdown from explicit workflow state.",
        "constraints": ["Omit empty sections."],
    }
)

print(result["rendered_prompt"])
```

## Real Codex Executor

Codex is opt-in. `CodexExecutor` shells out to `codex exec`, captures stdout, stderr, return code, and timeout state, and refuses dangerous bypass flags.

```python
import pathlib

import langgraph_codex.execution
import langgraph_codex.graph


executor = langgraph_codex.execution.CodexExecutor()
graph = langgraph_codex.graph.build_execution_graph(executor=executor)

result = graph.invoke(
    {
        "workspace_path": pathlib.Path.cwd(),
        "task_title": "Inspect workspace",
        "objective": "Summarize the workspace without changing files.",
    }
)

print(result["execution_result"].stdout)
```

## Explicit State

The default state is a `TypedDict` with generic workflow fields:

- `workspace_path`
- `task_title`
- `objective`
- `context`
- `constraints`
- `artifacts`
- `metadata`
- `rendered_prompt`
- `execution_result`
- `validation_result`
- `review_result`
- `retry_count`
- `max_retries`

Domain-specific fields belong in your application state or in `metadata` and `artifacts`.

## Prompt Rendering

`utils.prompts` renders stable Markdown from structured data. It supports title, objective, context sections, constraints, acceptance criteria, files, resources, artifacts, and additional instructions. Empty sections are omitted.

```python
import langgraph_codex.utils.prompts


prompt = langgraph_codex.utils.prompts.render_prompt(
    langgraph_codex.utils.prompts.PromptSpec(
        title="Inspect inputs",
        objective="Find inconsistencies in the supplied records.",
        constraints=["Do not mutate files."],
    )
)
```

## Validation

Validation is pluggable and deterministic. Built-in helpers cover generic checks such as required artifacts, file existence, JSON artifacts, and arbitrary command execution. Domain-specific workflows should provide their own validators.

```python
import pathlib

import langgraph_codex.execution
import langgraph_codex.graph
import langgraph_codex.utils.validation


executor = langgraph_codex.execution.FakeExecutor()
graph = langgraph_codex.graph.build_execution_graph(
    executor=executor,
    validators=[langgraph_codex.utils.validation.require_files(["README.md"])],
)

result = graph.invoke({"workspace_path": pathlib.Path.cwd()})
print(result["validation_result"].passed)
```

## Retry Routing

`build_retry_graph()` retries only through deterministic routing:

```text
START -> build_context -> render_prompt -> execute -> review -> router
router success -> END
router retry -> retry_node -> render_prompt -> execute
router fail -> END
```

The router uses only `validation_result`, `retry_count`, and `max_retries`.

## Architecture

- `execution.base`: `ExecutionRequest`, `ExecutionResult`, and `Executor`.
- `execution.fake`: testable fake executor for local development, CI, and examples.
- `execution.codex`: `codex exec` executor with safe command construction and timeout handling.
- `utils.prompts`: deterministic Markdown prompt rendering.
- `utils.validation`: composable deterministic validators.
- `utils.workspace`: workspace path normalization and validation.
- `graph.state`: explicit generic workflow state.
- `graph.nodes`: reusable deterministic nodes.
- `graph.builders`: context-only, execution, and retry graph builders.

## Examples

Run the offline examples first. They do not require Codex and are included in normal CI:

```bash
uv run python examples/00_context_only_graph.py
uv run python examples/01_fake_executor_graph.py
```

Examples 02-10 use `CodexExecutor` and are excluded from offline CI. Run them only when the Codex CLI is installed and authenticated:

```bash
uv run python examples/02_codex_executor_graph.py
uv run python examples/03_retry_graph.py
uv run python examples/04_custom_validation.py
uv run python examples/05_quickstart.py
uv run python examples/06_customer_feedback_triage.py
uv run python examples/07_dataset_quality_profile.py
uv run python examples/08_policy_review_retry.py
uv run python examples/09_research_digest.py
uv run python examples/10_service_config_review.py
```

Or use the Makefile targets:

```bash
make examples
make examples-codex
make test-codex
```

## CI/CD

The repository includes GitHub Actions workflows for:

- Pull request and main-branch CI across Python 3.10, 3.11, 3.12, and 3.13.
- Formatting, Ruff, Pylint `10.00/10`, strict typing, tests, package build, Twine package checks, and offline example execution.
- Optional workflow-dispatch real Codex checks when `run-real-codex` is enabled and `OPEN_AI_SECRET_KEY` is configured as a GitHub Actions secret.
- Release publishing through `uv publish` with PyPI trusted publishing.
- Weekly Dependabot updates for GitHub Actions and `uv` dependencies.

Configure the `pypi` GitHub environment and PyPI trusted publisher before using the release workflow.

## Non-Goals

`langgraph_codex` does not provide hidden memory, chat history, git automation, test orchestration, checkpoint persistence, streaming, or a model abstraction. Those can be added by applications as explicit state, validators, graph nodes, or custom executors.

## Future Extensions

Useful additions could include an MCP executor, app-server executor, streaming result adapter, checkpoint examples, richer structured output handling, and a small gallery of domain-neutral workflow recipes.
