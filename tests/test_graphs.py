import pathlib
import typing

import langgraph.graph

import langgraph_codex.execution
import langgraph_codex.graph


class AppState(typing.TypedDict, total=False):
    workspace_path: pathlib.Path
    ticket: str
    codex_result: langgraph_codex.execution.ExecutionResult
    answer: str


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


def test_codex_node_can_replace_node_in_existing_langgraph(tmp_path: pathlib.Path) -> None:
    executor = langgraph_codex.execution.FakeExecutor(stdout="priority=medium")

    def load_ticket(_state: AppState) -> dict[str, str]:
        return {"ticket": "Billing export is missing purchase order references."}

    def finalize(state: AppState) -> dict[str, str]:
        codex_result = typing.cast(
            langgraph_codex.execution.ExecutionResult,
            state.get("codex_result"),
        )
        return {"answer": codex_result.stdout}

    graph: typing.Any = langgraph.graph.StateGraph(AppState)
    graph.add_node("load_ticket", load_ticket)
    graph.add_node(
        "codex_triage",
        langgraph_codex.graph.create_codex_node(
            executor=executor,
            prompt_builder=lambda state: f"Triage this support ticket: {state['ticket']}",
            workspace_path=lambda state: typing.cast(pathlib.Path, state.get("workspace_path")),
        ),
    )
    graph.add_node("finalize", finalize)
    graph.add_edge(langgraph.graph.START, "load_ticket")
    graph.add_edge("load_ticket", "codex_triage")
    graph.add_edge("codex_triage", "finalize")
    graph.add_edge("finalize", langgraph.graph.END)

    result = graph.compile().invoke({"workspace_path": tmp_path})

    assert result["answer"] == "priority=medium"
    assert executor.requests[0].workspace_path == tmp_path.resolve()
    assert executor.requests[0].prompt == (
        "Triage this support ticket: Billing export is missing purchase order references."
    )


def test_codex_node_can_map_result_to_application_state(tmp_path: pathlib.Path) -> None:
    executor = langgraph_codex.execution.FakeExecutor(stdout="accepted")
    node = langgraph_codex.graph.create_codex_node(
        executor=executor,
        prompt_builder=lambda _state: "Review the proposed change.",
        workspace_path=tmp_path,
        result_mapper=lambda result: {"answer": result.stdout.upper()},
    )

    result = node({})

    assert result == {"answer": "ACCEPTED"}


def test_codex_node_passes_metadata_options_and_custom_result_key(
    tmp_path: pathlib.Path,
) -> None:
    executor = langgraph_codex.execution.FakeExecutor(stdout="done")
    node = langgraph_codex.graph.create_codex_node(
        executor=executor,
        prompt_builder=lambda state: f"Process {state['item_id']}",
        workspace_path=tmp_path,
        result_key="agent_result",
        metadata_builder=lambda state: {"item_id": state["item_id"]},
        options_builder=lambda _state: {"timeout_seconds": 15},
    )

    result = node({"item_id": "A-42"})

    assert result["agent_result"].stdout == "done"
    assert executor.requests[0].metadata == {"item_id": "A-42"}
    assert executor.requests[0].options == {"timeout_seconds": 15}
    assert executor.requests[0].prompt == "Process A-42"
