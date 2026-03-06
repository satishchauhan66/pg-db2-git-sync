"""Apply SQL to Azure SQL database with continue-on-error reporting."""

from pathlib import Path
import os
import re
import struct
from typing import Callable, List, Optional, Union

from pydantic import BaseModel

from pg_db2_git_sync.api.sql_loader import SqlFile, read_sql_from_folder
from pg_db2_git_sync.core.repo import resolve_server_folder


class DbConfig(BaseModel):
    """Database connection config (Azure SQL; MFA via mfa_callback)."""

    host: str = ""
    port: int = 1433
    user: str = ""
    database: str = ""
    tenant_id: Optional[str] = None
    token_cache_file: Optional[str] = None
    odbc_driver: str = "ODBC Driver 18 for SQL Server"


class DeployError(BaseModel):
    """Single error from deploying a script (continue on error; collect and return at end)."""

    file_name: str = ""
    line_number: Optional[int] = None
    message: str = ""


class ApplyResult(BaseModel):
    """Result of apply_to_database. Errors listed at end; execution continues on error."""

    success: bool
    message: str
    applied_count: int = 0
    errors: List[DeployError] = []


def apply_to_database(
    connection_config: DbConfig,
    sql_folder_or_files: Union[Path, List[SqlFile]],
    mfa_callback: Optional[Callable[[], str]] = None,
    schema_name_only: Optional[str] = None,
    target_schema: Optional[str] = None,
) -> ApplyResult:
    """
    Apply SQL to database in order (01_schema → 02_table → …).
    MFA via mfa_callback (e.g. return token).
    If schema_name_only is set (e.g. "dbo"), execute only CREATE SCHEMA [dbo] statements.
    If target_schema is set (e.g. "dbo"), execute only statements that target that schema.
    """
    if isinstance(sql_folder_or_files, Path):
        files = read_sql_from_folder(sql_folder_or_files)
    else:
        files = sorted(sql_folder_or_files, key=lambda f: (f.order, f.name))

    if not connection_config.host or not connection_config.database or not connection_config.user:
        return ApplyResult(
            success=False,
            message="Missing destination settings: host, database, and user are required.",
            applied_count=0,
            errors=[DeployError(file_name="", line_number=None, message="Invalid destination config")],
        )

    try:
        import pyodbc  # type: ignore
    except Exception as e:
        return ApplyResult(
            success=False,
            message="pyodbc is required for Azure SQL execution.",
            applied_count=0,
            errors=[DeployError(file_name="", line_number=None, message=str(e))],
        )

    access_token: Optional[str] = None
    if mfa_callback:
        access_token = mfa_callback()
    else:
        access_token = _get_cached_azure_token(connection_config)

    if not access_token:
        return ApplyResult(
            success=False,
            message="Failed to acquire Azure AD token (MFA).",
            applied_count=0,
            errors=[DeployError(file_name="", line_number=None, message="Token acquisition failed")],
        )

    errors: List[DeployError] = []
    applied_count = 0
    attempted_statements = 0

    # SQL_COPT_SS_ACCESS_TOKEN (1256) expects UTF-16LE token bytes prefixed by 4-byte length.
    token_bytes = access_token.encode("utf-16-le")
    token_struct = struct.pack("<I", len(token_bytes)) + token_bytes
    attrs_before = {1256: token_struct}
    conn_str = (
        f"DRIVER={{{connection_config.odbc_driver}}};"
        f"SERVER=tcp:{connection_config.host},{connection_config.port};"
        f"DATABASE={connection_config.database};"
        "Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
    )

    try:
        conn = pyodbc.connect(conn_str, attrs_before=attrs_before, autocommit=False)
    except Exception as e:
        return ApplyResult(
            success=False,
            message="Could not connect to destination Azure SQL.",
            applied_count=0,
            errors=[DeployError(file_name="", line_number=None, message=str(e))],
        )

    with conn:
        cursor = conn.cursor()
        for sql_file in files:
            file_name = sql_file.name
            try:
                sql_text = sql_file.path.read_text(encoding="utf-8", errors="ignore")
            except Exception as e:
                errors.append(DeployError(file_name=file_name, line_number=None, message=f"Read failed: {e}"))
                continue

            statements = _split_sql_batches(sql_text)
            if schema_name_only:
                statements = _filter_create_schema_statements(statements, schema_name_only)
                if not statements:
                    continue
            if target_schema:
                statements = _filter_statements_for_schema(statements, target_schema)
                if not statements:
                    continue
            file_failed = False
            for stmt in statements:
                if not stmt.strip():
                    continue
                attempted_statements += 1
                try:
                    cursor.execute(stmt)
                except Exception as e:
                    err_msg = str(e)
                    errors.append(
                        DeployError(
                            file_name=file_name,
                            line_number=_guess_error_line(err_msg),
                            message=err_msg,
                        )
                    )
                    file_failed = True
                    # Continue-on-error behavior: move to next statement/file.
                    continue

            try:
                conn.commit()
            except Exception as e:
                errors.append(DeployError(file_name=file_name, line_number=None, message=f"Commit failed: {e}"))
                try:
                    conn.rollback()
                except Exception:
                    pass
                file_failed = True

            if not file_failed:
                applied_count += 1

    if attempted_statements == 0:
        return ApplyResult(
            success=False,
            message="No SQL statements matched selected filters (restore_objects/schema_name_only).",
            applied_count=0,
            errors=[DeployError(file_name="", line_number=None, message="No statements to execute")],
        )

    success = len(errors) == 0
    message = "Deployment completed." if success else "Deployment completed with errors."
    return ApplyResult(success=success, message=message, applied_count=applied_count, errors=errors)


def _split_sql_batches(sql_text: str) -> List[str]:
    """Split SQL text on standalone GO batch separators."""
    return re.split(r"(?im)^\s*GO\s*;?\s*$", sql_text)


def _filter_create_schema_statements(statements: List[str], schema_name: str) -> List[str]:
    """
    Keep only CREATE SCHEMA statements for the provided schema name.
    Example target: CREATE SCHEMA [dbo]
    """
    target = schema_name.strip().lower()
    result: List[str] = []
    pattern = re.compile(r"^\s*CREATE\s+SCHEMA\s+(?:\[(?P<bracketed>[^\]]+)\]|(?P<plain>[A-Za-z0-9_]+))\s*$", re.IGNORECASE)
    for stmt in statements:
        match = pattern.match(stmt.strip())
        if not match:
            continue
        found_name = (match.group("bracketed") or match.group("plain") or "").strip().lower()
        if found_name == target:
            result.append(stmt)
    return result


def _filter_statements_for_schema(statements: List[str], schema_name: str) -> List[str]:
    """
    Keep statements that target the given schema.
    Matches common SQL Server forms like:
      CREATE SCHEMA [dbo]
      CREATE TABLE [dbo].[TableX] (...)
      CREATE TABLE dbo.TableX (...)
    """
    target = schema_name.strip().lower()
    out: List[str] = []
    schema_token_patterns = [
        rf"\[{re.escape(target)}\]\s*\.",
        rf"\b{re.escape(target)}\s*\.",
        rf"CREATE\s+SCHEMA\s+\[{re.escape(target)}\]",
        rf"CREATE\s+SCHEMA\s+{re.escape(target)}\b",
    ]
    combined = re.compile("|".join(schema_token_patterns), flags=re.IGNORECASE)
    for stmt in statements:
        if combined.search(stmt):
            out.append(stmt)
    return out


def _guess_error_line(message: str) -> Optional[int]:
    """Best-effort extraction of a line number from DB error text."""
    match = re.search(r"\bline\s+(\d+)\b", message, flags=re.IGNORECASE)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            return None
    return None


def _get_cached_azure_token(connection_config: DbConfig) -> Optional[str]:
    """
    Get Azure SQL access token using MSAL directly (no external project dependency).
    Uses persistent token cache and interactive MFA when silent token is unavailable.
    """
    try:
        from msal import PublicClientApplication, SerializableTokenCache  # type: ignore
    except Exception:
        return None

    client_id = os.environ.get("AZURE_CLIENT_ID", "04b07795-8ddb-461a-bbee-02f9e1bf7b46")
    scope = ["https://database.windows.net/.default"]
    authority = (
        f"https://login.microsoftonline.com/{connection_config.tenant_id}"
        if connection_config.tenant_id
        else "https://login.microsoftonline.com/common"
    )

    cache_path = connection_config.token_cache_file or str(Path.home() / ".pg_db2_git_sync_msal_cache.json")
    cache = SerializableTokenCache()
    cache_file = Path(cache_path)
    if cache_file.exists():
        try:
            cache.deserialize(cache_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    app = PublicClientApplication(client_id=client_id, authority=authority, token_cache=cache)
    accounts = app.get_accounts(username=connection_config.user) or app.get_accounts()
    result = None
    if accounts:
        result = app.acquire_token_silent(scopes=scope, account=accounts[0])
    if not result or "access_token" not in result:
        # Interactive MFA login fallback
        result = app.acquire_token_interactive(scopes=scope, login_hint=connection_config.user)
    if not result or "access_token" not in result:
        return None

    if cache.has_state_changed:
        try:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(cache.serialize(), encoding="utf-8")
        except Exception:
            pass
    return result["access_token"]


def _filter_by_restore_objects(files: List[SqlFile], restore_objects: List[str]) -> List[SqlFile]:
    """
    Keep only files whose name matches restore_objects.
    Dependency rule: if "table" is requested and a schema file exists, include schema first.
    """
    if not restore_objects:
        return files
    normalized = [o.lower().strip() for o in restore_objects]
    selected = [f for f in files if any(n in f.name.lower() for n in normalized)]

    # Ensure schema is applied before table restores.
    wants_table = any("table" in n for n in normalized)
    if wants_table:
        schema_files = [f for f in files if "schema" in f.name.lower()]
        # Prepend schema files (already in number-wise order from `files`) if not present.
        existing = {str(f.path) for f in selected}
        for sf in reversed(schema_files):
            if str(sf.path) not in existing:
                selected.insert(0, sf)
    return selected


def deploy_to_destination(
    repo_path: Path,
    env: str,
    db_name: str,
    server_folder_name: str,
    connection_config: DbConfig,
    selected_file_indices: Optional[List[int]] = None,
    restore_objects: Optional[List[str]] = None,
    schema_name_only: Optional[str] = None,
    target_schema: Optional[str] = None,
    mfa_callback: Optional[Callable[[], str]] = None,
    target_ddl_base: str = "target_ddl",
) -> ApplyResult:
    """
    Deploy SQL from the selected target to destination.
    restore_objects: if None, run all SQL files; else run only those matching.
    If "table" is requested, schema file(s) are automatically included first.
    schema_name_only: if set (e.g. "dbo"), execute only CREATE SCHEMA [dbo] statements.
    target_schema: if set (e.g. "dbo"), execute only statements for that schema.
    Errors are mapped to script (file_name) and error message; returned at end (continue on error).
    """
    repo_path = Path(repo_path).resolve()
    server_path = resolve_server_folder(
        repo_path, env=env, db_name=db_name, server_folder_name=server_folder_name,
        target_ddl_base=target_ddl_base,
    )
    if server_path is None:
        return ApplyResult(
            success=False,
            message=f"Server folder not found: {server_folder_name} under {env}/{db_name}",
            applied_count=0,
            errors=[DeployError(file_name="", line_number=None, message=f"Folder not found: {server_folder_name}")],
        )
    all_files = read_sql_from_folder(server_path)
    if schema_name_only:
        files = [f for f in all_files if "schema" in f.name.lower()]
    else:
        if selected_file_indices is not None:
            files = [all_files[i] for i in selected_file_indices if 0 <= i < len(all_files)]
        else:
            files = all_files
        if restore_objects is not None:
            files = _filter_by_restore_objects(files, restore_objects)
    result = apply_to_database(
        connection_config=connection_config,
        sql_folder_or_files=files,
        mfa_callback=mfa_callback,
        schema_name_only=schema_name_only,
        target_schema=target_schema,
    )
    return result
