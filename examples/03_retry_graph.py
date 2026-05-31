import pathlib

import langgraph_codex.backends
import langgraph_codex.graph


def main() -> None:
    backend = langgraph_codex.backends.FakeBackend(returncode=1, stderr="Simulated failure.")
    graph = langgraph_codex.graph.build_retry_graph(backend=backend)
    result = graph.invoke(
        {
            "workspace_path": pathlib.Path.cwd(),
            "task_title": "Retry demonstration",
            "objective": "Show deterministic retry routing after backend failure.",
            "max_retries": 2,
        }
    )
    print(f"Attempts: {len(backend.requests)}")
    print(f"Retry count: {result['retry_count']}")
    print(result["review_result"]["message"])


if __name__ == "__main__":
    main()
