from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd


def ensure_directories(root: Path) -> None:
    for name in ("raw", "clean", "quarantine"):
        (root / name).mkdir(parents=True, exist_ok=True)


def table_path(folder: Path, table_name: str) -> Path:
    return folder / f"{table_name}.parquet"


def write_table(frame: pd.DataFrame, folder: Path, table_name: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = table_path(folder, table_name)
    frame.to_parquet(path, index=False, compression="zstd")
    return path


def read_table(folder: Path, table_name: str, columns: list[str] | None = None) -> pd.DataFrame:
    return pd.read_parquet(table_path(folder, table_name), columns=columns)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(payload: Any, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    return path


def build_file_manifest(folder: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(folder.glob("*.parquet")):
        frame = pd.read_parquet(path)
        rows.append(
            {
                "table": path.stem,
                "rows": int(len(frame)),
                "columns": int(len(frame.columns)),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return rows
