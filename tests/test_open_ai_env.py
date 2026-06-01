import pathlib

import langgraph_codex.utils.open_ai_env as open_ai_env


def test_configure_open_ai_environment_maps_secret_to_openai_api_key(
    tmp_path: pathlib.Path,
) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "OPEN_AI_SECRET_KEY=secret-value",
                "OPEN_AI_KEY_NAME=todoist",
                "OPEN_AI_MODEL=gpt-5.5",
            ]
        ),
        encoding="utf-8",
    )
    environ: dict[str, str] = {}

    environment = open_ai_env.configure_open_ai_environment(env_path=env_path, environ=environ)

    assert environment.authorized is True
    assert environment.key_name == "todoist"
    assert environment.model == "gpt-5.5"
    assert environment.secret_key_present is True
    assert environment.openai_api_key_present is True
    assert environment.env_file_loaded == env_path
    assert environ["OPENAI_API_KEY"] == "secret-value"


def test_configure_open_ai_environment_keeps_existing_openai_api_key(
    tmp_path: pathlib.Path,
) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "OPEN_AI_SECRET_KEY=secret-value",
                "OPEN_AI_KEY_NAME=CUSTOM_OPENAI_KEY",
                "OPEN_AI_MODEL=",
            ]
        ),
        encoding="utf-8",
    )
    environ = {"OPENAI_API_KEY": "existing-value"}

    environment = open_ai_env.configure_open_ai_environment(env_path=env_path, environ=environ)

    assert environment.key_name == "CUSTOM_OPENAI_KEY"
    assert environment.model is None
    assert environ["OPENAI_API_KEY"] == "existing-value"


def test_configure_open_ai_environment_defaults_key_name_without_env_file() -> None:
    environment = open_ai_env.configure_open_ai_environment(environ={})

    assert environment.key_name is None
    assert environment.authorized is False
    assert environment.env_file_loaded is None
