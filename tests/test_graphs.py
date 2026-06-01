import pathlib

import langgraph_codex.execution
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


def test_execution_graph_runs_fake_executor(tmp_path: pathlib.Path) -> None:
    executor = langgraph_codex.execution.FakeExecutor(stdout="completed")
    graph = langgraph_codex.graph.build_execution_graph(executor=executor)

    result = graph.invoke(
        {
            "workspace_path": tmp_path,
            "task_title": "Basic graph",
            "objective": "Run executor.",
        }
    )

    assert result["execution_result"].stdout == "completed"
    assert result["validation_result"].passed is True
    assert len(executor.requests) == 1
    assert executor.requests[0].prompt.startswith("# Basic graph")


def test_retry_graph_retries_executor_failure(tmp_path: pathlib.Path) -> None:
    executor = langgraph_codex.execution.FakeExecutor(returncode=1, stderr="failed")
    graph = langgraph_codex.graph.build_retry_graph(executor=executor)

    result = graph.invoke(
        {
            "workspace_path": tmp_path,
            "task_title": "Retry graph",
            "objective": "Retry failed executor.",
            "max_retries": 2,
        }
    )

    assert len(executor.requests) == 3
    assert result["retry_count"] == 2
    assert result["validation_result"].passed is False


def test_retry_graph_stops_after_success(tmp_path: pathlib.Path) -> None:
    attempts = {"count": 0}

    def responder(
        _request: langgraph_codex.execution.ExecutionRequest,
    ) -> langgraph_codex.execution.ExecutionResult:
        attempts["count"] += 1
        if attempts["count"] == 1:
            return langgraph_codex.execution.ExecutionResult(
                stdout="",
                stderr="try again",
                returncode=1,
            )

        return langgraph_codex.execution.ExecutionResult(stdout="ok", stderr="", returncode=0)

    executor = langgraph_codex.execution.FakeExecutor(responder=responder)
    graph = langgraph_codex.graph.build_retry_graph(executor=executor)

    result = graph.invoke(
        {
            "workspace_path": tmp_path,
            "task_title": "Recover",
            "objective": "Succeed after retry.",
            "max_retries": 2,
        }
    )

    assert len(executor.requests) == 2
    assert result["retry_count"] == 1
    assert result["validation_result"].passed is True
