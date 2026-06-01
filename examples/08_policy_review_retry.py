import hashlib
import json
import pathlib
import tempfile
import typing

import langgraph_codex.codex_runtime as codex_runtime

import langgraph_codex.execution
import langgraph_codex.graph
import langgraph_codex.utils.validation as validation_utils

RISK_REGISTER_PATH = "risk_register.md"


def read_text(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def sha256_file(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def format_json(value: typing.Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, default=str)


def print_workspace_files(workspace_path: pathlib.Path) -> None:
    files = sorted(path for path in workspace_path.rglob("*") if path.is_file())
    for path in files:
        relative_path = path.relative_to(workspace_path)
        codex_runtime.print_section(f"Workspace file: {relative_path}", read_text(path))


def write_policy(workspace_path: pathlib.Path) -> pathlib.Path:
    policy_path = workspace_path / "travel_policy.md"
    policy_path.write_text(
        "\n".join(
            [
                "# Travel Policy",
                "",
                "- Employees may book economy flights without prior approval.",
                "- Hotel stays above 250 USD per night require manager approval.",
                "- International trips require finance review.",
                "- Receipts must be submitted within 14 days.",
            ]
        ),
        encoding="utf-8",
    )
    return policy_path


def build_policy_context(
    state: langgraph_codex.graph.WorkflowState,
) -> dict[str, typing.Any]:
    workspace_path = pathlib.Path(state["workspace_path"])
    policy_path = workspace_path / "travel_policy.md"
    policy_text = read_text(policy_path)
    approval_mentions = policy_text.lower().count("approval") + policy_text.lower().count("review")
    deterministic_artifacts = {
        "approval_or_review_mentions": approval_mentions,
        "source_sha256": sha256_file(policy_path),
        "expected_risk_register_path": RISK_REGISTER_PATH,
    }

    return {
        "context": {
            "Scenario": "Review a small policy draft in a temporary non-code workspace.",
            "Policy Text": policy_text,
            "Deterministic Scan": f"Found {approval_mentions} approval or review mentions.",
            "Required Output": (
                f"Create `{RISK_REGISTER_PATH}` with `Deterministic Facts`, `Risks`, "
                "and `Controls` sections."
            ),
        },
        "files": [{"path": policy_path.name, "description": "Internal travel policy draft."}],
        "artifacts": deterministic_artifacts,
        "metadata": deterministic_artifacts,
        "acceptance_criteria": [
            f"Create `{RISK_REGISTER_PATH}`.",
            "Include the exact line `approval_or_review_mentions=3`.",
            "Include at least one risk and one control recommendation.",
            "Do not modify `travel_policy.md`.",
        ],
    }


def validate_risk_register(
    state: typing.MutableMapping[str, typing.Any],
) -> validation_utils.ValidationResult:
    workspace_path = pathlib.Path(state["workspace_path"])
    metadata = dict(state.get("metadata", {}) or {})
    policy_path = workspace_path / "travel_policy.md"
    risk_register_path = workspace_path / RISK_REGISTER_PATH

    if not risk_register_path.exists():
        return validation_utils.failing_validation(
            message=f"Expected Codex to create {RISK_REGISTER_PATH}.",
            details={"missing": RISK_REGISTER_PATH},
        )
    if sha256_file(policy_path) != metadata["source_sha256"]:
        return validation_utils.failing_validation(
            message="Codex modified travel_policy.md.",
            details={"expected_sha256": metadata["source_sha256"]},
        )

    risk_register_text = read_text(risk_register_path)
    required_fragments = ["approval_or_review_mentions=3", "risk", "control"]
    missing_fragments = [
        fragment for fragment in required_fragments if fragment not in risk_register_text.lower()
    ]
    if missing_fragments:
        return validation_utils.failing_validation(
            message=f"{RISK_REGISTER_PATH} is incomplete.",
            details={"missing_fragments": missing_fragments},
        )

    return validation_utils.passing_validation(
        message=f"{RISK_REGISTER_PATH} exists and preserves travel_policy.md."
    )


def main() -> None:
    codex_runtime.ensure_codex_authorized()
    codex_runtime.print_authorization_status()
    with tempfile.TemporaryDirectory(prefix="langgraph-codex-policy-") as temporary_directory:
        workspace_path = pathlib.Path(temporary_directory)
        write_policy(workspace_path)

        codex_runtime.print_section("Scenario", "Real CodexExecutor policy review with retry.")
        codex_runtime.print_section("Temporary Workspace", workspace_path)
        print_workspace_files(workspace_path)

        executor = codex_runtime.create_codex_executor()
        graph = langgraph_codex.graph.build_retry_graph(
            executor=executor,
            validators=[validate_risk_register],
            context_builder=build_policy_context,
        )
        result = graph.invoke(
            {
                "workspace_path": workspace_path,
                "task_title": "Review a travel policy",
                "objective": (
                    f"Read `travel_policy.md` and create `{RISK_REGISTER_PATH}` as a concise "
                    "risk register for operations leadership."
                ),
                "constraints": [
                    "Work only inside the temporary sample workspace.",
                    "Do not modify the source policy.",
                    "Use deterministic facts exactly as provided.",
                ],
                "max_retries": 1,
                "execution_options": {"timeout_seconds": 300},
            }
        )

        execution_result = result["execution_result"]
        codex_runtime.print_section("Deterministic Artifacts", format_json(result["artifacts"]))
        codex_runtime.print_section("Rendered Prompt", result["rendered_prompt"])
        codex_runtime.print_section("Retry Count", result["retry_count"])
        codex_runtime.print_section("Review Result", format_json(result["review_result"]))
        codex_runtime.print_section("Execution Return Code", execution_result.returncode)
        codex_runtime.print_section("Execution Stdout", execution_result.stdout or "(empty)")
        codex_runtime.print_section("Execution Stderr", execution_result.stderr or "(empty)")
        print_workspace_files(workspace_path)


if __name__ == "__main__":
    main()
