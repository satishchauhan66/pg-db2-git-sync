"""Pre-push validation: clean tree, conflict check."""

from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from pg_db2_git_sync.core.git import get_repo, git_status
from pg_db2_git_sync.exceptions import ValidationError


class ValidationResult(BaseModel):
    """Result of validate_before_push."""

    valid: bool
    message: str
    staged: list = []
    unstaged: list = []
    untracked: list = []
    raw_status: str = ""


def validate_repo_state(
    repo_path: Path,
    allow_staged: bool = True,
    require_clean_working_tree: bool = True,
) -> ValidationResult:
    """
    Validate repo state before push.
    If require_clean_working_tree, fail when there are unstaged or untracked changes.
    """
    status = git_status(repo_path)
    unstaged = status.get("unstaged", [])
    untracked = status.get("untracked", [])
    staged = status.get("staged", [])

    if require_clean_working_tree and (unstaged or untracked):
        return ValidationResult(
            valid=False,
            message="Working tree has unstaged or untracked changes. Commit or stash them before push.",
            staged=staged,
            unstaged=unstaged,
            untracked=untracked,
            raw_status=status.get("raw", ""),
        )
    if not allow_staged and staged:
        return ValidationResult(
            valid=False,
            message="There are staged changes. Commit or unstage before push.",
            staged=staged,
            unstaged=unstaged,
            untracked=untracked,
            raw_status=status.get("raw", ""),
        )
    return ValidationResult(
        valid=True,
        message="OK",
        staged=staged,
        unstaged=unstaged,
        untracked=untracked,
        raw_status=status.get("raw", ""),
    )
