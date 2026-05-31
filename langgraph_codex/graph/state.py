import pathlib
import typing

import langgraph_codex.backends.base as backend_base
import langgraph_codex.utils.validation as validation_utils


class WorkflowState(typing.TypedDict, total=False):
    workspace_path: str | pathlib.Path
    task_title: str
    objective: str
    context: typing.Any
    constraints: list[str]
    acceptance_criteria: list[str]
    files: list[typing.Any]
    resources: list[str]
    artifacts: dict[str, typing.Any]
    metadata: dict[str, typing.Any]
    backend_options: dict[str, typing.Any]
    rendered_prompt: str
    backend_result: backend_base.BackendResult
    validation_result: validation_utils.ValidationResult
    review_result: dict[str, typing.Any]
    retry_count: int
    max_retries: int
    additional_instructions: list[str]
