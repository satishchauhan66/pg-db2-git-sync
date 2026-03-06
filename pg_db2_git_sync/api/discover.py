"""List server folders under target_ddl/<env>/<db_name>/."""

from pathlib import Path
from typing import List, Optional

from pg_db2_git_sync.core.repo import ServerFolderInfo, discover_server_folders_impl


def discover_server_folders(
    repo_path: Path,
    env: str,
    db_name: Optional[str] = None,
    target_ddl_base: str = "target_ddl",
) -> List[ServerFolderInfo]:
    """
    List server folders (e.g. SS_SLD_DB22U) under target_ddl/<env>/<db_name>/.
    Handles both hyphen and underscore naming in folder names.
    """
    return discover_server_folders_impl(
        repo_path=Path(repo_path),
        env=env,
        db_name=db_name,
        target_ddl_base=target_ddl_base,
    )
