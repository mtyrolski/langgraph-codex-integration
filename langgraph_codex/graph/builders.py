import typing

import langgraph.graph

import langgraph_codex.backends.base as backend_base
import langgraph_codex.graph.nodes as graph_nodes
import langgraph_codex.graph.state as graph_state
import langgraph_codex.utils.validation as validation_utils

CompiledGraph = typing.Any


def build_context_only_graph(
    context_builder: graph_nodes.ContextBuilder | None = None,
) -> CompiledGraph:
    graph: typing.Any = langgraph.graph.StateGraph(graph_state.WorkflowState)
    _add_node(graph, "build_context", graph_nodes.create_build_context_node(context_builder))
    _add_node(graph, "render_prompt", graph_nodes.create_render_prompt_node())
    graph.add_edge(langgraph.graph.START, "build_context")
    graph.add_edge("build_context", "render_prompt")
    graph.add_edge("render_prompt", langgraph.graph.END)
    return graph.compile()


def build_basic_backend_graph(
    backend: backend_base.ExecutionBackend | None = None,
    validators: list[validation_utils.Validator] | None = None,
    context_builder: graph_nodes.ContextBuilder | None = None,
) -> CompiledGraph:
    graph: typing.Any = langgraph.graph.StateGraph(graph_state.WorkflowState)
    _add_node(graph, "build_context", graph_nodes.create_build_context_node(context_builder))
    _add_node(graph, "render_prompt", graph_nodes.create_render_prompt_node())
    _add_node(graph, "backend", graph_nodes.create_backend_node(backend))
    _add_node(graph, "review", graph_nodes.create_review_node(validators))
    graph.add_edge(langgraph.graph.START, "build_context")
    graph.add_edge("build_context", "render_prompt")
    graph.add_edge("render_prompt", "backend")
    graph.add_edge("backend", "review")
    graph.add_edge("review", langgraph.graph.END)
    return graph.compile()


def build_retry_graph(
    backend: backend_base.ExecutionBackend | None = None,
    validators: list[validation_utils.Validator] | None = None,
    context_builder: graph_nodes.ContextBuilder | None = None,
) -> CompiledGraph:
    graph: typing.Any = langgraph.graph.StateGraph(graph_state.WorkflowState)
    _add_node(graph, "build_context", graph_nodes.create_build_context_node(context_builder))
    _add_node(graph, "render_prompt", graph_nodes.create_render_prompt_node())
    _add_node(graph, "backend", graph_nodes.create_backend_node(backend))
    _add_node(graph, "review", graph_nodes.create_review_node(validators))
    _add_node(graph, "retry_node", graph_nodes.retry_node)
    graph.add_edge(langgraph.graph.START, "build_context")
    graph.add_edge("build_context", "render_prompt")
    graph.add_edge("render_prompt", "backend")
    graph.add_edge("backend", "review")
    graph.add_conditional_edges(
        "review",
        graph_nodes.route_after_review,
        {
            "success": langgraph.graph.END,
            "retry": "retry_node",
            "fail": langgraph.graph.END,
        },
    )
    graph.add_edge("retry_node", "render_prompt")
    return graph.compile()


def _add_node(
    graph: typing.Any,
    name: str,
    node: graph_nodes.ContextBuilder,
) -> None:
    graph.add_node(name, typing.cast(typing.Any, node))
