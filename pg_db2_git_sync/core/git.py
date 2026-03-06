"""Git operations: add, commit, status using GitPython."""

from pathlib import Path
from typing import List, Optional

import git
from git.repo.base import Repo

from pg_db2_git_sync.exceptions import GitOperationError, RepoNotFoundError


def get_repo(repo_path: Path) -> Repo:
    """Return GitPython Repo; raise if not a valid repo."""
    repo_path = Path(repo_path).resolve()
    if not (repo_path / ".git").exists():
        raise RepoNotFoundError(f"Not a Git repository: {repo_path}")
    try:
        return Repo(repo_path)
    except Exception as e:
        raise GitOperationError(f"Failed to open repo: {e}") from e


def git_status(repo_path: Path) -> dict:
    """Return status summary: staged, unstaged, untracked (list of paths)."""
    repo = get_repo(repo_path)
    try:
        status = repo.git.status("--porcelain")
    except Exception as e:
        raise GitOperationError(f"git status failed: {e}") from e
    staged: List[str] = []
    unstaged: List[str] = []
    untracked: List[str] = []
    for line in status.splitlines():
        if not line.strip():
            continue
        code = line[:2]
        path = line[3:].strip().split(None, 1)[0] if len(line) > 3 else ""
        if code[0] in ("A", "M", "D", "R", "C"):
            staged.append(path)
        if code[1] in ("M", "D", "?"):
            if code[1] == "?":
                untracked.append(path)
            else:
                unstaged.append(path)
    return {"staged": staged, "unstaged": unstaged, "untracked": untracked, "raw": status}


def git_add_commit(
    repo_path: Path,
    paths: Optional[List[Path]] = None,
    message: str = "Update DDL",
    add_all_under: Optional[Path] = None,
) -> str:
    """
    Add paths (or all under add_all_under) and commit.
    Returns commit hash.
    """
    repo = get_repo(repo_path)
    if paths:
        for p in paths:
            path_str = str(Path(p).resolve())
            if not path_str.startswith(str(repo_path.resolve())):
                path_str = str(repo_path / p) if not str(p).startswith("/") else p
            try:
                repo.index.add(path_str)
            except Exception as e:
                raise GitOperationError(f"git add failed: {e}") from e
    elif add_all_under is not None:
        under = Path(add_all_under).resolve()
        repo_root = Path(repo.working_dir).resolve()
        if not str(under).startswith(str(repo_root)):
            raise GitOperationError("add_all_under must be inside repo")
        try:
            repo.index.add(str(under) + "/")
        except Exception as e:
            raise GitOperationError(f"git add failed: {e}") from e
    else:
        try:
            repo.index.add("*")
        except Exception as e:
            raise GitOperationError(f"git add failed: {e}") from e

    try:
        commit = repo.index.commit(message)
        return str(commit.hexsha)
    except Exception as e:
        raise GitOperationError(f"git commit failed: {e}") from e
