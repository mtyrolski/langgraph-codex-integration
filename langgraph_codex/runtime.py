import pathlib
import shutil

import langgraph_codex.utils.open_ai_env as open_ai_env
from langgraph_codex.execution import CodexExecutor

REPOSITORY_ROOT = pathlib.Path(__file__).resolve().parents[1]
ENV_PATH = REPOSITORY_ROOT / ".env"


def load_local_env() -> open_ai_env.OpenAIEnvironment:
    """Load repository-local Codex/OpenAI settings from .env."""
    return open_ai_env.configure_open_ai_environment(env_path=ENV_PATH)


def ensure_codex_authorized() -> None:
    """Fail fast when the Codex CLI or usable OpenAI credentials are missing."""
    environment = load_local_env()
    has_codex_cli = shutil.which("codex") is not None
    if not has_codex_cli:
        raise RuntimeError("Codex CLI is not available on PATH.")
    if not environment.authorized:
        raise RuntimeError(
            f"Missing {open_ai_env.OPEN_AI_SECRET_KEY} or {open_ai_env.DEFAULT_OPENAI_KEY_NAME}. "
            "Create .env from .env.example or authenticate Codex before running real examples."
        )


def create_codex_executor(timeout_seconds: int = 300) -> CodexExecutor:
    """Create a Codex executor from local environment defaults."""
    environment = load_local_env()
    ensure_codex_authorized()
    if environment.model:
        return CodexExecutor(
            model=environment.model,
            timeout_seconds=timeout_seconds,
        )

    return CodexExecutor(
        model=None,
        timeout_seconds=timeout_seconds,
    )


def print_section(title: str, body: object = "") -> None:
    """Print a readable console section for examples and smoke scripts."""
    print(f"\n{'=' * 80}")
    print(title)
    print(f"{'=' * 80}")
    if body != "":
        print(body)


def print_authorization_status() -> None:
    """Print authorization diagnostics without exposing secret values."""
    environment = load_local_env()
    print_section(
        "Codex Authorization",
        "\n".join(
            [
                f"codex_on_path={shutil.which('codex') is not None}",
                f"{open_ai_env.OPEN_AI_SECRET_KEY}_present={environment.secret_key_present}",
                f"{open_ai_env.OPEN_AI_KEY_NAME}={environment.key_name or '<unset>'}",
                (
                    f"{open_ai_env.DEFAULT_OPENAI_KEY_NAME}_present="
                    f"{environment.openai_api_key_present}"
                ),
                f"{open_ai_env.OPEN_AI_MODEL}_present={bool(environment.model)}",
                "secret_value_printed=False",
            ]
        ),
    )
