import dataclasses
import pathlib

import langgraph_codex.defaults as defaults
import langgraph_codex.execution.base as execution_base
import langgraph_codex.utils.subprocess as subprocess_utils
import langgraph_codex.utils.workspace as workspace_utils

DANGEROUS_CODEX_FLAGS = {
    "--dangerously-bypass-approvals-and-sandbox",
    "--dangerously-bypass-hook-trust",
}


@dataclasses.dataclass
class CodexExecutor(execution_base.Executor):
    codex_bin: str = defaults.DEFAULT_CODEX_BIN
    model: str | None = defaults.DEFAULT_CODEX_MODEL
    sandbox: str = defaults.DEFAULT_SANDBOX
    approval_policy: str = defaults.DEFAULT_APPROVAL_POLICY
    timeout_seconds: int = defaults.DEFAULT_TIMEOUT_SECONDS
    extra_args: list[str] = dataclasses.field(default_factory=list)
    skip_git_repo_check: bool = True

    def execute(
        self,
        request: execution_base.ExecutionRequest,
    ) -> execution_base.ExecutionResult:
        workspace_path = workspace_utils.validate_workspace_path(request.workspace_path)
        command = self.build_command(workspace_path=workspace_path)
        result = subprocess_utils.run_command(
            command,
            cwd=workspace_path,
            timeout_seconds=self._timeout_from_request(request),
            input_text=request.prompt,
        )
        return execution_base.ExecutionResult(
            stdout=result.stdout,
            stderr=result.stderr,
            returncode=result.returncode,
            structured_outputs={
                "args": result.args,
                "cwd": str(result.cwd),
                "timed_out": result.timed_out,
            },
            raw_response=result,
        )

    def build_command(self, workspace_path: str | pathlib.Path) -> list[str]:
        resolved_workspace_path = pathlib.Path(workspace_path).expanduser().resolve()
        self._validate_args()

        command = [
            self.codex_bin,
            "exec",
            "-s",
            self.sandbox,
            "-C",
            str(resolved_workspace_path),
            "-c",
            f"approval_policy={self.approval_policy!r}",
        ]
        if self.model:
            command[2:2] = ["-m", self.model]
        if self.skip_git_repo_check:
            command.append("--skip-git-repo-check")

        command.extend(self.extra_args)
        command.append("-")
        return command

    def _timeout_from_request(
        self,
        request: execution_base.ExecutionRequest,
    ) -> int | float:
        timeout = request.options.get("timeout_seconds", self.timeout_seconds)
        if not isinstance(timeout, (int, float)):
            raise TypeError(f"timeout_seconds must be int or float, got {type(timeout).__name__}")
        if timeout <= 0:
            raise ValueError(f"timeout_seconds must be positive, got {timeout}")
        return timeout

    def _validate_args(self) -> None:
        if not self.codex_bin:
            raise ValueError("codex_bin must not be empty")
        if not self.sandbox:
            raise ValueError("sandbox must not be empty")
        if not self.approval_policy:
            raise ValueError("approval_policy must not be empty")

        for arg in self.extra_args:
            if _is_dangerous_codex_flag(arg):
                raise ValueError(f"Refusing dangerous Codex flag: {arg}")


CodexBackend = CodexExecutor
CodexExecBackend = CodexExecutor


def _is_dangerous_codex_flag(arg: str) -> bool:
    for dangerous_flag in DANGEROUS_CODEX_FLAGS:
        if arg == dangerous_flag or arg.startswith(f"{dangerous_flag}="):
            return True

    return False
