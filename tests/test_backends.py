import pathlib
import typing

import pytest

import langgraph_codex.backends
import langgraph_codex.backends.exec
import langgraph_codex.utils.subprocess


def test_fake_backend_returns_configured_result_and_captures_request(
    tmp_path: pathlib.Path,
) -> None:
    backend = langgraph_codex.backends.FakeBackend(
        stdout="done",
        stderr="",
        returncode=0,
        structured_outputs={"value": 1},
    )
    request = langgraph_codex.backends.BackendRequest(
        workspace_path=tmp_path,
        prompt="Perform work.",
    )

    result = backend.execute(request)

    assert result.succeeded is True
    assert result.stdout == "done"
    assert result.structured_outputs == {"value": 1}
    assert backend.requests == [request]


def test_fake_backend_can_use_responder(tmp_path: pathlib.Path) -> None:
    def responder(
        request: langgraph_codex.backends.BackendRequest,
    ) -> langgraph_codex.backends.BackendResult:
        return langgraph_codex.backends.BackendResult(
            stdout=f"prompt={request.prompt}",
            stderr="",
            returncode=0,
        )

    backend = langgraph_codex.backends.FakeBackend(responder=responder)
    result = backend.execute(
        langgraph_codex.backends.BackendRequest(
            workspace_path=tmp_path,
            prompt="abc",
        )
    )

    assert result.stdout == "prompt=abc"


def test_codex_backend_builds_safe_exec_command(tmp_path: pathlib.Path) -> None:
    backend = langgraph_codex.backends.CodexBackend(
        codex_bin="codex",
        model="gpt-5.5-mini",
        sandbox="workspace-write",
        approval_policy="never",
        extra_args=["--json"],
    )

    command = backend.build_command(tmp_path)

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


def test_codex_backend_rejects_dangerous_flags(tmp_path: pathlib.Path) -> None:
    backend = langgraph_codex.backends.CodexBackend(
        extra_args=["--dangerously-bypass-approvals-and-sandbox=true"]
    )

    with pytest.raises(ValueError, match="Refusing dangerous Codex flag"):
        backend.build_command(tmp_path)


def test_codex_backend_execute_passes_prompt_on_stdin(
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
    backend = langgraph_codex.backends.CodexBackend(timeout_seconds=30)
    request = langgraph_codex.backends.BackendRequest(
        workspace_path=tmp_path,
        prompt="Do work.",
        options={"timeout_seconds": 10},
    )

    result = backend.execute(request)

    assert result.stdout == "ok"
    assert calls[0]["input_text"] == "Do work."
    assert calls[0]["timeout_seconds"] == 10
    assert calls[0]["args"][-1] == "-"
