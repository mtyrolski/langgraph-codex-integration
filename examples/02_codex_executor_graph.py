import pathlib

import langgraph_codex.codex_runtime as codex_runtime

import langgraph_codex.execution
import langgraph_codex.graph


def print_section(title: str, value: object) -> None:
    print(f"\n{'=' * 80}")
    print(title)
    print(f"{'=' * 80}")
    print(value)


def main() -> None:
    codex_runtime.ensure_codex_authorized()
    codex_runtime.print_authorization_status()
    executor = codex_runtime.create_codex_executor()
    graph = langgraph_codex.graph.build_execution_graph(executor=executor)
    result = graph.invoke(
        {
            "workspace_path": pathlib.Path.cwd(),
            "task_title": "Inspect workspace",
            "objective": (
                "Describe the visible workspace contents without changing files. "
                "Focus on what this package appears to provide and mention that this is "
                "a real CodexExecutor execution."
            ),
            "constraints": [
                "Do not modify files.",
                "Keep the answer grounded in visible files.",
                "End with the exact marker CODEX_WORKSPACE_INSPECTION_COMPLETE.",
            ],
        }
    )
    execution_result = result["execution_result"]
    print_section("Rendered prompt", result["rendered_prompt"])
    print_section("Execution return code", execution_result.returncode)
    print_section("Execution stdout", execution_result.stdout)
    print_section("Execution stderr", execution_result.stderr or "<empty>")
    print_section("Review result", result["review_result"])


if __name__ == "__main__":
    main()
