import pathlib
import typing

import langgraph_codex.runtime as runtime

import langgraph_codex.execution
import langgraph_codex.graph
import langgraph_codex.utils.validation

SUCCESS_MARKER = "CODEX_RETRY_GRAPH_COMPLETE"


def stdout_contains_marker(
    marker: str,
) -> langgraph_codex.utils.validation.Validator:
    def validate(
        state: typing.MutableMapping[str, typing.Any],
    ) -> langgraph_codex.utils.validation.ValidationResult:
        execution_result = state["execution_result"]
        if marker in execution_result.stdout:
            return langgraph_codex.utils.validation.ValidationResult(
                passed=True,
                message=f"Execution stdout contains required marker {marker}.",
            )

        return langgraph_codex.utils.validation.ValidationResult(
            passed=False,
            message=f"Execution stdout is missing required marker {marker}.",
            details={"stdout": execution_result.stdout},
        )

    return validate


def print_section(title: str, value: object) -> None:
    print(f"\n{'=' * 80}")
    print(title)
    print(f"{'=' * 80}")
    print(value)


def main() -> None:
    runtime.ensure_codex_authorized()
    runtime.print_authorization_status()
    executor = runtime.create_codex_executor()
    graph = langgraph_codex.graph.build_retry_graph(
        executor=executor,
        validators=[stdout_contains_marker(SUCCESS_MARKER)],
    )
    result = graph.invoke(
        {
            "workspace_path": pathlib.Path.cwd(),
            "task_title": "Retry router demonstration with real Codex",
            "objective": (
                "Answer in two short paragraphs explaining how deterministic retry routing "
                "works in this package. End with the exact marker "
                f"{SUCCESS_MARKER} so the deterministic validator can pass."
            ),
            "constraints": [
                "Do not modify files.",
                "Do not claim a retry happened unless retry_count is greater than zero.",
            ],
            "max_retries": 1,
        }
    )
    execution_result = result["execution_result"]
    print_section("Rendered prompt", result["rendered_prompt"])
    print_section("Retry count", result["retry_count"])
    print_section("Validation result", result["validation_result"])
    print_section("Review result", result["review_result"])
    print_section("Execution return code", execution_result.returncode)
    print_section("Execution stdout", execution_result.stdout)
    print_section("Execution stderr", execution_result.stderr or "<empty>")


if __name__ == "__main__":
    main()
