import dataclasses
import pathlib
import typing

import langgraph_codex.backends.base as backend_base
import langgraph_codex.backends.fake as fake_backend
import langgraph_codex.defaults as defaults
import langgraph_codex.graph.state as graph_state
import langgraph_codex.utils.prompts as prompt_utils
import langgraph_codex.utils.validation as validation_utils
import langgraph_codex.utils.workspace as workspace_utils

StateUpdate = dict[str, typing.Any]
ContextBuilder = typing.Callable[[graph_state.WorkflowState], StateUpdate]


def build_context(state: graph_state.WorkflowState) -> StateUpdate:
    workspace_path = workspace_utils.resolve_workspace_path(state.get("workspace_path"))
    return {
        "workspace_path": workspace_path,
        "metadata": dict(state.get("metadata", {}) or {}),
        "artifacts": dict(state.get("artifacts", {}) or {}),
        "retry_count": int(state.get("retry_count", 0) or 0),
        "max_retries": int(
            state.get("max_retries", defaults.DEFAULT_MAX_RETRIES) or defaults.DEFAULT_MAX_RETRIES
        ),
    }


def render_prompt(state: graph_state.WorkflowState) -> StateUpdate:
    prompt_spec = prompt_utils.prompt_spec_from_state(state)
    return {"rendered_prompt": prompt_utils.render_prompt(prompt_spec)}


def retry_node(state: graph_state.WorkflowState) -> StateUpdate:
    retry_count = int(state.get("retry_count", 0) or 0)
    return {"retry_count": retry_count + 1}


def route_after_review(state: graph_state.WorkflowState) -> str:
    validation_result = state.get("validation_result")
    if validation_result is not None and validation_result.passed:
        return "success"

    retry_count = int(state.get("retry_count", 0) or 0)
    max_retries = int(state.get("max_retries", 0) or 0)
    if retry_count < max_retries:
        return "retry"

    return "fail"


def create_build_context_node(context_builder: ContextBuilder | None = None) -> ContextBuilder:
    def node(state: graph_state.WorkflowState) -> StateUpdate:
        update = build_context(state)
        if context_builder is not None:
            merged_state = dict(state)
            merged_state.update(update)
            builder_state = typing.cast(graph_state.WorkflowState, merged_state)
            custom_update = context_builder(builder_state)
            update.update(custom_update)

        return update

    return node


def create_render_prompt_node() -> ContextBuilder:
    def node(state: graph_state.WorkflowState) -> StateUpdate:
        return render_prompt(state)

    return node


def create_backend_node(
    backend: backend_base.ExecutionBackend | None = None,
) -> ContextBuilder:
    selected_backend = backend or fake_backend.FakeBackend()

    def node(state: graph_state.WorkflowState) -> StateUpdate:
        workspace_path = workspace_utils.resolve_workspace_path(state.get("workspace_path"))
        request = backend_base.BackendRequest(
            workspace_path=workspace_path,
            prompt=str(state.get("rendered_prompt", "") or ""),
            metadata=dict(state.get("metadata", {}) or {}),
            options=dict(state.get("backend_options", {}) or {}),
        )
        result = selected_backend.execute(request)
        return {"backend_result": result}

    return node


def create_review_node(
    validators: list[validation_utils.Validator] | None = None,
) -> ContextBuilder:
    def node(state: graph_state.WorkflowState) -> StateUpdate:
        backend_result = state.get("backend_result")
        if backend_result is not None and backend_result.returncode != 0:
            validation_result = validation_utils.ValidationResult(
                passed=False,
                message=f"Backend failed with return code {backend_result.returncode}.",
                details={
                    "stdout": backend_result.stdout,
                    "stderr": backend_result.stderr,
                    "returncode": backend_result.returncode,
                },
            )
        else:
            mutable_state = typing.cast(typing.MutableMapping[str, typing.Any], dict(state))
            validation_result = validation_utils.run_validators(
                state=mutable_state,
                validators=validators,
            )

        return {
            "validation_result": validation_result,
            "review_result": {
                "passed": validation_result.passed,
                "message": validation_result.message,
                "details": validation_result.details,
            },
        }

    return node


def serialize_state_value(value: typing.Any) -> typing.Any:
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        dataclass_value = typing.cast(typing.Any, value)
        return dataclasses.asdict(dataclass_value)
    if isinstance(value, pathlib.Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): serialize_state_value(value[key]) for key in value}
    if isinstance(value, list):
        return [serialize_state_value(item) for item in value]

    return value
