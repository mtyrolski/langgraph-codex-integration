import dataclasses
import pathlib
import subprocess


@dataclasses.dataclass
class CommandResult:
    args: list[str]
    cwd: pathlib.Path
    stdout: str
    stderr: str
    returncode: int
    timed_out: bool = False


def run_command(
    args: list[str],
    cwd: str | pathlib.Path,
    timeout_seconds: int | float | None = None,
    input_text: str | None = None,
) -> CommandResult:
    """Run a command with captured output and convert timeouts into a result object."""
    resolved_cwd = pathlib.Path(cwd).expanduser().resolve()
    try:
        completed = subprocess.run(
            args,
            cwd=resolved_cwd,
            capture_output=True,
            text=True,
            input=input_text,
            timeout=timeout_seconds,
            check=False,
        )
        return CommandResult(
            args=list(args),
            cwd=resolved_cwd,
            stdout=completed.stdout,
            stderr=completed.stderr,
            returncode=completed.returncode,
            timed_out=False,
        )
    except subprocess.TimeoutExpired as timeout_error:
        stdout = timeout_error.stdout if isinstance(timeout_error.stdout, str) else ""
        stderr = timeout_error.stderr if isinstance(timeout_error.stderr, str) else ""
        return CommandResult(
            args=list(args),
            cwd=resolved_cwd,
            stdout=stdout,
            stderr=f"{stderr}\nCommand timed out after {timeout_seconds} seconds.".strip(),
            returncode=124,
            timed_out=True,
        )
