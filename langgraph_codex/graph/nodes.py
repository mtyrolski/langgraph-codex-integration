import dataclasses
import pathlib
import typing

import langgraph_codex.defaults as defaults
import langgraph_codex.execution.base as execution_base
import langgraph_codex.execution.fake as fake_execution
import langgraph_codex.graph.state as graph_state
import langgraph_codex.utils.prompts as prompt_utils
import langgraph_codex.utils.validation as validation_utils
import langgraph_codex.utils.workspace as workspace_utils

StateUpdate = dict[str, typing.Any]
ContextBuilder = typing.Callable[[graph_state.WorkflowState], StateUpdate]
StateMapping = typing.Mapping[str, typing.Any]
PromptBuilder = typing.Callable[[typing.Any], str]
WorkspacePathBuilder = typing.Callable[[typing.Any], str | pathlib.Path | None]
MetadataBuilder = typing.Callable[[typing.Any], dict[str, typing.Any]]
OptionsBuilder = typing.Callable[[typing.Any], dict[str, typing.Any]]
ResultMapper = typing.Callable[[execution_base.ExecutionResult], StateUpdate]


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


def create_execution_node(
    executor: execution_base.Executor | None = None,
) -> ContextBuilder:
    selected_executor = executor or fake_execution.FakeExecutor()

    def node(state: graph_state.WorkflowState) -> StateUpdate:
        workspace_path = workspace_utils.resolve_workspace_path(state.get("workspace_path"))
        execution_options = dict(state.get("execution_options", {}) or {})
        if not execution_options:
            execution_options = dict(state.get("backend_options", {}) or {})
        request = execution_base.ExecutionRequest(
            workspace_path=workspace_path,
            prompt=str(state.get("rendered_prompt", "") or ""),
            metadata=dict(state.get("metadata", {}) or {}),
            options=execution_options,
        )
        result = selected_executor.execute(request)
        return {"execution_result": result, "backend_result": result}

    return node


def create_backend_node(
    backend: execution_base.Executor | None = None,
) -> ContextBuilder:
    return create_execution_node(backend)


def create_codex_node(  # pylint: disable=too-many-arguments
    executor: execution_base.Executor,
    *,
    prompt_builder: PromptBuilder,
    workspace_path: str | pathlib.Path | WorkspacePathBuilder | None = None,
    result_key: str = "codex_result",
    metadata_builder: MetadataBuilder | None = None,
    options_builder: OptionsBuilder | None = None,
    result_mapper: ResultMapper | None = None,
) -> typing.Callable[[StateMapping], StateUpdate]:
    def node(state: StateMapping) -> StateUpdate:
        request = execution_base.ExecutionRequest(
            workspace_path=_resolve_node_workspace_path(state, workspace_path),
            prompt=prompt_builder(state),
            metadata=_build_node_mapping(state, metadata_builder),
            options=_build_node_mapping(state, options_builder),
        )
        result = executor.execute(request)
        if result_mapper is not None:
            return result_mapper(result)

        return {result_key: result}

    return node


def create_review_node(
    validators: list[validation_utils.Validator] | None = None,
) -> ContextBuilder:
    def node(state: graph_state.WorkflowState) -> StateUpdate:
        execution_result = state.get("execution_result") or state.get("backend_result")
        if execution_result is not None and execution_result.returncode != 0:
            validation_result = validation_utils.ValidationResult(
                passed=False,
                message=f"Execution failed with return code {execution_result.returncode}.",
                details={
                    "stdout": execution_result.stdout,
                    "stderr": execution_result.stderr,
                    "returncode": execution_result.returncode,
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


def _resolve_node_workspace_path(
    state: StateMapping,
    workspace_path: str | pathlib.Path | WorkspacePathBuilder | None,
) -> pathlib.Path:
    if callable(workspace_path):
        return workspace_utils.resolve_workspace_path(workspace_path(state))
    if workspace_path is not None:
        return workspace_utils.resolve_workspace_path(workspace_path)

    return workspace_utils.resolve_workspace_path(state.get("workspace_path"))


def _build_node_mapping(
    state: StateMapping,
    builder: MetadataBuilder | OptionsBuilder | None,
) -> dict[str, typing.Any]:
    if builder is None:
        return {}

    return dict(builder(state))
