import pathlib

import langgraph_codex.backends
import langgraph_codex.graph


def test_context_only_graph_renders_prompt(tmp_path: pathlib.Path) -> None:
    graph = langgraph_codex.graph.build_context_only_graph()

    result = graph.invoke(
        {
            "workspace_path": tmp_path,
            "task_title": "Context only",
            "objective": "Render prompt.",
        }
    )

    assert result["workspace_path"] == tmp_path.resolve()
    assert result["rendered_prompt"].startswith("# Context only")
    assert "## Objective" in result["rendered_prompt"]


def test_basic_backend_graph_runs_fake_backend(tmp_path: pathlib.Path) -> None:
    backend = langgraph_codex.backends.FakeBackend(stdout="completed")
    graph = langgraph_codex.graph.build_basic_backend_graph(backend=backend)

    result = graph.invoke(
        {
            "workspace_path": tmp_path,
            "task_title": "Basic graph",
            "objective": "Run backend.",
        }
    )

    assert result["backend_result"].stdout == "completed"
    assert result["validation_result"].passed is True
    assert len(backend.requests) == 1
    assert backend.requests[0].prompt.startswith("# Basic graph")


def test_retry_graph_retries_backend_failure(tmp_path: pathlib.Path) -> None:
    backend = langgraph_codex.backends.FakeBackend(returncode=1, stderr="failed")
    graph = langgraph_codex.graph.build_retry_graph(backend=backend)

    result = graph.invoke(
        {
            "workspace_path": tmp_path,
            "task_title": "Retry graph",
            "objective": "Retry failed backend.",
            "max_retries": 2,
        }
    )

    assert len(backend.requests) == 3
    assert result["retry_count"] == 2
    assert result["validation_result"].passed is False


def test_retry_graph_stops_after_success(tmp_path: pathlib.Path) -> None:
    attempts = {"count": 0}

    def responder(
        request: langgraph_codex.backends.BackendRequest,
    ) -> langgraph_codex.backends.BackendResult:
        attempts["count"] += 1
        if attempts["count"] == 1:
            return langgraph_codex.backends.BackendResult(
                stdout="",
                stderr="try again",
                returncode=1,
            )

        return langgraph_codex.backends.BackendResult(stdout="ok", stderr="", returncode=0)

    backend = langgraph_codex.backends.FakeBackend(responder=responder)
    graph = langgraph_codex.graph.build_retry_graph(backend=backend)

    result = graph.invoke(
        {
            "workspace_path": tmp_path,
            "task_title": "Recover",
            "objective": "Succeed after retry.",
            "max_retries": 2,
        }
    )

    assert len(backend.requests) == 2
    assert result["retry_count"] == 1
    assert result["validation_result"].passed is True
