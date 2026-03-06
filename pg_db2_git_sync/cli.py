"""CLI entrypoint for pg-db2-git-sync. Repo path is dynamic: use --repo-path or set PG_DB2_GIT_SYNC_REPO_PATH."""

from pathlib import Path
from typing import Optional

import typer

from pg_db2_git_sync import (
    discover_server_folders,
    read_sql_from_folder,
    sync_to_git,
    validate_before_push,
    __version__,
)
from pg_db2_git_sync.config import get_config, resolve_repo_path

app = typer.Typer(
    name="pg-db2-git-sync",
    help="Sync SQL DDL to Git (target_ddl) and apply to databases.",
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit(0)


@app.callback()
def main(
    version: bool = typer.Option(None, "--version", "-v", callback=_version_callback, is_eager=True),
) -> None:
    pass


@app.command()
def discover(
    repo_path: Optional[Path] = typer.Argument(None, help="Path to Git repo (optional if PG_DB2_GIT_SYNC_REPO_PATH is set)"),
    env: Optional[str] = typer.Option(None, "--env", "-e", help="Environment: non_prod or prod"),
    db_name: Optional[str] = typer.Option(None, "--db-name", "-d", help="Filter by database name (e.g. D_ACO)"),
) -> None:
    """List server folders under target_ddl/<env>/<db_name>/."""
    resolved = resolve_repo_path(repo_path)
    if resolved is None:
        typer.echo("Error: Set repo path via argument or PG_DB2_GIT_SYNC_REPO_PATH (env/.env)", err=True)
        raise typer.Exit(1)
    repo_path = resolved
    env = env or get_config().default_env
    if not repo_path.is_dir():
        typer.echo(f"Error: Not a directory: {repo_path}", err=True)
        raise typer.Exit(1)
    folders = discover_server_folders(repo_path, env=env, db_name=db_name)
    if not folders:
        typer.echo(f"No server folders found under target_ddl/{env}/" + (f"{db_name}/" if db_name else ""))
        return
    for f in folders:
        typer.echo(f"  {f.path}  [db={f.db_name} server={f.server_folder}]")


@app.command()
def sync(
    server_folder: Path = typer.Argument(..., help="Path to server folder inside repo (e.g. target_ddl/non_prod/D_ACO/SS_SLD_DB22U)"),
    repo_path: Optional[Path] = typer.Option(None, "--repo-path", "-r", help="Path to Git repo (optional if PG_DB2_GIT_SYNC_REPO_PATH is set)"),
    source_folder: Optional[Path] = typer.Option(None, "--source-folder", "-s", help="Local folder to copy from before commit"),
    message: str = typer.Option("Update DDL", "--message", "-m", help="Commit message"),
    no_validate: bool = typer.Option(False, "--no-validate", help="Skip validation before commit"),
) -> None:
    """Sync files into repo server folder and commit. Optionally copy from --source-folder first."""
    resolved = resolve_repo_path(repo_path)
    if resolved is None:
        typer.echo("Error: Set repo path via --repo-path or PG_DB2_GIT_SYNC_REPO_PATH (env/.env)", err=True)
        raise typer.Exit(1)
    repo_path = resolved
    server_folder_path = Path(server_folder)
    if not server_folder_path.is_absolute():
        server_folder_path = (repo_path / server_folder_path).resolve()
    result = sync_to_git(
        repo_path=repo_path,
        server_folder_path=server_folder_path,
        source_folder=Path(source_folder) if source_folder else None,
        message=message,
        validate=not no_validate,
    )
    if result.success:
        typer.echo(f"Committed: {result.commit_sha}")
    else:
        typer.echo(f"Error: {result.message}", err=True)
        raise typer.Exit(1)


@app.command()
def validate(
    repo_path: Optional[Path] = typer.Argument(None, help="Path to Git repo (optional if PG_DB2_GIT_SYNC_REPO_PATH is set)"),
    allow_dirty: bool = typer.Option(False, "--allow-dirty", help="Consider valid even with unstaged/untracked changes"),
) -> None:
    """Validate repo state before push (e.g. clean working tree)."""
    resolved = resolve_repo_path(repo_path)
    if resolved is None:
        typer.echo("Error: Set repo path via argument or PG_DB2_GIT_SYNC_REPO_PATH (env/.env)", err=True)
        raise typer.Exit(1)
    repo_path = resolved
    res = validate_before_push(
        repo_path,
        require_clean_working_tree=not allow_dirty,
        allow_staged=True,
    )
    if res.valid:
        typer.echo("OK")
    else:
        typer.echo(res.message, err=True)
        if res.unstaged:
            typer.echo("Unstaged: " + ", ".join(res.unstaged[:10]), err=True)
        if res.untracked:
            typer.echo("Untracked: " + ", ".join(res.untracked[:10]), err=True)
        raise typer.Exit(1)


@app.command()
def read_sql(
    folder_path: Path = typer.Argument(..., help="Path to server folder (or relative to repo if PG_DB2_GIT_SYNC_REPO_PATH set)"),
) -> None:
    """List SQL files in folder (ordered by 01_, 02_, ...)."""
    folder_path = Path(folder_path)
    if not folder_path.is_absolute():
        resolved_repo = resolve_repo_path(None)
        if resolved_repo is not None:
            folder_path = (resolved_repo / folder_path).resolve()
    if not folder_path.is_dir():
        typer.echo(f"Error: Not a directory: {folder_path}", err=True)
        raise typer.Exit(1)
    files = read_sql_from_folder(folder_path)
    for f in files:
        typer.echo(f"  {f.order}: {f.name}")
