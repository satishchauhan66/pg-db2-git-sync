"""Git operations: clone, add, commit, status using GitPython."""

from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse, urlunparse

import git
from git.repo.base import Repo

from pg_db2_git_sync.exceptions import GitOperationError, RepoNotFoundError


def _url_with_token(url: str, token: str) -> str:
    """Embed token in URL for HTTPS clone (e.g. https://oauth2:TOKEN@host/path)."""
    parsed = urlparse(url)
    if not parsed.scheme or parsed.scheme not in ("http", "https"):
        return url
    # Use oauth2 as username so token is the password (GitLab/GitHub accept this)
    netloc = parsed.hostname or ""
    if parsed.port:
        netloc += f":{parsed.port}"
    auth = f"oauth2:{token}" if token else ""
    new_netloc = f"{auth}@{netloc}" if auth else netloc
    return urlunparse(parsed._replace(netloc=new_netloc))


def clone_repo(
    url: str,
    token: str,
    branch_name: str,
    target_dir: Path,
) -> Path:
    """
    Clone repo from URL using token, checkout branch_name, return local path.
    target_dir must not exist or be an empty directory; clone is created inside it.
    """
    target_dir = Path(target_dir).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    # GitPython clone_from expects the parent dir to exist; clone creates a dir from repo name.
    # To clone into target_dir directly we use target_dir as the path (clone_from(url, path) puts .git inside path).
    if (target_dir / ".git").exists():
        repo = Repo(target_dir)
        try:
            repo.remotes.origin.fetch()
            repo.git.checkout(branch_name)
        except Exception as e:
            raise GitOperationError(f"Fetch/checkout failed: {e}") from e
        return target_dir
    url_with_token = _url_with_token(url, token)
    try:
        Repo.clone_from(
            url_with_token,
            str(target_dir),
            branch=branch_name,
            single_branch=True,
        )
    except Exception as e:
        raise GitOperationError(f"Clone failed: {e}") from e
    return target_dir


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
