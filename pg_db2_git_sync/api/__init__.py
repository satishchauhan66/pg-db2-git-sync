"""Public API: discover, read SQL, sync to Git, validate, apply to DB."""

from pg_db2_git_sync.api.discover import discover_server_folders
from pg_db2_git_sync.api.sql_loader import read_sql_from_folder, SqlFile
from pg_db2_git_sync.api.git_ops import sync_to_git, validate_before_push, SyncResult
from pg_db2_git_sync.api.db_apply import apply_to_database, ApplyResult

__all__ = [
    "discover_server_folders",
    "read_sql_from_folder",
    "SqlFile",
    "sync_to_git",
    "validate_before_push",
    "SyncResult",
    "apply_to_database",
    "ApplyResult",
]
