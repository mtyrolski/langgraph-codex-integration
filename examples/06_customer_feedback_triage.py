import collections
import csv
import hashlib
import json
import pathlib
import tempfile
import typing

import langgraph_codex.runtime as runtime

import langgraph_codex.execution
import langgraph_codex.graph
import langgraph_codex.utils.validation as validation_utils

REPORT_PATH = "triage_summary.md"


def print_section(title: str, body: typing.Any = "") -> None:
    print(f"\n{'=' * 80}\n{title}\n{'=' * 80}")
    if body != "":
        print(body)


def format_json(value: typing.Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, default=str)


def read_text(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def sha256_file(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def print_workspace_files(workspace_path: pathlib.Path) -> None:
    files = sorted(path for path in workspace_path.rglob("*") if path.is_file())
    if not files:
        print("(no files)")
        return

    for path in files:
        relative_path = path.relative_to(workspace_path)
        print(f"\n--- {relative_path} ---")
        print(read_text(path))


def write_feedback_csv(workspace_path: pathlib.Path) -> pathlib.Path:
    feedback_path = workspace_path / "feedback.csv"
    rows = [
        {
            "channel": "email",
            "segment": "enterprise",
            "sentiment": "negative",
            "message": "Invoices sometimes arrive with missing purchase order references.",
        },
        {
            "channel": "chat",
            "segment": "startup",
            "sentiment": "positive",
            "message": "The onboarding checklist made the first week much easier.",
        },
        {
            "channel": "survey",
            "segment": "enterprise",
            "sentiment": "negative",
            "message": "Exported account reports do not include enough billing detail.",
        },
        {
            "channel": "email",
            "segment": "nonprofit",
            "sentiment": "neutral",
            "message": "The dashboard labels are understandable after a short walkthrough.",
        },
    ]
    with feedback_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["channel", "segment", "sentiment", "message"])
        writer.writeheader()
        writer.writerows(rows)

    return feedback_path


def build_feedback_context(
    state: langgraph_codex.graph.WorkflowState,
) -> dict[str, typing.Any]:
    workspace_path = pathlib.Path(state["workspace_path"])
    feedback_path = workspace_path / "feedback.csv"
    with feedback_path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    sentiment_counts = collections.Counter(row["sentiment"] for row in rows)
    segment_counts = collections.Counter(row["segment"] for row in rows)
    channel_counts = collections.Counter(row["channel"] for row in rows)
    negative_messages = [
        f"{row['segment']}: {row['message']}" for row in rows if row["sentiment"] == "negative"
    ]
    top_segment = segment_counts.most_common(1)[0][0]
    deterministic_artifacts = {
        "record_count": len(rows),
        "negative_count": sentiment_counts["negative"],
        "top_segment": top_segment,
        "channel_counts": dict(sorted(channel_counts.items())),
        "sentiment_counts": dict(sorted(sentiment_counts.items())),
        "segment_counts": dict(sorted(segment_counts.items())),
        "source_sha256": sha256_file(feedback_path),
        "expected_report_path": REPORT_PATH,
    }

    return {
        "context": {
            "Scenario": (
                "You are triaging a small customer feedback export in a temporary sample "
                "workspace. This is not a code repository task."
            ),
            "Dataset": f"{len(rows)} feedback records from email, chat, and survey channels.",
            "Sentiment Counts": dict(sorted(sentiment_counts.items())),
            "Segment Counts": dict(sorted(segment_counts.items())),
            "Channel Counts": dict(sorted(channel_counts.items())),
            "Negative Themes": "\n".join([f"- {message}" for message in negative_messages]),
            "Required Report": (
                f"Create `{REPORT_PATH}` with separate `Deterministic Facts` and "
                "`Recommended Follow-up` sections."
            ),
        },
        "files": [{"path": feedback_path.name, "description": "Raw customer feedback export."}],
        "artifacts": deterministic_artifacts,
        "metadata": deterministic_artifacts,
        "acceptance_criteria": [
            f"Create `{REPORT_PATH}` in the workspace.",
            "Identify the highest-priority customer segment.",
            (
                "Include these exact deterministic fact lines: `record_count=4`, "
                "`negative_count=2`, and `top_segment=enterprise`."
            ),
            "Separate deterministic counts from suggested follow-up actions.",
            "Do not modify `feedback.csv`.",
        ],
        "additional_instructions": [
            (
                "Do not run tests, use git, install dependencies, or assume this workspace "
                "is a code project."
            ),
            "Use only the generated CSV and the deterministic context in this prompt.",
        ],
    }


def validate_triage_report(
    state: typing.MutableMapping[str, typing.Any],
) -> validation_utils.ValidationResult:
    workspace_path = pathlib.Path(state["workspace_path"])
    metadata = dict(state.get("metadata", {}) or {})
    report_path = workspace_path / REPORT_PATH
    feedback_path = workspace_path / "feedback.csv"

    if not report_path.exists():
        return validation_utils.failing_validation(
            message=f"Expected Codex to create {REPORT_PATH}.",
            details={"missing": REPORT_PATH},
        )

    if sha256_file(feedback_path) != metadata["source_sha256"]:
        return validation_utils.failing_validation(
            message="Codex modified feedback.csv.",
            details={
                "expected_sha256": metadata["source_sha256"],
                "actual_sha256": sha256_file(feedback_path),
            },
        )

    report_text = read_text(report_path)
    required_fragments = [
        "record_count=4",
        "negative_count=2",
        "top_segment=enterprise",
    ]
    missing_fragments = [fragment for fragment in required_fragments if fragment not in report_text]
    if missing_fragments:
        return validation_utils.failing_validation(
            message=f"{REPORT_PATH} is missing deterministic facts.",
            details={"missing_fragments": missing_fragments},
        )

    return validation_utils.passing_validation(
        message=f"{REPORT_PATH} exists, preserves feedback.csv, and includes expected facts."
    )


def main() -> None:
    runtime.ensure_codex_authorized()
    runtime.print_authorization_status()
    with tempfile.TemporaryDirectory(prefix="langgraph-codex-feedback-") as temporary_directory:
        workspace_path = pathlib.Path(temporary_directory)
        feedback_path = write_feedback_csv(workspace_path)

        print_section(
            "Scenario",
            "Real CodexExecutor demo: customer feedback triage in a temporary sample workspace.",
        )
        print_section("Temporary Workspace", workspace_path)
        print_section("Generated Files Before Execution")
        print_workspace_files(workspace_path)

        executor = runtime.create_codex_executor()
        graph = langgraph_codex.graph.build_execution_graph(
            executor=executor,
            context_builder=build_feedback_context,
            validators=[validate_triage_report],
        )
        result = graph.invoke(
            {
                "workspace_path": workspace_path,
                "task_title": "Triage customer feedback",
                "objective": (
                    f"Read `{feedback_path.name}` and create `{REPORT_PATH}` as a concise "
                    "triage summary for customer support leadership."
                ),
                "constraints": [
                    "Work only inside this temporary sample workspace.",
                    "Do not hide deterministic counts.",
                    "Treat recommendations as suggestions, not validated facts.",
                    "Do not modify the source CSV.",
                ],
                "execution_options": {"timeout_seconds": 300},
            }
        )

        print_section(
            "Deterministic Context",
            format_json(
                {
                    "context": result.get("context", {}),
                    "files": result.get("files", []),
                    "acceptance_criteria": result.get("acceptance_criteria", []),
                    "additional_instructions": result.get("additional_instructions", []),
                }
            ),
        )
        print_section("Deterministic Artifacts", format_json(result.get("artifacts", {})))
        print_section("Rendered Prompt", result["rendered_prompt"])

        execution_result = result["execution_result"]
        print_section("Execution Return Code", execution_result.returncode)
        print_section("Execution Stdout", execution_result.stdout or "(empty)")
        print_section("Execution Stderr", execution_result.stderr or "(empty)")
        print_section(
            "Execution Structured Outputs", format_json(execution_result.structured_outputs)
        )
        print_section("Validation Result", format_json(result.get("review_result", {})))
        print_section("Generated Files After Execution")
        print_workspace_files(workspace_path)


if __name__ == "__main__":
    main()
