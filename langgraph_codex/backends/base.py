import abc
import dataclasses
import pathlib
import typing


@dataclasses.dataclass
class BackendRequest:
    workspace_path: pathlib.Path
    prompt: str
    metadata: dict[str, typing.Any] = dataclasses.field(default_factory=dict)
    options: dict[str, typing.Any] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass
class BackendResult:
    stdout: str
    stderr: str
    returncode: int
    structured_outputs: dict[str, typing.Any] = dataclasses.field(default_factory=dict)
    backend_response: typing.Any = None

    @property
    def succeeded(self) -> bool:
        return self.returncode == 0


class ExecutionBackend(abc.ABC):
    @abc.abstractmethod
    def execute(self, request: BackendRequest) -> BackendResult:
        raise NotImplementedError
