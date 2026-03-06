"""Custom exceptions for pg-db2-git-sync."""


class PgDb2GitSyncError(Exception):
    """Base exception for pg-db2-git-sync."""


class RepoNotFoundError(PgDb2GitSyncError):
    """Repository path does not exist or is not a valid Git repo."""


class InvalidPathError(PgDb2GitSyncError):
    """Path is invalid or not under expected target_ddl structure."""


class ValidationError(PgDb2GitSyncError):
    """Validation failed (e.g. pre-push checks, conflict detection)."""


class GitOperationError(PgDb2GitSyncError):
    """Git command or operation failed."""


class ConfigError(PgDb2GitSyncError):
    """Configuration is missing or invalid."""
