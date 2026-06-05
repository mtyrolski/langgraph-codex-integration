import pathlib


def resolve_workspace_path(workspace_path: str | pathlib.Path | None) -> pathlib.Path:
    """Resolve a workspace path, using the current directory when none is provided."""
    if workspace_path is None:
        return pathlib.Path.cwd()

    return pathlib.Path(workspace_path).expanduser().resolve()


def validate_workspace_path(workspace_path: str | pathlib.Path) -> pathlib.Path:
    """Resolve a workspace path and fail unless it is an existing directory."""
    resolved_path = resolve_workspace_path(workspace_path)
    if not resolved_path.exists():
        raise FileNotFoundError(f"Workspace path does not exist: {resolved_path}")
    if not resolved_path.is_dir():
        raise NotADirectoryError(f"Workspace path is not a directory: {resolved_path}")

    return resolved_path
