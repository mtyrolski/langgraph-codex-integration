import pathlib

import langgraph_codex.backends
import langgraph_codex.graph


def main() -> None:
    backend = langgraph_codex.backends.CodexBackend()
    graph = langgraph_codex.graph.build_basic_backend_graph(backend=backend)
    result = graph.invoke(
        {
            "workspace_path": pathlib.Path.cwd(),
            "task_title": "Inspect workspace",
            "objective": "Describe the visible workspace contents without changing files.",
            "constraints": ["Keep the response concise."],
        }
    )
    print(result["backend_result"].stdout)


if __name__ == "__main__":
    main()
