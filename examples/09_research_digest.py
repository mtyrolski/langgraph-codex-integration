import hashlib
import json
import pathlib
import tempfile
import typing

import langgraph_codex.codex_runtime as codex_runtime

import langgraph_codex.execution
import langgraph_codex.graph
import langgraph_codex.utils.validation as validation_utils

DIGEST_PATH = "research_digest.md"


def read_text(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def sha256_file(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def format_json(value: typing.Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, default=str)


def print_workspace_files(workspace_path: pathlib.Path) -> None:
    for path in sorted(candidate for candidate in workspace_path.rglob("*") if candidate.is_file()):
        codex_runtime.print_section(
            f"Workspace file: {path.relative_to(workspace_path)}", read_text(path)
        )


def write_research_notes(workspace_path: pathlib.Path) -> list[pathlib.Path]:
    notes = {
        "interview_01.md": [
            "# Interview 01",
            "The team loses time reconciling spreadsheet versions after partner reviews.",
            "A shared review checklist reduced mistakes during the pilot.",
        ],
        "interview_02.md": [
            "# Interview 02",
            "Analysts want a short evidence trail for every recommendation.",
            "Long narrative reports are rarely read before weekly planning.",
        ],
        "field_note.md": [
            "# Field Note",
            "Stakeholders trusted summaries more when source excerpts were attached.",
        ],
    }
    paths: list[pathlib.Path] = []
    for filename, lines in notes.items():
        path = workspace_path / filename
        path.write_text("\n".join(lines), encoding="utf-8")
        paths.append(path)

    return paths


def build_research_context(
    state: langgraph_codex.graph.WorkflowState,
) -> dict[str, typing.Any]:
    workspace_path = pathlib.Path(state["workspace_path"])
    note_paths = sorted(workspace_path.glob("*.md"))
    excerpts = {}
    checklist_mentions = 0
    evidence_mentions = 0
    source_hashes = {}

    for path in note_paths:
        text = read_text(path)
        excerpts[path.name] = text
        checklist_mentions += text.lower().count("checklist")
        evidence_mentions += text.lower().count("evidence")
        source_hashes[path.name] = sha256_file(path)

    deterministic_artifacts = {
        "note_count": len(note_paths),
        "checklist_mentions": checklist_mentions,
        "evidence_mentions": evidence_mentions,
        "source_hashes": source_hashes,
        "expected_digest_path": DIGEST_PATH,
    }

    return {
        "context": {
            "Scenario": "Synthesize research notes in a temporary non-code workspace.",
            **excerpts,
            "Required Digest": (
                f"Create `{DIGEST_PATH}` with `Observations`, `Recommendations`, "
                "and `Traceability` sections."
            ),
        },
        "files": [
            {"path": path.name, "description": "Research note used as source material."}
            for path in note_paths
        ],
        "artifacts": deterministic_artifacts,
        "metadata": deterministic_artifacts,
        "acceptance_criteria": [
            f"Create `{DIGEST_PATH}`.",
            "Include the exact line `note_count=3`.",
            "Include the exact line `checklist_mentions=1`.",
            "Include the exact line `evidence_mentions=1`.",
            "Do not modify source notes.",
        ],
    }


def validate_digest(
    state: typing.MutableMapping[str, typing.Any],
) -> validation_utils.ValidationResult:
    workspace_path = pathlib.Path(state["workspace_path"])
    metadata = dict(state.get("metadata", {}) or {})
    digest_path = workspace_path / DIGEST_PATH

    if not digest_path.exists():
        return validation_utils.failing_validation(
            message=f"Expected Codex to create {DIGEST_PATH}.",
            details={"missing": DIGEST_PATH},
        )
    for filename, expected_hash in metadata["source_hashes"].items():
        if sha256_file(workspace_path / filename) != expected_hash:
            return validation_utils.failing_validation(
                message=f"Codex modified source note {filename}.",
                details={"filename": filename},
            )

    digest_text = read_text(digest_path)
    required_fragments = ["note_count=3", "checklist_mentions=1", "evidence_mentions=1"]
    missing_fragments = [fragment for fragment in required_fragments if fragment not in digest_text]
    if missing_fragments:
        return validation_utils.failing_validation(
            message=f"{DIGEST_PATH} is missing deterministic traceability facts.",
            details={"missing_fragments": missing_fragments},
        )

    return validation_utils.passing_validation(
        message=f"{DIGEST_PATH} exists and source notes are unchanged."
    )


def main() -> None:
    codex_runtime.ensure_codex_authorized()
    codex_runtime.print_authorization_status()
    with tempfile.TemporaryDirectory(prefix="langgraph-codex-research-") as temporary_directory:
        workspace_path = pathlib.Path(temporary_directory)
        write_research_notes(workspace_path)

        codex_runtime.print_section("Scenario", "Real CodexExecutor research digest.")
        codex_runtime.print_section("Temporary Workspace", workspace_path)
        print_workspace_files(workspace_path)

        executor = codex_runtime.create_codex_executor()
        graph = langgraph_codex.graph.build_execution_graph(
            executor=executor,
            validators=[validate_digest],
            context_builder=build_research_context,
        )
        result = graph.invoke(
            {
                "workspace_path": workspace_path,
                "task_title": "Synthesize research notes",
                "objective": (
                    f"Read the Markdown source notes and create `{DIGEST_PATH}` as a "
                    "traceable planning digest."
                ),
                "constraints": [
                    "Do not invent participants, metrics, or findings.",
                    "Do not modify source notes.",
                    "Keep observations separate from recommendations.",
                ],
                "execution_options": {"timeout_seconds": 300},
            }
        )

        execution_result = result["execution_result"]
        codex_runtime.print_section("Deterministic Artifacts", format_json(result["artifacts"]))
        codex_runtime.print_section("Rendered Prompt", result["rendered_prompt"])
        codex_runtime.print_section("Review Result", format_json(result["review_result"]))
        codex_runtime.print_section("Execution Return Code", execution_result.returncode)
        codex_runtime.print_section("Execution Stdout", execution_result.stdout or "(empty)")
        codex_runtime.print_section("Execution Stderr", execution_result.stderr or "(empty)")
        print_workspace_files(workspace_path)


if __name__ == "__main__":
    main()
