"""
pg-db2-git-sync: Sync SQL DDL to Git (target_ddl) and apply to databases.
"""

from pathlib import Path
from typing import List, Optional

from pg_db2_git_sync.api import (
    DeployTarget,
    discover_server_folders,
    list_deploy_targets,
    list_deploy_targets_from_remote,
    list_environments,
    list_databases,
    read_sql_from_folder,
    sync_to_git,
    validate_before_push,
    apply_to_database,
    deploy_to_destination,
    SqlFile,
    SyncResult,
    ApplyResult,
    DeployError,
    DbConfig,
)
from pg_db2_git_sync.config import SyncConfig, get_config, resolve_repo_path
from pg_db2_git_sync.core.repo import ServerFolderInfo
from pg_db2_git_sync.core.validation import ValidationResult

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "DeployTarget",
    "discover_server_folders",
    "list_environments",
    "list_databases",
    "list_deploy_targets",
    "list_deploy_targets_from_remote",
    "read_sql_from_folder",
    "sync_to_git",
    "validate_before_push",
    "apply_to_database",
    "deploy_to_destination",
    "SqlFile",
    "SyncResult",
    "ApplyResult",
    "DeployError",
    "DbConfig",
    "ServerFolderInfo",
    "ValidationResult",
    "SyncConfig",
    "get_config",
    "resolve_repo_path",
]
