# langgraph_codex

`langgraph_codex` is a small infrastructure package for deterministic LangGraph workflows that can optionally delegate one node to Codex.

It is not an agent framework, chat model wrapper, repository automation toolkit, or testing workflow. The package keeps orchestration, state, validation, and routing explicit so applications can use Codex as one execution backend without making the rest of the workflow depend on Codex.

```text
LangGraph = orchestration
Deterministic Python nodes = state transformations
Codex = optional execution backend
Validation = deterministic
Routing = deterministic
State = explicit and inspectable
```

## When To Use It

Use `langgraph_codex` when you want a directed workflow where most steps are deterministic, but one or more steps may need a powerful execution backend.

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

The Makefile wraps the project’s `uv` workflows. Useful targets include `make sync`, `make format`, `make lint`, `make type`, `make test`, `make build`, `make examples`, and `make clean`.

## Quickstart With FakeBackend

The default development path does not require Codex.

```python
import pathlib

import langgraph_codex.backends
import langgraph_codex.graph


backend = langgraph_codex.backends.FakeBackend(stdout="completed")
graph = langgraph_codex.graph.build_basic_backend_graph(backend=backend)

result = graph.invoke(
    {
        "workspace_path": pathlib.Path.cwd(),
        "task_title": "Process structured inputs",
        "objective": "Run a graph with explicit state and a fake execution backend.",
        "context": {"Input": "Any domain-specific context can live here."},
    }
)

print(result["backend_result"].stdout)
print(result["review_result"]["message"])
```

## Context-Only Graph

Prompt rendering and state preparation work without any execution backend.

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

## Real Codex Backend

Codex is opt-in. The backend shells out to `codex exec`, captures stdout, stderr, return code, and timeout state, and refuses dangerous bypass flags.

```python
import pathlib

import langgraph_codex.backends
import langgraph_codex.graph


backend = langgraph_codex.backends.CodexBackend()
graph = langgraph_codex.graph.build_basic_backend_graph(backend=backend)

result = graph.invoke(
    {
        "workspace_path": pathlib.Path.cwd(),
        "task_title": "Inspect workspace",
        "objective": "Summarize the workspace without changing files.",
    }
)

print(result["backend_result"].stdout)
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
- `backend_result`
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

import langgraph_codex.backends
import langgraph_codex.graph
import langgraph_codex.utils.validation


backend = langgraph_codex.backends.FakeBackend()
graph = langgraph_codex.graph.build_basic_backend_graph(
    backend=backend,
    validators=[langgraph_codex.utils.validation.require_files(["README.md"])],
)

result = graph.invoke({"workspace_path": pathlib.Path.cwd()})
print(result["validation_result"].passed)
```

## Retry Routing

`build_retry_graph()` retries only through deterministic routing:

```text
START -> build_context -> render_prompt -> backend -> review -> router
router success -> END
router retry -> retry_node -> render_prompt -> backend
router fail -> END
```

The router uses only `validation_result`, `retry_count`, and `max_retries`.

## Architecture

- `backends.base`: `BackendRequest`, `BackendResult`, and `ExecutionBackend`.
- `backends.fake`: testable backend for local development, CI, and examples.
- `backends.exec`: `codex exec` backend with safe command construction and timeout handling.
- `utils.prompts`: deterministic Markdown prompt rendering.
- `utils.validation`: composable deterministic validators.
- `utils.workspace`: workspace path normalization and validation.
- `graph.state`: explicit generic workflow state.
- `graph.nodes`: reusable deterministic nodes.
- `graph.builders`: context-only, basic backend, and retry graph builders.

## Examples

Run the no-Codex examples first:

```bash
uv run python examples/00_context_only_graph.py
uv run python examples/01_fake_backend_graph.py
uv run python examples/04_custom_validation.py
uv run python examples/03_retry_graph.py
uv run python examples/05_quickstart.py
```

Real Codex usage is opt-in:

```bash
uv run python examples/02_codex_backend_graph.py
```

## CI/CD

The repository includes GitHub Actions workflows for:

- Pull request and main-branch CI across Python 3.10, 3.11, 3.12, and 3.13.
- Formatting, linting, strict typing, tests, package build, and no-Codex example execution.
- Release publishing through `uv publish` with PyPI trusted publishing.
- Weekly Dependabot updates for GitHub Actions and `uv` dependencies.

Configure the `pypi` GitHub environment and PyPI trusted publisher before using the release workflow.

## Non-Goals

`langgraph_codex` does not provide hidden memory, chat history, git automation, test orchestration, checkpoint persistence, streaming, or a model abstraction. Those can be added by applications as explicit state, validators, graph nodes, or custom backends.

## Future Extensions

Useful additions could include an MCP backend, app-server backend, streaming result adapter, checkpoint examples, richer structured output handling, and a small gallery of domain-neutral workflow recipes.
