import os
from pathlib import Path

from pg_db2_git_sync import list_deploy_targets_from_remote, deploy_to_destination, DbConfig

token = 'glpat-LS8ZOeqlADT8bwhygfFTdG86MQp1Omp0eXN4Cw.01.120mut3ot'

targets, repo_path = list_deploy_targets_from_remote(
    url="https://gitlab.com/pgforsta/user-groups/66degrees/66degrees-database-migration.git",
    token=token,
    branch_name="feature-playground",
    clone_dir=Path.home() / "66degrees-db-clone",
)

print(f"Clone: {repo_path}\nDBs: {len(targets)}")
for i, t in enumerate(targets):
    print(f"  {i}: {t.env} | {t.db_name} | {t.server_folder}")

# User selection: index 7 -> non_prod | D_DIACAP | SS_SLD_DB22U
# Destination (Azure SQL, MFA login)
TARGET_INDEX = 7
DEST_HOST = "route66-uat-eus2-mi.c6cdc75167f1.database.windows.net"
DEST_DB = "D_DIACAP_test_demo"
DEST_USER_MFA = "satish.chauhan@pressganey.com"
# What to restore: None = all; else list e.g. ["table"] for table restore only
RESTORE_OBJECTS = ["schema", "table"]
# Optional: only run CREATE SCHEMA [dbo]. Set None to disable.
SCHEMA_NAME_ONLY = None
# Optional: run only statements for this schema (e.g. "dbo")
TARGET_SCHEMA = "dbo"
AZURE_MIGRATION_TOOL_PATH = r"C:\Users\chauhs\Desktop\program\github\azure_migration_tool"

chosen = targets[TARGET_INDEX]
config = DbConfig(
    host=DEST_HOST,
    database=DEST_DB,
    user=DEST_USER_MFA,
    migration_tool_path=AZURE_MIGRATION_TOOL_PATH,
)
result = deploy_to_destination(
    repo_path=repo_path,
    env=chosen.env,
    db_name=chosen.db_name,
    server_folder_name=chosen.server_folder,
    connection_config=config,
    restore_objects=RESTORE_OBJECTS,
    schema_name_only=SCHEMA_NAME_ONLY,
    target_schema=TARGET_SCHEMA,
    mfa_callback=None,
)
print(f"\nDeploy: {chosen.db_name} -> {DEST_DB} | success={result.success}")
print(f"Applied files: {result.applied_count}")
for e in result.errors:
    print(f"  {e.file_name} L{e.line_number}: {e.message}")
