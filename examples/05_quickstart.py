import pathlib

import langgraph_codex.backends
import langgraph_codex.graph


def main() -> None:
    backend = langgraph_codex.backends.FakeBackend(stdout="Quickstart complete.")
    graph = langgraph_codex.graph.build_basic_backend_graph(backend=backend)
    result = graph.invoke(
        {
            "workspace_path": pathlib.Path.cwd(),
            "task_title": "Quickstart",
            "objective": "Run a deterministic LangGraph workflow with a fake backend.",
            "context": {"Input": "All state is explicit."},
            "acceptance_criteria": ["The graph returns a backend result and review result."],
        }
    )
    print(result["rendered_prompt"])
    print(result["backend_result"].stdout)


if __name__ == "__main__":
    main()
