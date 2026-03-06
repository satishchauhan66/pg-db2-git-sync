"""Load configuration from environment or config file. All paths are dynamic."""

from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SyncConfig(BaseSettings):
    """Configuration for pg-db2-git-sync. Loaded from env (PG_DB2_GIT_SYNC_*) or .env file."""

    model_config = SettingsConfigDict(
        env_prefix="PG_DB2_GIT_SYNC_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    repo_path: Optional[Path] = Field(default=None, description="Path to cloned Git repository (any clone: GitHub, GitLab, etc.)")
    target_ddl_base: str = Field(default="target_ddl", description="Base folder under repo for DDL (e.g. target_ddl)")
    default_env: str = Field(default="non_prod", description="Default environment: non_prod or prod")


def get_config() -> SyncConfig:
    """Return current config (env + .env). Use for dynamic repo path and defaults."""
    return SyncConfig()


def resolve_repo_path(repo_path: Optional[Path] = None) -> Optional[Path]:
    """
    Resolve repo path dynamically: argument overrides, else PG_DB2_GIT_SYNC_REPO_PATH from env/config.
    Returns None if neither is set.
    """
    if repo_path is not None:
        return Path(repo_path).resolve()
    cfg = get_config()
    if cfg.repo_path is not None:
        return Path(cfg.repo_path).resolve()
    return None
