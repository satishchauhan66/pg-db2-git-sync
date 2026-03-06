# pg-db2-git-sync — Requirements & Proposed Architecture

## 1. Overview

This document describes the requirements and proposed architecture for a **Python package** that automates checking SQL schema files into a Git repository, discovering database-specific source folders, and applying changes to databases (with multi-factor authentication support). The package is intended to be **installable** so other teams can use it as a dependency and call its operations programmatically or via CLI.

### 1.1 Repository Context (satish chauhan-database-migration)

- **Git repository (cloned)**: `satish chauhan-database-migration` — this is where all schema/DDL changes are versioned and where the tool will operate.
- **Primary working area**: Under the repo, the canonical structure for target DDL is:
  - **Base path**: `target_ddl / <environment> / <database_name> / <server_folder>`
  - **Environments**: `non_prod`, `prod`
  - **Database name**: e.g. `D_ACO`, `U_QHP`, `SLD_FIT`, `TESTINFO`
  - **Server folder**: Identifies the server and environment; naming may use hyphens or underscores (e.g. `SS_SLD_DB22U`, `SS-SLD-DB22U`, `SS_INFT_DB22Q`).

**Example paths:**

| Path (relative to repo root) | Meaning |
|------------------------------|--------|
| `target_ddl/non_prod/D_ACO/SS_SLD_DB22U` | Database **D_ACO**, server **SS_SLD_DB22**, environment **U** (UAT) |
| `target_ddl/non_prod/D_ACO/SS_SLD_DB22D` | Database **D_ACO**, server **SS_SLD_DB22**, environment **D** (Dev) |
| `target_ddl/non_prod/D_ACO/SS_INFT_DB22Q` | Database **D_ACO**, server **SS_INFT_DB22**, environment **Q** (e.g. QA) |

**Naming convention (server folder):**

- **Server name** + **environment suffix**: last character (or known suffix) indicates environment.
  - **U** = UAT  
  - **D** = Dev  
  - **Q** = QA (or similar)

**Typical user flow:** The user has a **server folder** (e.g. `SS_SLD_DB22U`) that contains **updated SQL scripts**. They want to either **push** those changes into the Git repo (check-in/commit/push) and/or **apply** them to the destination database. DB auth and apply will be handled by existing modules later; this document focuses on **requirements and repo structure**.

### 1.2 Play branch (feature-playground)

- **GitLab repo**: [66degrees-database-migration](https://gitlab.com/pgforsta/user-groups/66degrees/66degrees-database-migration) (private).
- **Play branch**: `feature-playground` — all “play” and deploy flows use this branch. Users clone the repo (e.g. via SSH or PAT), checkout `feature-playground`, and point the tool at the local clone path.

---

## 2. Deploy workflow (end-to-end flow)

The tool supports the following **deploy** flow. Destination is always **Azure SQL Server**; most logins use **MFA** (two or more login options). On execution errors, **continue** and collect errors; return the **list of errors at the end**.

| Step | Action |
|------|--------|
| 1 | **Connect to Git** — Use local clone of repo (branch `feature-playground`). |
| 2 | **List DBs** — List databases available under `target_ddl/<env>/` (database names). |
| 3 | **Select environment** — User chooses environment (e.g. `non_prod`, `prod`). |
| 4 | **Select database_name** — User chooses database (e.g. `D_ACO`). |
| 5 | **Select server_folder** — User chooses server folder (e.g. `SS_SLD_DB22U`). |
| 6 | **List all SQL files** — List SQL files in selected server folder (ordered 01_, 02_, …). |
| 7 | **User selects which files to execute** — User decides which of the listed SQL files to deploy. |
| 8 | **Connect to destination** — Connect to **Azure SQL Server** (2+ login options; most use **MFA**). |
| 9 | **Select correct database** — User or config selects the target database on Azure SQL. |
| 10 | **Deploy selected scripts** — Execute only the user-selected SQL files in order. |
| 11 | **Error handling** — On error for a specific file/line: record the error, **continue** with remaining scripts. At the end, **return a list of errors** (file, line, message). Success count and error list are both returned. |

**Error behaviour:** Continue on error; do not stop the whole run. Return a list of errors at the end (e.g. file name, line number if available, error message).

---

## 3. Goals

- **Automate** the workflow of checking SQL files (tables, indexes, etc.) into a Git repository.
- **Scale** beyond manual script generation and one-off local runs.
- **Integrate** Git operations into the database change workflow with validation before push.
- **Support** multi-factor authentication when applying changes to databases.
- **Expose** a clean API and CLI so other people can install the package and perform operations without forking or copying scripts.

---

## 4. Repository Structure (target_ddl)

Aligned with **satish chauhan-database-migration** repo:

```
target_ddl/
├── non_prod/
│   └── <database_name>/           e.g. D_ACO, U_QHP, SLD_FIT
│       └── <server_folder>/      e.g. SS_SLD_DB22U, SS_INFT_DB22Q
│           ├── 01_schema.sql
│           ├── 02_table.sql
│           ├── 03_constraints.sql
│           ├── 04_index.sql
│           ├── 05_trigger.sql
│           ├── 06_function.sql
│           ├── 07_procedures.sql (or 08_procedure.sql)
│           └── ... (other DDL; naming may vary per DB)
│   └── ...
└── prod/
    └── <database_name>/
        └── <server_folder>/
            └── (same structure)
```

- **Server folder names** in the repo may use **hyphens** (e.g. `SS-SLD-DB22U`) or **underscores** (e.g. `SS_SLD_DB22U`); the tool should support both and allow user to refer to a folder by either name or by full path.
- **SQL file ordering** (01, 02, …) implies execution order when applying to the database (schemas → tables → constraints → indexes → triggers → procedures/functions).

---

## 5. Functional Requirements

### 5.1 User Inputs

| Requirement | Description |
|-------------|-------------|
| **Git repository path** | User provides the **path to the cloned Git repository** (e.g. `satish chauhan-database-migration`). This is the single source of truth for DDL; all changes are made under it (e.g. under `target_ddl`). |
| **Server folder (or path)** | User identifies the **server folder** containing the SQL to sync or apply (e.g. `SS_SLD_DB22U`). This may be given as: (a) folder name only (tool resolves under a chosen env + db), or (b) full path such as `target_ddl/non_prod/D_ACO/SS_SLD_DB22U`. |
| **Source folder discovery** | The tool lists **available server folders** from the repo (e.g. under `target_ddl/non_prod/<db_name>/` or for a chosen database). User selects which folder(s) to work with. Optionally, user may provide **database name** and **environment** (non_prod/prod) to narrow the list. |
| **Optional: local folder** | For **check-in** flows, user may provide a **local folder path** (outside the repo) that contains updated SQL files; the tool will copy/sync these into the appropriate server folder in the repo and then commit. |

### 5.2 Git Operations

| Requirement | Description |
|-------------|-------------|
| **List server folders** | From the repo path, **discover and list** server folders under `target_ddl/<env>/<db_name>/`. Support filtering by environment (non_prod/prod) and optionally by database name. Handle both hyphen and underscore naming (e.g. `SS_SLD_DB22U` vs `SS-SLD-DB22U`). |
| **Read SQL files** | **Read SQL files** from the selected server folder(s) in the repo (and/or from a user-provided local folder). Respect execution order (01_schema, 02_table, …) when applying or validating. |
| **Check-in / commit** | Support **checking in** (add, commit) files under the repo. When user provides a **local folder** with updated scripts, copy/sync into the correct `target_ddl/.../<server_folder>/` and then commit. |
| **Conflict avoidance** | Design for **minimizing conflicts** (e.g. one server folder per change set, validation before push, optional branch strategy). |
| **Validation before push** | **Validate** state or content before pushing to the remote (e.g. lint, dry-run, conflict check, clean working tree). |

### 5.3 Database Operations (Azure SQL, MFA, continue-on-error)

| Requirement | Description |
|-------------|-------------|
| **Apply changes to database** | **Apply** only the **user-selected** SQL files to the destination in order. Destination is always **Azure SQL Server**. |
| **Multi-factor authentication (MFA)** | Support **MFA** (two or more login options); most connections use MFA. |
| **Continue on error** | On error for a file/line: record error, **continue** with remaining scripts. |
| **Return list of errors at end** | Return a list of errors (e.g. file name, line number, message). Report success count and full error list at the end. |

*DB connection and execution to be implemented with existing auth/apply modules; Azure SQL + MFA + per-error reporting are required.*

### 5.4 Package & Usability

| Requirement | Description |
|-------------|-------------|
| **Installable package** | Package is **installable** (e.g. via `pip install` from repo or index). |
| **Callable operations** | Other developers can **import and call** functions (e.g. `discover_server_folders()`, `sync_to_git()`, `apply_to_database()`) from their own code. |
| **CLI (optional)** | Optional **CLI** for interactive or scripted use: prompt or accept repo path, environment, database name, server folder (e.g. `SS_SLD_DB22U`), and optionally local folder for check-in. |

---

## 6. Non-Functional Requirements

- **Scalable**: Avoid manual, repetitive script generation; support multiple databases/folders and future extensions.
- **Safe**: Validation and optional dry-run before committing or pushing; clear feedback on errors.
- **Configurable**: Connection details, repo path, and folder conventions should be configurable (e.g. config file or env vars).
- **Documented**: Clear docs for install, config, and API/CLI usage.

---

## 7. Proposed Architecture

### 7.1 High-Level Components

```
┌─────────────────────────────────────────────────────────────────┐
│                     pg-db2-git-sync (Python package)             │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Config    │  │    CLI      │  │  Public API (modules)   │  │
│  │  (paths,    │  │  (prompts,  │  │  - discover_folders()   │  │
│  │   DB, repo) │  │   commands) │  │  - read_sql_files()      │  │
│  └──────┬──────┘  └──────┬──────┘  │  - sync_to_git()        │  │
│         │                │         │  - apply_to_database()  │  │
│         └────────────────┼─────────│  - validate_before_push │  │
│                          │         └───────────┬─────────────┘  │
│                          │                     │                │
│  ┌───────────────────────┴─────────────────────┴──────────────┐ │
│  │                     Core services                           │ │
│  │  - RepoDiscovery   - GitOperations   - SqlLoader            │ │
│  │  - DbConnector (MFA) - Validation   - ConflictDetection     │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 7.2 Module Layout (Proposed)

```
pg_db2_git_sync/
├── __init__.py           # Package root; expose main API
├── config.py             # Load config (env, file, defaults)
├── cli.py                # CLI entrypoint (e.g. click/typer)
├── api/
│   ├── __init__.py
│   ├── discover.py       # List server folders (target_ddl/<env>/<db>/)
│   ├── git_ops.py        # Add, commit, status, push (with validation)
│   ├── sql_loader.py     # Read SQL files from folder(s)
│   └── db_apply.py       # Apply SQL to DB with MFA support
├── core/
│   ├── __init__.py
│   ├── repo.py           # Repo path handling, folder discovery
│   ├── git.py            # Git commands (wrapper or GitPython)
│   ├── db.py             # DB connection + MFA (e.g. prompt, token)
│   └── validation.py     # Pre-push validation, conflict checks
└── exceptions.py         # Custom exceptions
```

### 7.3 Public API (Proposed)

Functions other teams can call after `pip install`:

| Function | Purpose |
|----------|---------|
| `discover_server_folders(repo_path: Path, env: str, db_name: Optional[str]) -> List[ServerFolderInfo]` | List server folders under `target_ddl/<env>/<db_name>/` (e.g. `SS_SLD_DB22U`); support both hyphen/underscore naming. |
| `read_sql_from_folder(folder_path: Path, order_by: Optional[str]) -> List[SqlFile]` | Read SQL files from a server folder; optional ordering (e.g. by 01_, 02_ prefix). |
| `sync_to_git(repo_path: Path, server_folder_path: Path, source_folder: Optional[Path], message: str, validate: bool = True) -> SyncResult` | Check-in files: if `source_folder` given, copy into repo `server_folder_path` then add/commit; optional validation before commit. |
| `validate_before_push(repo_path: Path, options: ValidateOptions) -> ValidationResult` | Run validation (e.g. lint, conflict check, clean tree) before push. |
| `apply_to_database(connection_config: DbConfig, sql_folder_or_files: Union[Path, List[SqlFile]], mfa_callback: Optional[Callable] = None) -> ApplyResult` | Apply SQL to database in order; MFA via existing modules/callback (implementation later). |

(Exact signatures can be refined; the idea is a small, stable set of entrypoints.)

### 7.4 Configuration

- **Repo path**: Path to cloned `satish chauhan-database-migration` (or equivalent); can be argument or config/env.
- **Target DDL base**: `target_ddl` under repo root; environments `non_prod`, `prod`; server folder naming (hyphen/underscore) configurable or normalized.
- **Database**: Connection params and MFA method from config/env; integration with existing auth modules later.
- (Folder conventions are defined by the Target DDL structure above.) (e.g. `databases/<name>/tables/`, `databases/<name>/indexes/`) so that “source folders” can be discovered consistently.

### 7.5 Git & Validation Flow

1. **Discover** server folders under `target_ddl/<env>/<db_name>/` (or from user-provided path).
2. **Read** SQL from the selected server folder (and/or from user-provided local folder for check-in).
3. **Validate** (e.g. SQL lint, conflict detection with `git status` / `git diff`).
4. **Check-in**: If syncing from local folder, copy into repo server folder; then `git add` → `git commit` (with message); optionally block if validation fails.
5. **Pre-push**: Run `validate_before_push()` (e.g. clean state, no conflicts with remote).
6. **Push**: Only after user or caller confirms (CLI prompt or explicit API flag).

### 7.6 Database & MFA Flow

1. **Resolve connection config** (from config/env or server folder → environment mapping).
2. **If MFA required**: Use **existing auth modules** (callback or interactive prompt).
3. **Establish connection** and **apply** SQL in order (01_schema → 02_table → …).
4. **Report** success/failure per file or batch.

### 7.7 Technology Choices (Proposed)

| Concern | Option |
|---------|--------|
| **Git** | `GitPython` or `subprocess` + `git` CLI. |
| **CLI** | `typer` or `click` for prompts and subcommands. |
| **Config** | `pydantic-settings` or `python-dotenv` + YAML/JSON. |
| **DB driver** | Driver appropriate to target DB (e.g. `psycopg2` for PostgreSQL, DB2 driver for DB2); connection layer abstracted for MFA. |
| **Packaging** | `pyproject.toml` (PEP 517/518), installable via `pip install .` or from private index. |

---

## 8. Out of Scope (Initial Version)

- Web UI or dashboard.
- Full conflict resolution (e.g. 3-way merge); focus on validation and clear reporting.
- Support for every database engine; start with one (e.g. PostgreSQL and/or DB2) and abstract so more can be added later.

---

## 9. Success Criteria

- Another team can **install** the package and **call** at least: discover folders, read SQL, sync to Git (with validation), and apply to DB with MFA.
- **Validation** runs before push and is clearly exposed (CLI + API).
- **Documentation** (README + optional docs site) explains install, config, and usage of the public API and CLI.

---

## 10. Next Steps

1. **Package setup**: Create package layout, `pyproject.toml`, and minimal `pg_db2_git_sync/__init__.py` with the proposed API stubs.
2. **Config & CLI**: Implement config loading and CLI skeleton (prompts for repo path, environment, database name, server folder e.g. `SS_SLD_DB22U`, optional local folder for check-in).
3. **Repo discovery**: Implement `discover_server_folders()` for `target_ddl/<env>/<db_name>/` with hyphen/underscore normalization.
4. **Git operations**: Implement add/commit and `validate_before_push()` (e.g. status, diff, optional lint).
5. **SQL loader**: Implement `read_sql_from_folder()` with ordering by filename (01_, 02_, …).
6. **DB apply (later)**: Integrate with existing auth/apply modules; apply SQL in order.
7. **Documentation**: README, config example, and API reference.
8. **Testing**: Unit tests for discovery, validation, and file loading; integration tests for Git (optional).

---

*This document is the single source of truth for requirements and proposed architecture until updated by the team.*
