import pathlib
import sys

import langgraph_codex.utils.validation


def test_require_artifacts_reports_missing_keys() -> None:
    validator = langgraph_codex.utils.validation.require_artifacts(["summary", "score"])

    result = validator({"artifacts": {"summary": "done"}})

    assert result.passed is False
    assert result.details == {"missing": ["score"]}


def test_require_files_uses_workspace_path(tmp_path: pathlib.Path) -> None:
    required_file = tmp_path / "artifact.txt"
    required_file.write_text("content", encoding="utf-8")
    validator = langgraph_codex.utils.validation.require_files(["artifact.txt"])

    result = validator({"workspace_path": tmp_path})

    assert result.passed is True


def test_json_artifact_accepts_string_json() -> None:
    validator = langgraph_codex.utils.validation.require_json_artifact("payload")

    result = validator({"artifacts": {"payload": '{"ok": true}'}})

    assert result.passed is True


def test_command_validator_runs_generic_command(tmp_path: pathlib.Path) -> None:
    validator = langgraph_codex.utils.validation.command_validator(
        [sys.executable, "-c", "print('ok')"],
        timeout_seconds=5,
    )

    result = validator({"workspace_path": tmp_path})

    assert result.passed is True
    assert result.details["returncode"] == 0
    assert result.details["stdout"] == "ok\n"
