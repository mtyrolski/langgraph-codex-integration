import hashlib
import json
import pathlib
import tempfile
import typing

import _codex_runtime

import langgraph_codex.execution
import langgraph_codex.graph
import langgraph_codex.utils.validation as validation_utils

REMEDIATION_PATH = "remediation_plan.md"


def read_text(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def sha256_file(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def format_json(value: typing.Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, default=str)


def print_workspace_files(workspace_path: pathlib.Path) -> None:
    for path in sorted(candidate for candidate in workspace_path.rglob("*") if candidate.is_file()):
        _codex_runtime.print_section(
            f"Workspace file: {path.relative_to(workspace_path)}", read_text(path)
        )


def write_service_config(workspace_path: pathlib.Path) -> pathlib.Path:
    config_path = workspace_path / "service_config.json"
    config = {
        "service": "appointment-reminders",
        "retry_attempts": 6,
        "timeout_seconds": 45,
        "batch_size": 500,
        "channels": ["email", "sms"],
        "owner": "operations",
    }
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    return config_path


def build_config_context(
    state: langgraph_codex.graph.WorkflowState,
) -> dict[str, typing.Any]:
    workspace_path = pathlib.Path(state["workspace_path"])
    config_path = workspace_path / "service_config.json"
    config = json.loads(read_text(config_path))
    deterministic_findings = []

    if config["retry_attempts"] > 3:
        deterministic_findings.append("retry_attempts exceeds the recommended maximum of 3")
    if config["timeout_seconds"] > 30:
        deterministic_findings.append("timeout_seconds exceeds the recommended maximum of 30")
    if config["batch_size"] > 250:
        deterministic_findings.append("batch_size exceeds the recommended maximum of 250")

    deterministic_artifacts = {
        "finding_count": len(deterministic_findings),
        "deterministic_findings": deterministic_findings,
        "source_sha256": sha256_file(config_path),
        "expected_remediation_path": REMEDIATION_PATH,
    }

    return {
        "context": {
            "Scenario": "Review JSON service configuration in a temporary non-code workspace.",
            "Config": json.dumps(config, indent=2),
            "Deterministic Findings": deterministic_findings,
            "Required Output": (
                f"Create `{REMEDIATION_PATH}` with `Deterministic Findings` and "
                "`Remediation Plan` sections."
            ),
        },
        "files": [{"path": config_path.name, "description": "JSON service configuration."}],
        "artifacts": deterministic_artifacts,
        "metadata": deterministic_artifacts,
        "acceptance_criteria": [
            f"Create `{REMEDIATION_PATH}`.",
            "Include the exact line `finding_count=3`.",
            "Address retry_attempts, timeout_seconds, and batch_size.",
            "Do not modify `service_config.json`.",
        ],
    }


def validate_remediation_plan(
    state: typing.MutableMapping[str, typing.Any],
) -> validation_utils.ValidationResult:
    workspace_path = pathlib.Path(state["workspace_path"])
    metadata = dict(state.get("metadata", {}) or {})
    config_path = workspace_path / "service_config.json"
    remediation_path = workspace_path / REMEDIATION_PATH

    if not remediation_path.exists():
        return validation_utils.failing_validation(
            message=f"Expected Codex to create {REMEDIATION_PATH}.",
            details={"missing": REMEDIATION_PATH},
        )
    if sha256_file(config_path) != metadata["source_sha256"]:
        return validation_utils.failing_validation(
            message="Codex modified service_config.json.",
            details={"expected_sha256": metadata["source_sha256"]},
        )

    remediation_text = read_text(remediation_path)
    required_fragments = ["finding_count=3", "retry_attempts", "timeout_seconds", "batch_size"]
    missing_fragments = [
        fragment for fragment in required_fragments if fragment not in remediation_text
    ]
    if missing_fragments:
        return validation_utils.failing_validation(
            message=f"{REMEDIATION_PATH} does not cover every deterministic finding.",
            details={"missing_fragments": missing_fragments},
        )

    return validation_utils.passing_validation(
        message=f"{REMEDIATION_PATH} exists and service_config.json is unchanged."
    )


def main() -> None:
    _codex_runtime.ensure_codex_authorized()
    _codex_runtime.print_authorization_status()
    with tempfile.TemporaryDirectory(prefix="langgraph-codex-config-") as temporary_directory:
        workspace_path = pathlib.Path(temporary_directory)
        write_service_config(workspace_path)

        _codex_runtime.print_section("Scenario", "Real CodexExecutor service config review.")
        _codex_runtime.print_section("Temporary Workspace", workspace_path)
        print_workspace_files(workspace_path)

        executor = _codex_runtime.create_codex_executor()
        graph = langgraph_codex.graph.build_execution_graph(
            executor=executor,
            validators=[validate_remediation_plan],
            context_builder=build_config_context,
        )
        result = graph.invoke(
            {
                "workspace_path": workspace_path,
                "task_title": "Review service configuration",
                "objective": (
                    f"Read `service_config.json` and create `{REMEDIATION_PATH}` as a "
                    "structured remediation plan."
                ),
                "constraints": [
                    "Work only inside the temporary sample workspace.",
                    "Do not modify the source JSON.",
                    "Preserve every deterministic finding.",
                ],
                "execution_options": {"timeout_seconds": 300},
            }
        )

        execution_result = result["execution_result"]
        _codex_runtime.print_section("Deterministic Artifacts", format_json(result["artifacts"]))
        _codex_runtime.print_section("Rendered Prompt", result["rendered_prompt"])
        _codex_runtime.print_section("Review Result", format_json(result["review_result"]))
        _codex_runtime.print_section("Execution Return Code", execution_result.returncode)
        _codex_runtime.print_section("Execution Stdout", execution_result.stdout or "(empty)")
        _codex_runtime.print_section("Execution Stderr", execution_result.stderr or "(empty)")
        print_workspace_files(workspace_path)


if __name__ == "__main__":
    main()
