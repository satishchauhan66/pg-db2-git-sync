# pg-db2-git-sync

Automate checking SQL DDL files into a Git repository (e.g. **satish chauhan-database-migration** `target_ddl`), discover server folders, and apply changes to databases with optional MFA support.

## Install

From a clone:

```bash
pip install -e .
# or: pip install .
```

From GitHub (public repo):

```bash
pip install git+https://github.com/YOUR_ORG/pg-db2-git-sync.git
```

### Run tests

```bash
pip install -e ".[dev]"
pytest
```

## Repository structure

The tool expects a repo layout like:

```
target_ddl/
├── non_prod/
│   └── <database_name>/        e.g. D_ACO, SLD_FIT
│       └── <server_folder>/   e.g. SS_SLD_DB22U, SS_INFT_DB22Q
│           ├── 01_schema.sql
│           ├── 02_table.sql
│           └── ...
└── prod/
    └── ...
```

Server folder naming may use hyphens or underscores (e.g. `SS_SLD_DB22U` or `SS-SLD-DB22U`). The last character often denotes environment: **U** = UAT, **D** = Dev, **Q** = QA.

## Usage

### CLI

```bash
# List server folders under target_ddl/non_prod (optional: filter by database name)
pg-db2-git-sync discover --repo-path /path/to/satish chauhan-database-migration --env non_prod [--db-name D_ACO]

# Sync local folder into repo and commit
pg-db2-git-sync sync --repo-path /path/to/repo --server-folder path/to/target_ddl/non_prod/D_ACO/SS_SLD_DB22U [--source-folder /path/to/local/sql] --message "Update DDL"

# Validate before push
pg-db2-git-sync validate --repo-path /path/to/repo
```

### Python API

```python
from pathlib import Path
from pg_db2_git_sync import (
    discover_server_folders,
    read_sql_from_folder,
    sync_to_git,
    validate_before_push,
)

repo = Path("/path/to/satish chauhan-database-migration")

# List server folders
folders = discover_server_folders(repo, env="non_prod", db_name="D_ACO")
for f in folders:
    print(f.path, f.db_name, f.server_folder)

# Read SQL files in execution order
sql_files = read_sql_from_folder(repo / "target_ddl/non_prod/D_ACO/SS_SLD_DB22U")

# Sync and commit (optional: copy from source_folder first)
result = sync_to_git(repo_path=repo, server_folder_path=repo / "target_ddl/non_prod/D_ACO/SS_SLD_DB22U", message="Update DDL", validate=True)

# Validate before push
validation = validate_before_push(repo)
```

## Configuration

Optional: set `REPO_PATH`, `TARGET_DDL_BASE` (default `target_ddl`), or use a config file. See `.env.example` for environment variables.

## Requirements

See [REQUIREMENTS_AND_ARCHITECTURE.md](REQUIREMENTS_AND_ARCHITECTURE.md) for full requirements and architecture.

## License

MIT
