import dataclasses
import pathlib
import typing


@dataclasses.dataclass
class PromptSection:
    title: str
    body: str


@dataclasses.dataclass
class PromptFile:
    path: str | pathlib.Path
    description: str = ""


@dataclasses.dataclass
class PromptSpec:
    title: str = ""
    objective: str = ""
    context_sections: list[PromptSection] = dataclasses.field(default_factory=list)
    constraints: list[str] = dataclasses.field(default_factory=list)
    acceptance_criteria: list[str] = dataclasses.field(default_factory=list)
    files: list[PromptFile] = dataclasses.field(default_factory=list)
    resources: list[str] = dataclasses.field(default_factory=list)
    artifacts: dict[str, typing.Any] = dataclasses.field(default_factory=dict)
    additional_instructions: list[str] = dataclasses.field(default_factory=list)


def render_prompt(spec: PromptSpec) -> str:
    blocks: list[str] = []

    if spec.title.strip():
        blocks.append(f"# {spec.title.strip()}")

    if spec.objective.strip():
        blocks.append(_render_text_section("Objective", spec.objective))

    context_block = _render_context_sections(spec.context_sections)
    if context_block:
        blocks.append(context_block)

    constraints_block = _render_bullets("Constraints", spec.constraints)
    if constraints_block:
        blocks.append(constraints_block)

    acceptance_block = _render_bullets("Acceptance Criteria", spec.acceptance_criteria)
    if acceptance_block:
        blocks.append(acceptance_block)

    files_block = _render_files(spec.files)
    if files_block:
        blocks.append(files_block)

    resources_block = _render_bullets("Resources", spec.resources)
    if resources_block:
        blocks.append(resources_block)

    artifacts_block = _render_artifacts(spec.artifacts)
    if artifacts_block:
        blocks.append(artifacts_block)

    instructions_block = _render_bullets("Additional Instructions", spec.additional_instructions)
    if instructions_block:
        blocks.append(instructions_block)

    return "\n\n".join(blocks).strip()


def prompt_spec_from_state(state: typing.Mapping[str, typing.Any]) -> PromptSpec:
    return PromptSpec(
        title=str(state.get("task_title", "") or ""),
        objective=str(state.get("objective", "") or ""),
        context_sections=_coerce_context_sections(state.get("context", [])),
        constraints=_coerce_list(state.get("constraints", [])),
        acceptance_criteria=_coerce_list(state.get("acceptance_criteria", [])),
        files=_coerce_files(state.get("files", [])),
        resources=_coerce_list(state.get("resources", [])),
        artifacts=dict(state.get("artifacts", {}) or {}),
        additional_instructions=_coerce_list(state.get("additional_instructions", [])),
    )


def _render_text_section(title: str, body: str) -> str:
    return f"## {title}\n\n{body.strip()}"


def _render_context_sections(sections: list[PromptSection]) -> str:
    rendered_sections: list[str] = []
    for section in sections:
        if section.title.strip() and section.body.strip():
            rendered_sections.append(f"### {section.title.strip()}\n\n{section.body.strip()}")

    if not rendered_sections:
        return ""

    joined_sections = "\n\n".join(rendered_sections)
    return f"## Context\n\n{joined_sections}"


def _render_bullets(title: str, values: list[str]) -> str:
    normalized_values = [value.strip() for value in values if value.strip()]
    if not normalized_values:
        return ""

    bullets = "\n".join([f"- {value}" for value in normalized_values])
    return f"## {title}\n\n{bullets}"


def _render_files(files: list[PromptFile]) -> str:
    rendered_files: list[str] = []
    for prompt_file in files:
        path = str(prompt_file.path).strip()
        description = prompt_file.description.strip()
        if path and description:
            rendered_files.append(f"- `{path}`: {description}")
        elif path:
            rendered_files.append(f"- `{path}`")

    if not rendered_files:
        return ""

    joined_files = "\n".join(rendered_files)
    return f"## Files\n\n{joined_files}"


def _render_artifacts(artifacts: dict[str, typing.Any]) -> str:
    rendered_artifacts: list[str] = []
    for key in sorted(artifacts):
        value = artifacts[key]
        if value is None or value == "":
            continue
        rendered_artifacts.append(f"- `{key}`: {value}")

    if not rendered_artifacts:
        return ""

    joined_artifacts = "\n".join(rendered_artifacts)
    return f"## Artifacts\n\n{joined_artifacts}"


def _coerce_context_sections(value: typing.Any) -> list[PromptSection]:
    if value is None:
        return []
    if isinstance(value, dict):
        return [
            PromptSection(title=str(key), body=str(value[key]))
            for key in sorted(value)
            if value[key] is not None and str(value[key]).strip()
        ]
    if isinstance(value, list):
        sections: list[PromptSection] = []
        for item in value:
            if isinstance(item, PromptSection):
                sections.append(item)
            elif isinstance(item, dict):
                sections.append(
                    PromptSection(
                        title=str(item.get("title", "")),
                        body=str(item.get("body", "")),
                    )
                )
            else:
                sections.append(PromptSection(title="Context", body=str(item)))
        return sections

    return [PromptSection(title="Context", body=str(value))]


def _coerce_files(value: typing.Any) -> list[PromptFile]:
    if value is None:
        return []
    if isinstance(value, list):
        files: list[PromptFile] = []
        for item in value:
            if isinstance(item, PromptFile):
                files.append(item)
            elif isinstance(item, dict):
                files.append(
                    PromptFile(
                        path=str(item.get("path", "")),
                        description=str(item.get("description", "")),
                    )
                )
            else:
                files.append(PromptFile(path=str(item)))
        return files

    return [PromptFile(path=str(value))]


def _coerce_list(value: typing.Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value if item is not None]

    return [str(value)]
