"""Public API: discover, read SQL, sync to Git, validate, apply to DB."""

from pg_db2_git_sync.api.discover import (
    DeployTarget,
    discover_server_folders,
    list_databases,
    list_deploy_targets,
    list_deploy_targets_from_remote,
    list_environments,
)
from pg_db2_git_sync.api.sql_loader import read_sql_from_folder, SqlFile
from pg_db2_git_sync.api.git_ops import sync_to_git, validate_before_push, SyncResult
from pg_db2_git_sync.api.db_apply import (
    apply_to_database,
    deploy_to_destination,
    ApplyResult,
    DeployError,
    DbConfig,
)

__all__ = [
    "DeployTarget",
    "discover_server_folders",
    "list_environments",
    "list_databases",
    "list_deploy_targets",
    "list_deploy_targets_from_remote",
    "read_sql_from_folder",
    "sync_to_git",
    "validate_before_push",
    "SyncResult",
    "apply_to_database",
    "deploy_to_destination",
    "ApplyResult",
    "DeployError",
    "DbConfig",
]
