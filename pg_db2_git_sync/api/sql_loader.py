"""Read SQL files from a server folder with optional ordering by 01_, 02_ prefix."""

import re
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel


class SqlFile(BaseModel):
    """A single SQL file with path and optional order index."""

    path: Path
    order: int = 0
    name: str = ""

    class Config:
        arbitrary_types_allowed = True


# Match leading digits and underscore (e.g. 01_schema, 02_table)
_ORDER_PATTERN = re.compile(r"^(\d+)_(.+)$")


def _order_key(path: Path) -> tuple:
    """Sort key: (numeric_prefix, name)."""
    name = path.name
    m = _ORDER_PATTERN.match(name)
    if m:
        return (int(m.group(1)), name)
    return (999, name)


def read_sql_from_folder(
    folder_path: Path,
    order_by_prefix: bool = True,
    pattern: str = "*.sql",
) -> List[SqlFile]:
    """
    Read SQL files from a server folder.
    If order_by_prefix=True, sort by leading 01_, 02_, ... in filename.
    """
    folder_path = Path(folder_path)
    if not folder_path.is_dir():
        return []

    files: List[SqlFile] = []
    for i, path in enumerate(folder_path.glob(pattern)):
        if not path.is_file():
            continue
        order = i
        if order_by_prefix:
            idx, _ = _order_key(path)
            order = idx
        files.append(
            SqlFile(path=path, order=order, name=path.name)
        )

    if order_by_prefix:
        files.sort(key=lambda f: (f.order, f.name))
    return files
