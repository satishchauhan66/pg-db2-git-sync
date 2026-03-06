"""
pg-db2-git-sync: Sync SQL DDL to Git (target_ddl) and apply to databases.
"""

from pathlib import Path
from typing import List, Optional

from pg_db2_git_sync.api import (
    discover_server_folders,
    read_sql_from_folder,
    sync_to_git,
    validate_before_push,
    apply_to_database,
    SqlFile,
    SyncResult,
    ApplyResult,
)
from pg_db2_git_sync.api.db_apply import DbConfig
from pg_db2_git_sync.core.repo import ServerFolderInfo
from pg_db2_git_sync.core.validation import ValidationResult

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "discover_server_folders",
    "read_sql_from_folder",
    "sync_to_git",
    "validate_before_push",
    "apply_to_database",
    "SqlFile",
    "SyncResult",
    "ApplyResult",
    "DbConfig",
    "ServerFolderInfo",
    "ValidationResult",
]
