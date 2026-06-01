import abc
import dataclasses
import pathlib
import typing


@dataclasses.dataclass
class ExecutionRequest:
    workspace_path: pathlib.Path
    prompt: str
    metadata: dict[str, typing.Any] = dataclasses.field(default_factory=dict)
    options: dict[str, typing.Any] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass
class ExecutionResult:
    stdout: str
    stderr: str
    returncode: int
    structured_outputs: dict[str, typing.Any] = dataclasses.field(default_factory=dict)
    raw_response: typing.Any = None

    @property
    def succeeded(self) -> bool:
        return self.returncode == 0


class Executor(abc.ABC):
    @abc.abstractmethod
    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        raise NotImplementedError


BackendRequest = ExecutionRequest
BackendResult = ExecutionResult
ExecutionBackend = Executor
