import collections
import csv
import hashlib
import json
import pathlib
import tempfile
import typing

import langgraph_codex.codex_runtime as codex_runtime

import langgraph_codex.execution
import langgraph_codex.graph
import langgraph_codex.utils.validation as validation_utils

PROFILE_PATH = "quality_profile.md"


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


def write_orders_csv(workspace_path: pathlib.Path) -> pathlib.Path:
    orders_path = workspace_path / "orders.csv"
    rows = [
        {"order_id": "A100", "region": "north", "amount": "125.50", "status": "paid"},
        {"order_id": "A101", "region": "south", "amount": "", "status": "pending"},
        {"order_id": "A102", "region": "north", "amount": "82.10", "status": "paid"},
        {"order_id": "A103", "region": "", "amount": "210.00", "status": "refunded"},
        {"order_id": "A103", "region": "west", "amount": "210.00", "status": "paid"},
    ]
    with orders_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["order_id", "region", "amount", "status"])
        writer.writeheader()
        writer.writerows(rows)

    return orders_path


def profile_orders_dataset(
    state: langgraph_codex.graph.WorkflowState,
) -> dict[str, typing.Any]:
    workspace_path = pathlib.Path(state["workspace_path"])
    orders_path = workspace_path / "orders.csv"
    with orders_path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    order_ids = [row["order_id"] for row in rows]
    duplicate_order_ids = sorted(
        {order_id for order_id in order_ids if order_ids.count(order_id) > 1}
    )
    missing_by_column = {
        column: sum(1 for row in rows if not row[column])
        for column in ["order_id", "region", "amount", "status"]
    }
    amounts = [float(row["amount"]) for row in rows if row["amount"]]
    status_counts = collections.Counter(row["status"] for row in rows)
    region_counts = collections.Counter(row["region"] or "(missing)" for row in rows)
    deterministic_artifacts = {
        "row_count": len(rows),
        "column_count": 4,
        "duplicate_order_ids": duplicate_order_ids,
        "missing_by_column": missing_by_column,
        "amount_min": min(amounts),
        "amount_max": max(amounts),
        "status_counts": dict(sorted(status_counts.items())),
        "region_counts": dict(sorted(region_counts.items())),
        "source_sha256": sha256_file(orders_path),
        "expected_profile_path": PROFILE_PATH,
    }

    return {
        "context": {
            "Scenario": (
                "You are profiling a small order export in a temporary sample workspace. "
                "This is not a code repository task."
            ),
            "Dataset Shape": f"{len(rows)} rows and 4 columns.",
            "Missing Values": missing_by_column,
            "Duplicate Order IDs": duplicate_order_ids,
            "Amount Range": f"{min(amounts)} to {max(amounts)}",
            "Status Counts": dict(sorted(status_counts.items())),
            "Region Counts": dict(sorted(region_counts.items())),
            "Required Profile": (
                f"Create `{PROFILE_PATH}` with separate `Deterministic Profile` and "
                "`Recommended Data Checks` sections."
            ),
        },
        "files": [
            {"path": orders_path.name, "description": "Small order export with quality issues."}
        ],
        "artifacts": deterministic_artifacts,
        "metadata": deterministic_artifacts,
        "acceptance_criteria": [
            f"Create `{PROFILE_PATH}` in the workspace.",
            "Expose duplicate identifiers.",
            "Expose missing values by column.",
            (
                "Include these exact deterministic fact lines: `row_count=5`, "
                "`duplicate_order_ids=A103`, `missing_region=1`, and `missing_amount=1`."
            ),
            "Do not modify `orders.csv`.",
        ],
        "additional_instructions": [
            (
                "Do not run tests, use git, install dependencies, or assume this workspace "
                "is a code project."
            ),
            "Use only the generated CSV and the deterministic context in this prompt.",
        ],
    }


def validate_quality_profile(
    state: typing.MutableMapping[str, typing.Any],
) -> validation_utils.ValidationResult:
    workspace_path = pathlib.Path(state["workspace_path"])
    metadata = dict(state.get("metadata", {}) or {})
    profile_path = workspace_path / PROFILE_PATH
    orders_path = workspace_path / "orders.csv"

    if not profile_path.exists():
        return validation_utils.failing_validation(
            message=f"Expected Codex to create {PROFILE_PATH}.",
            details={"missing": PROFILE_PATH},
        )

    if sha256_file(orders_path) != metadata["source_sha256"]:
        return validation_utils.failing_validation(
            message="Codex modified orders.csv.",
            details={
                "expected_sha256": metadata["source_sha256"],
                "actual_sha256": sha256_file(orders_path),
            },
        )

    profile_text = read_text(profile_path)
    required_fragments = [
        "row_count=5",
        "duplicate_order_ids=A103",
        "missing_region=1",
        "missing_amount=1",
    ]
    missing_fragments = [
        fragment for fragment in required_fragments if fragment not in profile_text
    ]
    if missing_fragments:
        return validation_utils.failing_validation(
            message=f"{PROFILE_PATH} is missing deterministic profile facts.",
            details={"missing_fragments": missing_fragments},
        )

    return validation_utils.passing_validation(
        message=f"{PROFILE_PATH} exists, preserves orders.csv, and includes expected facts."
    )


def main() -> None:
    codex_runtime.ensure_codex_authorized()
    codex_runtime.print_authorization_status()
    with tempfile.TemporaryDirectory(prefix="langgraph-codex-orders-") as temporary_directory:
        workspace_path = pathlib.Path(temporary_directory)
        orders_path = write_orders_csv(workspace_path)

        print_section(
            "Scenario",
            "Real CodexExecutor demo: dataset quality profile in a temporary sample workspace.",
        )
        print_section("Temporary Workspace", workspace_path)
        print_section("Generated Files Before Execution")
        print_workspace_files(workspace_path)

        executor = codex_runtime.create_codex_executor()
        graph = langgraph_codex.graph.build_execution_graph(
            executor=executor,
            context_builder=profile_orders_dataset,
            validators=[validate_quality_profile],
        )
        result = graph.invoke(
            {
                "workspace_path": workspace_path,
                "task_title": "Profile order data quality",
                "objective": (
                    f"Read `{orders_path.name}` and create `{PROFILE_PATH}` as a concise "
                    "dataset quality profile for an operations analyst."
                ),
                "constraints": [
                    "Work only inside this temporary sample workspace.",
                    "Do not modify the source CSV.",
                    "Keep deterministic profile facts separate from recommended follow-up checks.",
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
