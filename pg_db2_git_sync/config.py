"""Load configuration from environment or config file."""

from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SyncConfig(BaseSettings):
    """Configuration for pg-db2-git-sync."""

    model_config = SettingsConfigDict(
        env_prefix="PG_DB2_GIT_SYNC_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    repo_path: Optional[Path] = Field(default=None, description="Path to cloned Git repository")
    target_ddl_base: str = Field(default="target_ddl", description="Base folder under repo for DDL (e.g. target_ddl)")
    default_env: str = Field(default="non_prod", description="Default environment: non_prod or prod")
