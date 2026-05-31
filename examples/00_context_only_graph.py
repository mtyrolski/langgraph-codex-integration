import pathlib

import langgraph_codex.graph


def main() -> None:
    graph = langgraph_codex.graph.build_context_only_graph()
    result = graph.invoke(
        {
            "workspace_path": pathlib.Path.cwd(),
            "task_title": "Prepare a deterministic handoff",
            "objective": "Render a prompt from explicit workflow state.",
            "context": {"Current State": "The workflow has structured context only."},
            "constraints": ["Do not call an execution backend."],
        }
    )
    print(result["rendered_prompt"])


if __name__ == "__main__":
    main()
