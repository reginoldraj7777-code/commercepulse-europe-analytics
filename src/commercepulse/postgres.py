from __future__ import annotations

import io
import os
from pathlib import Path

import pandas as pd
import psycopg
from psycopg import sql


def _postgres_type(series: pd.Series) -> str:
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_integer_dtype(series):
        return "bigint"
    if pd.api.types.is_float_dtype(series):
        return "double precision"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "timestamp"
    return "text"


def _connection_string() -> str:
    return (
        f"host={os.getenv('POSTGRES_HOST', 'localhost')} "
        f"port={os.getenv('POSTGRES_PORT', '5432')} "
        f"dbname={os.getenv('POSTGRES_DB', 'commercepulse')} "
        f"user={os.getenv('POSTGRES_USER', 'commercepulse')} "
        f"password={os.getenv('POSTGRES_PASSWORD', 'commercepulse_local_only')}"
    )


def _load_frame(connection: psycopg.Connection, table_name: str, frame: pd.DataFrame) -> None:
    columns = [sql.Identifier(column) for column in frame.columns]
    definitions = [
        sql.SQL("{} {}").format(sql.Identifier(column), sql.SQL(_postgres_type(frame[column])))
        for column in frame.columns
    ]
    with connection.cursor() as cursor:
        cursor.execute(
            sql.SQL("drop table if exists raw.{} cascade").format(sql.Identifier(table_name))
        )
        cursor.execute(
            sql.SQL("create table raw.{} ({})").format(
                sql.Identifier(table_name), sql.SQL(", ").join(definitions)
            )
        )
        buffer = io.StringIO()
        export_frame = frame.copy()
        for column in export_frame.select_dtypes(include=["datetime64[ns]"]).columns:
            export_frame[column] = export_frame[column].dt.strftime("%Y-%m-%d %H:%M:%S")
        export_frame.to_csv(buffer, index=False, header=False, na_rep="")
        buffer.seek(0)
        statement = sql.SQL("copy raw.{} ({}) from stdin with (format csv, null '')").format(
            sql.Identifier(table_name), sql.SQL(", ").join(columns)
        )
        with cursor.copy(statement) as copy:
            while chunk := buffer.read(1024 * 1024):
                copy.write(chunk)


def load_clean_folder(clean_folder: Path) -> list[dict[str, int | str]]:
    paths = sorted(clean_folder.glob("*.parquet"))
    if not paths:
        raise FileNotFoundError(f"No Parquet files found in {clean_folder}")
    loaded: list[dict[str, int | str]] = []
    with psycopg.connect(_connection_string()) as connection:
        with connection.cursor() as cursor:
            cursor.execute("create schema if not exists raw")
        for path in paths:
            frame = pd.read_parquet(path)
            _load_frame(connection, path.stem, frame)
            loaded.append({"table": f"raw.{path.stem}", "rows": len(frame)})
        connection.commit()
    return loaded
