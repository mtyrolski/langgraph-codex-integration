import pathlib

import langgraph_codex.execution
import langgraph_codex.graph


def main() -> None:
    executor = langgraph_codex.execution.FakeExecutor(stdout="Fake work completed.")
    graph = langgraph_codex.graph.build_execution_graph(executor=executor)
    result = graph.invoke(
        {
            "workspace_path": pathlib.Path.cwd(),
            "task_title": "Summarize inputs",
            "objective": "Demonstrate executor-driven work without requiring Codex.",
        }
    )
    print(result["execution_result"].stdout)
    print(result["review_result"]["message"])


if __name__ == "__main__":
    main()
