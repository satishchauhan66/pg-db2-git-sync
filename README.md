# pg-db2-git-sync

Automate checking SQL DDL files into a Git repository (e.g. **66degrees-database-migration** `target_ddl`), discover server folders, and apply changes to databases with optional MFA support. Repo path is **dynamic** (env or argument) so it works with any clone (GitHub, GitLab private, etc.).

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

### Dynamic config (recommended)

Set the repo path once via environment or `.env` so you don't pass it every time (works with any clone — GitHub, GitLab private, etc.):

```bash
# Windows (PowerShell)
$env:PG_DB2_GIT_SYNC_REPO_PATH = "C:\path\to\66degrees-database-migration"

# Or create .env in current dir (copy from .env.example):
# PG_DB2_GIT_SYNC_REPO_PATH=C:\path\to\66degrees-database-migration
```

### CLI

```bash
# List server folders (repo from env if not passed)
pg-db2-git-sync discover
pg-db2-git-sync discover /path/to/repo --env non_prod --db-name D_ACO

# Sync: server folder as first arg; repo from env or --repo-path
pg-db2-git-sync sync target_ddl/non_prod/D_ACO/SS_SLD_DB22U
pg-db2-git-sync sync target_ddl/non_prod/D_ACO/SS_SLD_DB22U --source-folder /path/to/local/sql -m "Update DDL"

# Validate (repo from env if not passed)
pg-db2-git-sync validate
```

### Python API

Repo path can come from env (dynamic) or be passed explicitly:

```python
from pathlib import Path
from pg_db2_git_sync import (
    discover_server_folders,
    read_sql_from_folder,
    sync_to_git,
    validate_before_push,
    resolve_repo_path,
    get_config,
)

# Dynamic: use PG_DB2_GIT_SYNC_REPO_PATH from env, or pass path (overrides env)
repo = resolve_repo_path() or resolve_repo_path(Path("/path/to/66degrees-database-migration"))
if repo is None:
    raise SystemExit("Set PG_DB2_GIT_SYNC_REPO_PATH or pass repo path")

# List server folders
folders = discover_server_folders(repo, env=get_config().default_env, db_name="D_ACO")
for f in folders:
    print(f.path, f.db_name, f.server_folder)

# Read SQL files in execution order
sql_files = read_sql_from_folder(repo / "target_ddl/non_prod/D_ACO/SS_SLD_DB22U")

# Sync and commit (optional: copy from source_folder first)
result = sync_to_git(repo_path=repo, server_folder_path=repo / "target_ddl/non_prod/D_ACO/SS_SLD_DB22U", message="Update DDL", validate=True)

# Validate before push
validation = validate_before_push(repo)
```

### Deploy flow (two functions)

1. **Connect to Git (URL + token + branch) and list all DBs** — user selects the database/target to deploy to.
2. **Deploy to destination** — run selected SQL; errors are **mapped to script and error message**.

```python
from pathlib import Path
from pg_db2_git_sync import (
    list_deploy_targets_from_remote,
    deploy_to_destination,
    DbConfig,
    DeployError,
)

# 1. Connect via URL + token + branch; list all deploy targets
targets, repo_path = list_deploy_targets_from_remote(
    url="https://gitlab.com/.../66degrees-database-migration.git",
    token="YOUR_GITLAB_OR_GITHUB_TOKEN",
    branch_name="feature-playground",
    clone_dir=Path("/path/to/clone/dir"),
)
for i, t in enumerate(targets):
    print(f"{i}: {t.env} | {t.db_name} | {t.server_folder}")

# User selects one (e.g. index 0)
chosen = targets[0]
config = DbConfig(host="...", database=chosen.db_name, user="...")

# 2. Deploy; errors mapped to script + message (continue on error, list at end)
result = deploy_to_destination(
    repo_path=repo_path,
    env=chosen.env,
    db_name=chosen.db_name,
    server_folder_name=chosen.server_folder,
    connection_config=config,
    selected_file_indices=None,  # or [0, 1, 2] to run only those files
    mfa_callback=None,
)
for e in result.errors:
    print(f"{e.file_name} line {e.line_number}: {e.message}")
```

For a **local** clone instead of URL/token/branch, use `list_deploy_targets(repo_path)` and pass `repo_path` to `deploy_to_destination`.

## Configuration

All config is **dynamic** (env or `.env`). See `.env.example`:

| Variable | Description |
|----------|-------------|
| `PG_DB2_GIT_SYNC_REPO_PATH` | Path to your local clone (GitHub, GitLab private, etc.). Set once so CLI/API don't need the path every time. |
| `PG_DB2_GIT_SYNC_TARGET_DDL_BASE` | Base folder under repo (default `target_ddl`). |
| `PG_DB2_GIT_SYNC_DEFAULT_ENV` | Default environment (default `non_prod`). |

## Requirements

See [REQUIREMENTS_AND_ARCHITECTURE.md](REQUIREMENTS_AND_ARCHITECTURE.md) for full requirements and architecture.

## License

MIT
