# langgraph-codex

Put Codex inside the LangGraph you already own.

`langgraph-codex` is a small adapter library for one practical pattern: keep your deterministic graph, then replace one bounded node with a Codex-backed node when ordinary Python is not enough.

- LangGraph owns orchestration, state, routing, persistence, and checkpoints.
- Python owns parsing, context building, policy, and validation.
- Codex owns one explicit execution step with a clear prompt and workspace.
- Your application stays in control.

It is not a chat framework, hidden agent runtime, repository automation product, or broad model abstraction layer.

## Install

```bash
uv add langgraph-codex
```

For local development:

```bash
uv sync --extra dev
make check
```

## Start Here: Codex As One LangGraph Node

This is the main use case. Build a normal `langgraph.graph.StateGraph`, authorize Codex once, and use `create_codex_node` only for the node that needs agentic execution.

```python
import pathlib
import typing

import langgraph.graph

from langgraph_codex.execution import ExecutionResult
from langgraph_codex.graph import create_codex_node
from langgraph_codex.runtime import create_codex_executor, ensure_codex_authorized


class ReviewState(typing.TypedDict, total=False):
    workspace_path: typing.Required[pathlib.Path]
    repo_context: dict[str, list[str]]
    codex_result: ExecutionResult
    validation_message: str


def inspect_codebase(_state: ReviewState) -> dict[str, dict[str, list[str]]]:
    return {
        "repo_context": {
            "package_files": ["langgraph_codex/graph/nodes.py"],
            "test_files": ["tests/test_graphs.py", "tests/test_execution.py"],
            "example_files": ["examples/00_existing_langgraph_graph.py"],
        }
    }


def prompt_for_codex(state: ReviewState) -> str:
    return "\n".join(
        [
            "Audit the existing langgraph-codex repository.",
            f"Repository context: {state.get('repo_context', {})}",
            "Write codebase_audit.md with concrete findings about tests and examples.",
            "Do not invent an unrelated service configuration.",
        ]
    )


def validate_result(state: ReviewState) -> dict[str, str]:
    result = state.get("codex_result")
    if result is None:
        return {"validation_message": "Codex did not return a result."}
    if result.returncode != 0:
        return {"validation_message": f"Codex failed: {result.stderr}"}

    return {"validation_message": "Codex completed. Validate codebase_audit.md next."}


ensure_codex_authorized()
codex_node = create_codex_node(
    executor=create_codex_executor(timeout_seconds=300),
    prompt_builder=prompt_for_codex,
    workspace_path=lambda state: state["workspace_path"],
)


def draft_audit(state: ReviewState) -> dict[str, ExecutionResult]:
    update = codex_node(state)
    result = update.get("codex_result")
    if not isinstance(result, ExecutionResult):
        raise TypeError("Codex node did not return codex_result.")

    return {"codex_result": result}

graph = langgraph.graph.StateGraph(ReviewState)
graph.add_node("inspect_codebase", inspect_codebase)
graph.add_node("draft_audit", draft_audit)
graph.add_node("validate_result", validate_result)
graph.add_edge(langgraph.graph.START, "inspect_codebase")
graph.add_edge("inspect_codebase", "draft_audit")
graph.add_edge("draft_audit", "validate_result")
graph.add_edge("validate_result", langgraph.graph.END)

result = graph.compile().invoke({"workspace_path": pathlib.Path.cwd()})
print(result["validation_message"])
```

That is the intended shape:

```text
prepare deterministic context -> call Codex node -> validate deterministically -> route
```

## Authorization

Real Codex execution requires the Codex CLI and credentials. The runtime helpers load local `.env` values and map `OPEN_AI_SECRET_KEY` to `OPENAI_API_KEY` when needed.

```bash
cp .env.example .env
```

Then set the relevant values:

```text
OPEN_AI_SECRET_KEY=...
OPEN_AI_KEY_NAME=github-actions
OPEN_AI_MODEL=
```

See [docs/codex-authorization.md](docs/codex-authorization.md) for local setup, GitHub Actions secrets, and CI guidance.

## Validation

Codex output should be checked by deterministic code before anything downstream consumes it.

Good validators check files, schemas, command output, tests, checksums, and domain-specific facts:

```python
from langgraph_codex.utils.validation import require_files

validators = [require_files(["remediation_plan.md"])]
```

You can use the built-in validation helpers, or write normal LangGraph nodes that inspect your application state and route from there.

## Examples

The examples are intentionally few and close to the production integration shape:

- [examples/01_real_codex_node.py](examples/01_real_codex_node.py): real Codex inside a plain LangGraph graph, with deterministic preprocessing and validation.
- [examples/00_existing_langgraph_graph.py](examples/00_existing_langgraph_graph.py): offline version of the same idea using `FakeExecutor`.
- [examples/02_codebase_audit.py](examples/02_codebase_audit.py): real Codex codebase audit graph that gathers repository context and validates `codebase_audit.md`.

Run:

```bash
uv run python3 -m examples.00_existing_langgraph_graph
uv run python3 -m examples.01_real_codex_node
uv run python3 -m examples.02_codebase_audit
```

## Convenience Builders

For small tests and quick starts, the package also includes complete graph builders:

- `build_context_only_graph()`
- `build_execution_graph()`
- `build_retry_graph()`

Most production applications should prefer `create_codex_node` inside their own graph.

## CI/CD

The repository validates:

- GitHub Actions workflow syntax with actionlint;
- Ruff formatting and linting;
- Pylint with `10.00/10`;
- strict mypy and Pyright;
- Python compile checks;
- pytest across Python 3.11, 3.12, and 3.13;
- offline examples;
- wheel and source distribution build plus Twine metadata validation;
- optional real Codex smoke checks through workflow dispatch.

Release publishing uses PyPI trusted publishing through the `pypi` GitHub environment.

## Design Notes

The package deliberately stays small. It does not own memory, UI, checkpoint storage, broad model selection, or repository policy. Those concerns belong in the graph and infrastructure you already control.

Read more in [docs/design-philosophy.md](docs/design-philosophy.md).

## Testing Without Codex

Use `FakeExecutor` when you want CI-safe tests, examples, or local development without calling the Codex CLI.

```python
from langgraph_codex.execution import FakeExecutor

executor = FakeExecutor(stdout="Priority: medium. Area: billing exports.")
```

`FakeExecutor` records requests and returns deterministic results, so you can assert prompt content, metadata, options, and graph routing without network credentials.

## Development

```bash
make sync
make format
make check
```

Useful targets include `make quality`, `make test`, `make package-check`, `make examples`, `make examples-codex`, and `make clean`.

## License

MIT
