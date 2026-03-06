"""Apply SQL to database (stub; integrate with existing auth/apply modules later)."""

from pathlib import Path
from typing import Callable, List, Optional, Union

from pydantic import BaseModel

from pg_db2_git_sync.api.sql_loader import SqlFile, read_sql_from_folder


class DbConfig(BaseModel):
    """Database connection config (placeholder for existing auth modules)."""

    host: str = ""
    port: int = 0
    user: str = ""
    database: str = ""
    # MFA / token handled by mfa_callback


class ApplyResult(BaseModel):
    """Result of apply_to_database."""

    success: bool
    message: str
    applied_count: int = 0
    errors: List[str] = []


def apply_to_database(
    connection_config: DbConfig,
    sql_folder_or_files: Union[Path, List[SqlFile]],
    mfa_callback: Optional[Callable[[], str]] = None,
) -> ApplyResult:
    """
    Apply SQL to database in order (01_schema → 02_table → …).
    MFA via mfa_callback (e.g. return token).
    Stub: actual execution to be implemented with existing auth/apply modules.
    """
    if isinstance(sql_folder_or_files, Path):
        files = read_sql_from_folder(sql_folder_or_files)
    else:
        files = sorted(sql_folder_or_files, key=lambda f: (f.order, f.name))

    # Stub: no real DB connection yet
    return ApplyResult(
        success=False,
        message="apply_to_database is a stub; integrate with existing DB auth/apply modules to execute SQL.",
        applied_count=0,
        errors=["Not implemented"],
    )
