import pathlib

import langgraph_codex.runtime as runtime

import langgraph_codex.execution
import langgraph_codex.graph


def print_section(title: str, value: object) -> None:
    print(f"\n{'=' * 80}")
    print(title)
    print(f"{'=' * 80}")
    print(value)


def main() -> None:
    runtime.ensure_codex_authorized()
    runtime.print_authorization_status()
    executor = runtime.create_codex_executor()
    graph = langgraph_codex.graph.build_execution_graph(executor=executor)
    result = graph.invoke(
        {
            "workspace_path": pathlib.Path.cwd(),
            "task_title": "Quickstart with real CodexExecutor",
            "objective": (
                "Explain what happened in this graph run: deterministic context rendering, "
                "real CodexExecutor execution, and deterministic review."
            ),
            "context": {
                "Input": "All state is explicit.",
                "Executor": "This example uses CodexExecutor, not FakeExecutor.",
            },
            "constraints": ["Do not modify files.", "Keep the answer friendly but technical."],
            "acceptance_criteria": [
                "The graph returns a rendered prompt.",
                "The graph returns an execution result.",
                "The graph returns a deterministic review result.",
            ],
        }
    )
    execution_result = result["execution_result"]
    print_section("Rendered prompt", result["rendered_prompt"])
    print_section("Review result", result["review_result"])
    print_section("Execution return code", execution_result.returncode)
    print_section("Execution stdout", execution_result.stdout)
    print_section("Execution stderr", execution_result.stderr or "<empty>")


if __name__ == "__main__":
    main()
