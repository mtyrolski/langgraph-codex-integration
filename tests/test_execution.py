import pathlib
import typing

import pytest

import langgraph_codex.execution
import langgraph_codex.utils.subprocess


def test_fake_executor_returns_configured_result_and_captures_request(
    tmp_path: pathlib.Path,
) -> None:
    executor = langgraph_codex.execution.FakeExecutor(
        stdout="done",
        stderr="",
        returncode=0,
        structured_outputs={"value": 1},
    )
    request = langgraph_codex.execution.ExecutionRequest(
        workspace_path=tmp_path,
        prompt="Perform work.",
    )

    result = executor.execute(request)

    assert result.succeeded is True
    assert result.stdout == "done"
    assert result.structured_outputs == {"value": 1}
    assert executor.requests == [request]


def test_fake_executor_can_use_responder(tmp_path: pathlib.Path) -> None:
    def responder(
        request: langgraph_codex.execution.ExecutionRequest,
    ) -> langgraph_codex.execution.ExecutionResult:
        return langgraph_codex.execution.ExecutionResult(
            stdout=f"prompt={request.prompt}",
            stderr="",
            returncode=0,
        )

    executor = langgraph_codex.execution.FakeExecutor(responder=responder)
    result = executor.execute(
        langgraph_codex.execution.ExecutionRequest(
            workspace_path=tmp_path,
            prompt="abc",
        )
    )

    assert result.stdout == "prompt=abc"


def test_codex_executor_builds_safe_exec_command(tmp_path: pathlib.Path) -> None:
    executor = langgraph_codex.execution.CodexExecutor(
        codex_bin="codex",
        model="gpt-5.5-mini",
        sandbox="workspace-write",
        approval_policy="never",
        extra_args=["--json"],
    )

    command = executor.build_command(tmp_path)

    assert command == [
        "codex",
        "exec",
        "-m",
        "gpt-5.5-mini",
        "-s",
        "workspace-write",
        "-C",
        str(tmp_path.resolve()),
        "-c",
        "approval_policy='never'",
        "--skip-git-repo-check",
        "--json",
        "-",
    ]


def test_codex_executor_can_use_cli_default_model(tmp_path: pathlib.Path) -> None:
    executor = langgraph_codex.execution.CodexExecutor(model=None)

    command = executor.build_command(tmp_path)

    assert "-m" not in command
    assert "--skip-git-repo-check" in command
    assert command[-1] == "-"


def test_codex_executor_rejects_dangerous_flags(tmp_path: pathlib.Path) -> None:
    executor = langgraph_codex.execution.CodexExecutor(
        extra_args=["--dangerously-bypass-approvals-and-sandbox=true"]
    )

    with pytest.raises(ValueError, match="Refusing dangerous Codex flag"):
        executor.build_command(tmp_path)


def test_codex_executor_execute_passes_prompt_on_stdin(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    calls: list[dict[str, typing.Any]] = []

    def fake_run_command(
        args: list[str],
        cwd: str | pathlib.Path,
        timeout_seconds: int | float | None = None,
        input_text: str | None = None,
    ) -> langgraph_codex.utils.subprocess.CommandResult:
        calls.append(
            {
                "args": args,
                "cwd": cwd,
                "timeout_seconds": timeout_seconds,
                "input_text": input_text,
            }
        )
        return langgraph_codex.utils.subprocess.CommandResult(
            args=args,
            cwd=pathlib.Path(cwd),
            stdout="ok",
            stderr="",
            returncode=0,
        )

    monkeypatch.setattr(
        langgraph_codex.utils.subprocess,
        "run_command",
        fake_run_command,
    )
    executor = langgraph_codex.execution.CodexExecutor(timeout_seconds=30)
    request = langgraph_codex.execution.ExecutionRequest(
        workspace_path=tmp_path,
        prompt="Do work.",
        options={"timeout_seconds": 10},
    )

    result = executor.execute(request)

    assert result.stdout == "ok"
    assert calls[0]["input_text"] == "Do work."
    assert calls[0]["timeout_seconds"] == 10
    assert calls[0]["args"][-1] == "-"


@pytest.mark.parametrize(
    ("timeout", "error_type", "message"),
    [
        ("slow", TypeError, "timeout_seconds must be int or float"),
        (0, ValueError, "timeout_seconds must be positive"),
    ],
)
def test_codex_executor_rejects_invalid_request_timeout(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
    timeout: object,
    error_type: type[Exception],
    message: str,
) -> None:
    def unexpected_run_command(
        _args: list[str],
        _cwd: str | pathlib.Path,
        timeout_seconds: int | float | None = None,
        input_text: str | None = None,
    ) -> langgraph_codex.utils.subprocess.CommandResult:
        raise AssertionError("run_command should not be called")

    monkeypatch.setattr(
        langgraph_codex.utils.subprocess,
        "run_command",
        unexpected_run_command,
    )
    executor = langgraph_codex.execution.CodexExecutor()
    request = langgraph_codex.execution.ExecutionRequest(
        workspace_path=tmp_path,
        prompt="Do work.",
        options={"timeout_seconds": timeout},
    )

    with pytest.raises(error_type, match=message):
        executor.execute(request)
