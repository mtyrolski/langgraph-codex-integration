import pathlib
import typing

import _codex_runtime

import langgraph_codex.execution
import langgraph_codex.graph
import langgraph_codex.utils.validation

SUCCESS_MARKER = "CODEX_CUSTOM_VALIDATION_ACCEPTED"


def executor_stdout_contains(marker: str) -> langgraph_codex.utils.validation.Validator:
    def validate(
        state: typing.MutableMapping[str, typing.Any],
    ) -> langgraph_codex.utils.validation.ValidationResult:
        execution_result = state["execution_result"]
        if marker in execution_result.stdout:
            return langgraph_codex.utils.validation.ValidationResult(
                passed=True,
                message=f"Execution output contains required marker {marker}.",
            )

        return langgraph_codex.utils.validation.ValidationResult(
            passed=False,
            message=f"Execution output does not contain required marker {marker}.",
            details={"stdout": execution_result.stdout},
        )

    return validate


def print_section(title: str, value: object) -> None:
    print(f"\n{'=' * 80}")
    print(title)
    print(f"{'=' * 80}")
    print(value)


def main() -> None:
    _codex_runtime.ensure_codex_authorized()
    _codex_runtime.print_authorization_status()
    executor = _codex_runtime.create_codex_executor()
    graph = langgraph_codex.graph.build_execution_graph(
        executor=executor,
        validators=[executor_stdout_contains(SUCCESS_MARKER)],
    )
    result = graph.invoke(
        {
            "workspace_path": pathlib.Path.cwd(),
            "task_title": "Validate real Codex output",
            "objective": (
                "Produce a concise operational status note for this workflow. "
                f"End with the exact marker {SUCCESS_MARKER} so a deterministic "
                "custom validator can verify the execution output."
            ),
            "constraints": ["Do not modify files.", "Keep the status note under 120 words."],
        }
    )
    execution_result = result["execution_result"]
    print_section("Rendered prompt", result["rendered_prompt"])
    print_section("Validation result", result["validation_result"])
    print_section("Review result", result["review_result"])
    print_section("Execution return code", execution_result.returncode)
    print_section("Execution stdout", execution_result.stdout)
    print_section("Execution stderr", execution_result.stderr or "<empty>")


if __name__ == "__main__":
    main()
