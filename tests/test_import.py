"""Test that the package installs and public API is importable."""

import pytest
from pathlib import Path


def test_import_package():
    import pg_db2_git_sync as m
    assert m.__version__ == "0.1.0"


def test_import_public_api():
    from pg_db2_git_sync import (
        discover_server_folders,
        read_sql_from_folder,
        sync_to_git,
        validate_before_push,
        apply_to_database,
        SqlFile,
        SyncResult,
        ApplyResult,
        ServerFolderInfo,
        ValidationResult,
    )
    assert callable(discover_server_folders)
    assert callable(read_sql_from_folder)
    assert callable(sync_to_git)
    assert callable(validate_before_push)
    assert callable(apply_to_database)


def test_read_sql_from_folder_empty_dir(tmp_path):
    """read_sql_from_folder on empty dir returns []."""
    from pg_db2_git_sync import read_sql_from_folder
    assert read_sql_from_folder(tmp_path) == []


def test_read_sql_from_folder_ordering(tmp_path):
    """SQL files are ordered by 01_, 02_ prefix."""
    from pg_db2_git_sync import read_sql_from_folder
    (tmp_path / "02_second.sql").write_text("")
    (tmp_path / "01_first.sql").write_text("")
    (tmp_path / "03_third.sql").write_text("")
    files = read_sql_from_folder(tmp_path)
    assert len(files) == 3
    assert files[0].name == "01_first.sql"
    assert files[1].name == "02_second.sql"
    assert files[2].name == "03_third.sql"


def test_discover_requires_git_repo(tmp_path):
    """discover_server_folders raises on non-repo path."""
    from pg_db2_git_sync import discover_server_folders
    from pg_db2_git_sync.exceptions import RepoNotFoundError
    with pytest.raises(RepoNotFoundError):
        discover_server_folders(tmp_path, env="non_prod")
