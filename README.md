# langgraph-codex

Use your own LangGraph. Replace one bounded node with Codex when deterministic Python is not enough.

`langgraph-codex` keeps orchestration explicit:

- LangGraph owns graph structure, state, routing, persistence, and checkpoints.
- Python owns deterministic context building and validation.
- Codex is one executor node with a clear prompt and workspace.
- Your application owns domain policy, memory, UI, and deployment.

The package is intentionally small. It is not a chat framework, hidden agent runtime, repository automation product, or model abstraction layer.

## Install

```bash
uv add langgraph-codex
```

For local development:

```bash
uv sync --extra dev
make check
```

## Quickstart: Replace One LangGraph Node

This is the primary integration path. Build a normal `langgraph.graph.StateGraph`, then use `create_codex_node` for the step that needs Codex-style execution.

```python
import pathlib
import typing

import langgraph.graph

from langgraph_codex.execution import FakeExecutor
from langgraph_codex.graph import create_codex_node


class SupportState(typing.TypedDict, total=False):
    workspace_path: pathlib.Path
    ticket: str
    codex_result: object
    reply: str


def load_ticket(_state: SupportState) -> dict[str, str]:
    return {"ticket": "Billing export is missing purchase order references."}


def finalize(state: SupportState) -> dict[str, str]:
    return {"reply": state["codex_result"].stdout}


graph = langgraph.graph.StateGraph(SupportState)
graph.add_node("load_ticket", load_ticket)
graph.add_node(
    "draft_reply",
    create_codex_node(
        executor=FakeExecutor(stdout="Priority: medium. Area: billing exports."),
        prompt_builder=lambda state: f"Draft a support response for: {state['ticket']}",
        workspace_path=lambda state: state["workspace_path"],
    ),
)
graph.add_node("finalize", finalize)
graph.add_edge(langgraph.graph.START, "load_ticket")
graph.add_edge("load_ticket", "draft_reply")
graph.add_edge("draft_reply", "finalize")
graph.add_edge("finalize", langgraph.graph.END)

result = graph.compile().invoke({"workspace_path": pathlib.Path.cwd()})
print(result["reply"])
```

Swap `FakeExecutor` for `CodexExecutor` when you want a real `codex exec` run.

## Real Codex

`CodexExecutor` shells out to the Codex CLI, passes the prompt on stdin, captures stdout, stderr, return code, timeout state, and refuses known dangerous bypass flags.

```python
from langgraph_codex.execution import CodexExecutor

executor = CodexExecutor(timeout_seconds=300)
```

Real Codex examples and integration tests are opt-in because they require the Codex CLI and credentials.

```bash
make examples-codex
make test-codex
```

See [docs/codex-authorization.md](docs/codex-authorization.md) for `.env`, `OPEN_AI_SECRET_KEY`, `OPEN_AI_KEY_NAME`, `OPEN_AI_MODEL`, GitHub Actions secrets, and CI guidance.

## Convenience Builders

If you want a complete starter graph, the package still includes builders:

- `build_context_only_graph()`
- `build_execution_graph()`
- `build_retry_graph()`

They are useful for tests, quick starts, and simple workflows. Production applications will usually prefer `create_codex_node` inside their own graph.

## Validation

Validation is deterministic and application-owned. Built-in helpers cover common checks:

```python
from langgraph_codex.utils.validation import require_files

validators = [require_files(["remediation_plan.md"])]
```

Recommended shape:

```text
prepare context -> call Codex node -> validate deterministically -> route
```

Use file checks, JSON checks, command checks, checksums, tests, and domain assertions before downstream systems consume Codex output.

## Examples

The examples are intentionally few:

- [examples/00_existing_langgraph_graph.py](examples/00_existing_langgraph_graph.py): offline, CI-safe, plain LangGraph graph with one Codex-backed node using `FakeExecutor`.
- [examples/01_real_codex_node.py](examples/01_real_codex_node.py): real Codex graph with deterministic preprocessing and validation.

Run:

```bash
make examples
make examples-codex
```

## CI/CD

The repository validates:

- GitHub Actions workflow syntax with actionlint;
- Ruff formatting and linting;
- Pylint with `10.00/10`;
- strict mypy;
- Python compile checks;
- pytest across Python 3.10, 3.11, 3.12, and 3.13;
- offline examples;
- wheel and source distribution build plus Twine metadata validation;
- optional real Codex smoke checks through workflow dispatch.

Release publishing uses PyPI trusted publishing through the `pypi` GitHub environment.

## Documentation

- [Design Philosophy](docs/design-philosophy.md)
- [Codex Authorization](docs/codex-authorization.md)

## Development

```bash
make sync
make format
make check
```

Useful targets include `make quality`, `make test`, `make package-check`, `make examples`, `make examples-codex`, and `make clean`.

## License

MIT
