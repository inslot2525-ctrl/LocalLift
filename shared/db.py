"""Tiny Postgres helper shared by web and pipeline. DATABASE_URL comes from the environment."""
import os
from contextlib import contextmanager
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

SCHEMA = Path(__file__).with_name("schema.sql")


@contextmanager
def connect():
    conn = psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row, autocommit=True)
    try:
        yield conn
    finally:
        conn.close()


def apply_schema() -> None:
    with connect() as conn:
        conn.execute(SCHEMA.read_text(encoding="utf-8"))


def log_event(kind: str, order_id: int | None = None, rep_code: str | None = None, meta: dict | None = None) -> None:
    with connect() as conn:
        conn.execute(
            "insert into events (kind, order_id, rep_code, meta) values (%s, %s, %s, %s)",
            (kind, order_id, rep_code, Jsonb(meta) if meta else None),
        )
