"""Repo path handling and server folder discovery under target_ddl/<env>/<db_name>/."""

from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel

from pg_db2_git_sync.exceptions import InvalidPathError, RepoNotFoundError


class ServerFolderInfo(BaseModel):
    """Info for a server folder under target_ddl/<env>/<db_name>/<server_folder>."""

    path: Path
    db_name: str
    server_folder: str
    env: str

    class Config:
        arbitrary_types_allowed = True


def _normalize_server_name(name: str) -> str:
    """Normalize server folder name for comparison (hyphen vs underscore)."""
    return name.replace("-", "_").strip()


def discover_server_folders_impl(
    repo_path: Path,
    env: str,
    db_name: Optional[str] = None,
    target_ddl_base: str = "target_ddl",
) -> List[ServerFolderInfo]:
    """
    List server folders under target_ddl/<env>/<db_name>/.
    Supports both hyphen and underscore naming in folder names.
    """
    repo_path = Path(repo_path).resolve()
    if not repo_path.is_dir():
        raise RepoNotFoundError(f"Repo path is not a directory: {repo_path}")
    if not (repo_path / ".git").exists():
        raise RepoNotFoundError(f"Not a Git repository: {repo_path}")

    base = repo_path / target_ddl_base / env
    if not base.is_dir():
        return []

    result: List[ServerFolderInfo] = []

    if db_name:
        db_dir = base / db_name
        if not db_dir.is_dir():
            return []
        for child in db_dir.iterdir():
            if child.is_dir() and not child.name.startswith("."):
                result.append(
                    ServerFolderInfo(
                        path=child,
                        db_name=db_name,
                        server_folder=child.name,
                        env=env,
                    )
                )
    else:
        for db_dir in base.iterdir():
            if not db_dir.is_dir() or db_dir.name.startswith("."):
                continue
            for child in db_dir.iterdir():
                if child.is_dir() and not child.name.startswith("."):
                    result.append(
                        ServerFolderInfo(
                            path=child,
                            db_name=db_dir.name,
                            server_folder=child.name,
                            env=env,
                        )
                    )

    return result


def resolve_server_folder(
    repo_path: Path,
    env: str,
    db_name: str,
    server_folder_name: str,
    target_ddl_base: str = "target_ddl",
) -> Optional[Path]:
    """
    Resolve server folder by name (handles both hyphen and underscore).
    Returns the first matching directory under target_ddl/<env>/<db_name>/.
    """
    folders = discover_server_folders_impl(repo_path, env, db_name, target_ddl_base)
    normalized = _normalize_server_name(server_folder_name)
    for info in folders:
        if _normalize_server_name(info.server_folder) == normalized:
            return info.path
    return None
