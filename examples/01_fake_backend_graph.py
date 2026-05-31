import pathlib

import langgraph_codex.backends
import langgraph_codex.graph


def main() -> None:
    backend = langgraph_codex.backends.FakeBackend(stdout="Fake work completed.")
    graph = langgraph_codex.graph.build_basic_backend_graph(backend=backend)
    result = graph.invoke(
        {
            "workspace_path": pathlib.Path.cwd(),
            "task_title": "Summarize inputs",
            "objective": "Demonstrate backend execution without requiring Codex.",
        }
    )
    print(result["backend_result"].stdout)
    print(result["review_result"]["message"])


if __name__ == "__main__":
    main()
