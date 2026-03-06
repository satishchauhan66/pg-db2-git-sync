"""List environments, databases, and server folders under target_ddl/."""

from pathlib import Path
from typing import List, Optional, Tuple

from pydantic import BaseModel

from pg_db2_git_sync.core.git import clone_repo
from pg_db2_git_sync.core.repo import (
    ServerFolderInfo,
    discover_server_folders_impl,
    list_databases_impl,
    list_environments_impl,
)


class DeployTarget(BaseModel):
    """A single deploy target: env + database + server folder (user selects one to deploy)."""

    env: str
    db_name: str
    server_folder: str
    path: Path  # path to folder containing SQL files

    class Config:
        arbitrary_types_allowed = True


def list_environments(
    repo_path: Path,
    target_ddl_base: str = "target_ddl",
) -> List[str]:
    """List environment names (e.g. non_prod, prod) under target_ddl/."""
    return list_environments_impl(Path(repo_path), target_ddl_base=target_ddl_base)


def list_databases(
    repo_path: Path,
    env: str,
    target_ddl_base: str = "target_ddl",
) -> List[str]:
    """List database names under target_ddl/<env>/."""
    return list_databases_impl(Path(repo_path), env=env, target_ddl_base=target_ddl_base)


def discover_server_folders(
    repo_path: Path,
    env: str,
    db_name: Optional[str] = None,
    target_ddl_base: str = "target_ddl",
) -> List[ServerFolderInfo]:
    """
    List server folders (e.g. SS_SLD_DB22U) under target_ddl/<env>/<db_name>/.
    Handles both hyphen and underscore naming in folder names.
    """
    return discover_server_folders_impl(
        repo_path=Path(repo_path),
        env=env,
        db_name=db_name,
        target_ddl_base=target_ddl_base,
    )


def list_deploy_targets(
    repo_path: Path,
    target_ddl_base: str = "target_ddl",
) -> List[DeployTarget]:
    """
    Connect to Git repo (local path) and list all deploy targets (env, database, server_folder).
    User selects one target to deploy SQL to destination.
    Each target has: env, db_name, server_folder, path (to SQL folder).
    """
    repo_path = Path(repo_path).resolve()
    envs = list_environments_impl(repo_path, target_ddl_base=target_ddl_base)
    result: List[DeployTarget] = []
    for env in envs:
        folders = discover_server_folders_impl(
            repo_path, env=env, db_name=None, target_ddl_base=target_ddl_base
        )
        for f in folders:
            result.append(
                DeployTarget(
                    env=f.env,
                    db_name=f.db_name,
                    server_folder=f.server_folder,
                    path=f.path,
                )
            )
    return result


def list_deploy_targets_from_remote(
    url: str,
    token: str,
    branch_name: str,
    clone_dir: Path,
    target_ddl_base: str = "target_ddl",
) -> Tuple[List[DeployTarget], Path]:
    """
    Connect to Git repo via URL + token, checkout branch_name, list all deploy targets.
    Clones (or fetches) into clone_dir. Returns (targets, clone_path) so you can use
    clone_path for deploy_to_destination().
    """
    clone_dir = Path(clone_dir).resolve()
    repo_path = clone_repo(url=url, token=token, branch_name=branch_name, target_dir=clone_dir)
    targets = list_deploy_targets(repo_path, target_ddl_base=target_ddl_base)
    return (targets, repo_path)
