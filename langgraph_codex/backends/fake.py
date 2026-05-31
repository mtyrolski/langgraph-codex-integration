import dataclasses
import typing

import langgraph_codex.backends.base as backend_base

FakeResponder = typing.Callable[
    [backend_base.BackendRequest],
    backend_base.BackendResult,
]


@dataclasses.dataclass
class FakeBackend(backend_base.ExecutionBackend):
    stdout: str = "Fake backend completed."
    stderr: str = ""
    returncode: int = 0
    structured_outputs: dict[str, typing.Any] = dataclasses.field(default_factory=dict)
    response: typing.Any = None
    responder: FakeResponder | None = None
    requests: list[backend_base.BackendRequest] = dataclasses.field(default_factory=list)

    def execute(
        self,
        request: backend_base.BackendRequest,
    ) -> backend_base.BackendResult:
        self.requests.append(request)
        if self.responder is not None:
            return self.responder(request)

        return backend_base.BackendResult(
            stdout=self.stdout,
            stderr=self.stderr,
            returncode=self.returncode,
            structured_outputs=dict(self.structured_outputs),
            backend_response=self.response,
        )
