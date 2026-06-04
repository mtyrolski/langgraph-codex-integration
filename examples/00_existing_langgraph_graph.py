import pathlib
import typing

import langgraph.graph

from langgraph_codex.execution import FakeExecutor
from langgraph_codex.graph import create_codex_node


class SupportState(typing.TypedDict, total=False):
    workspace_path: pathlib.Path
    ticket: str
    deterministic_summary: str
    codex_result: object
    customer_reply: str


def load_ticket(_state: SupportState) -> dict[str, str]:
    return {
        "ticket": (
            "Enterprise customer reports that exported billing reports omit purchase order "
            "references for several invoices."
        )
    }


def summarize_ticket(state: SupportState) -> dict[str, str]:
    ticket = str(state.get("ticket", ""))
    keywords = [
        keyword
        for keyword in ["enterprise", "billing", "purchase order", "invoice"]
        if keyword in ticket.lower()
    ]
    return {"deterministic_summary": f"keywords={', '.join(keywords)}"}


def build_prompt(state: SupportState) -> str:
    ticket = str(state.get("ticket", ""))
    deterministic_summary = str(state.get("deterministic_summary", ""))
    return "\n".join(
        [
            "Draft a concise internal support response.",
            f"Ticket: {ticket}",
            f"Deterministic summary: {deterministic_summary}",
            "Include priority, affected area, and next action.",
        ]
    )


def finalize_reply(state: SupportState) -> dict[str, str]:
    codex_result = typing.cast(typing.Any, state.get("codex_result"))
    return {"customer_reply": str(codex_result.stdout)}


def build_graph() -> typing.Any:
    executor = FakeExecutor(
        stdout=(
            "Priority: medium\n"
            "Area: billing exports\n"
            "Next action: inspect export field mapping for purchase order references."
        )
    )
    graph: typing.Any = langgraph.graph.StateGraph(SupportState)
    graph.add_node("load_ticket", load_ticket)
    graph.add_node("summarize_ticket", summarize_ticket)
    graph.add_node(
        "draft_reply",
        create_codex_node(
            executor=executor,
            prompt_builder=build_prompt,
            workspace_path=lambda state: typing.cast(pathlib.Path, state.get("workspace_path")),
        ),
    )
    graph.add_node("finalize_reply", finalize_reply)
    graph.add_edge(langgraph.graph.START, "load_ticket")
    graph.add_edge("load_ticket", "summarize_ticket")
    graph.add_edge("summarize_ticket", "draft_reply")
    graph.add_edge("draft_reply", "finalize_reply")
    graph.add_edge("finalize_reply", langgraph.graph.END)
    return graph.compile()


def main() -> None:
    result = build_graph().invoke({"workspace_path": pathlib.Path.cwd()})
    print(result["customer_reply"])


if __name__ == "__main__":
    main()
