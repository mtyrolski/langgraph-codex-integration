import pathlib
import typing

import langgraph_codex.backends
import langgraph_codex.graph
import langgraph_codex.utils.validation


def backend_stdout_contains(text: str) -> langgraph_codex.utils.validation.Validator:
    def validate(
        state: typing.MutableMapping[str, typing.Any],
    ) -> langgraph_codex.utils.validation.ValidationResult:
        backend_result = state["backend_result"]
        if text in backend_result.stdout:
            return langgraph_codex.utils.validation.ValidationResult(
                passed=True,
                message=f"Backend output contains {text}.",
            )

        return langgraph_codex.utils.validation.ValidationResult(
            passed=False,
            message=f"Backend output does not contain {text}.",
        )

    return validate


def main() -> None:
    backend = langgraph_codex.backends.FakeBackend(stdout="status: accepted")
    graph = langgraph_codex.graph.build_basic_backend_graph(
        backend=backend,
        validators=[backend_stdout_contains("accepted")],
    )
    result = graph.invoke(
        {
            "workspace_path": pathlib.Path.cwd(),
            "task_title": "Validate backend output",
            "objective": "Run a custom deterministic validation policy.",
        }
    )
    print(result["review_result"]["message"])


if __name__ == "__main__":
    main()
