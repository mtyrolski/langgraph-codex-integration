import langgraph_codex.utils.prompts


def test_render_prompt_omits_empty_sections_and_uses_stable_order() -> None:
    spec = langgraph_codex.utils.prompts.PromptSpec(
        title="Analyze dataset",
        objective="Produce a concise summary.",
        context_sections=[
            langgraph_codex.utils.prompts.PromptSection(
                title="Source",
                body="Synthetic benchmark data.",
            )
        ],
        constraints=["Do not assume a software repository.", ""],
        acceptance_criteria=["Summary references inputs."],
        files=[
            langgraph_codex.utils.prompts.PromptFile(
                path="data/input.csv",
                description="Primary data file.",
            )
        ],
        resources=["https://example.invalid/spec"],
        artifacts={"zeta": "last", "alpha": "first", "empty": ""},
        additional_instructions=["Return Markdown."],
    )

    rendered_prompt = langgraph_codex.utils.prompts.render_prompt(spec)

    assert rendered_prompt == (
        "# Analyze dataset\n\n"
        "## Objective\n\n"
        "Produce a concise summary.\n\n"
        "## Context\n\n"
        "### Source\n\n"
        "Synthetic benchmark data.\n\n"
        "## Constraints\n\n"
        "- Do not assume a software repository.\n\n"
        "## Acceptance Criteria\n\n"
        "- Summary references inputs.\n\n"
        "## Files\n\n"
        "- `data/input.csv`: Primary data file.\n\n"
        "## Resources\n\n"
        "- https://example.invalid/spec\n\n"
        "## Artifacts\n\n"
        "- `alpha`: first\n"
        "- `zeta`: last\n\n"
        "## Additional Instructions\n\n"
        "- Return Markdown."
    )
    assert "empty" not in rendered_prompt


def test_prompt_spec_from_state_coerces_structured_state() -> None:
    spec = langgraph_codex.utils.prompts.prompt_spec_from_state(
        {
            "task_title": "Title",
            "objective": "Objective",
            "context": {"B": "second", "A": "first"},
            "constraints": "one constraint",
            "files": [{"path": "notes.md", "description": "Notes"}],
        }
    )

    assert [section.title for section in spec.context_sections] == ["A", "B"]
    assert spec.constraints == ["one constraint"]
    assert spec.files[0].path == "notes.md"
