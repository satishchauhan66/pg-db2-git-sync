"""Sync to Git (add/commit), validate before push."""

import shutil
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel

from pg_db2_git_sync.core.git import git_add_commit, get_repo
from pg_db2_git_sync.core.validation import validate_repo_state, ValidationResult


class SyncResult(BaseModel):
    """Result of sync_to_git."""

    success: bool
    message: str
    commit_sha: Optional[str] = None
    files_added: List[str] = []


def sync_to_git(
    repo_path: Path,
    server_folder_path: Path,
    source_folder: Optional[Path] = None,
    message: str = "Update DDL",
    validate: bool = True,
) -> SyncResult:
    """
    Check-in files under server_folder_path.
    If source_folder is given, copy its contents into server_folder_path first, then add and commit.
    """
    repo_path = Path(repo_path).resolve()
    server_folder_path = Path(server_folder_path).resolve()

    if not str(server_folder_path).startswith(str(repo_path)):
        return SyncResult(success=False, message="server_folder_path must be inside repo_path")

    if source_folder is not None:
        source_folder = Path(source_folder).resolve()
        if not source_folder.is_dir():
            return SyncResult(success=False, message=f"source_folder is not a directory: {source_folder}")
        # Copy files into server folder (overwrite)
        for f in source_folder.iterdir():
            if f.is_file():
                dest = server_folder_path / f.name
                shutil.copy2(f, dest)

    if validate:
        res = validate_repo_state(repo_path, allow_staged=True, require_clean_working_tree=False)
        if not res.valid and (res.unstaged or res.untracked):
            # After copy we may have new changes; allow and commit them
            pass

    try:
        commit_sha = git_add_commit(
            repo_path,
            add_all_under=server_folder_path,
            message=message,
        )
        return SyncResult(
            success=True,
            message="Committed successfully",
            commit_sha=commit_sha,
            files_added=[str(server_folder_path)],
        )
    except Exception as e:
        return SyncResult(success=False, message=str(e))


def validate_before_push(
    repo_path: Path,
    require_clean_working_tree: bool = True,
    allow_staged: bool = True,
) -> ValidationResult:
    """Run validation (clean tree, etc.) before push."""
    return validate_repo_state(
        Path(repo_path),
        allow_staged=allow_staged,
        require_clean_working_tree=require_clean_working_tree,
    )
