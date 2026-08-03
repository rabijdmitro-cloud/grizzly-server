from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

DB_PATH = Path(__file__).resolve().parent / "app.db"


def init_db() -> None:
    """Create required tables if they do not exist."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE
            )
            """
        )
        conn.commit()


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


def add_user(name: str, email: str) -> int:
    """Insert a user and return the inserted row id."""
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO users (name, email) VALUES (?, ?)",
            (name, email),
        )
        conn.commit()
        return int(cursor.lastrowid)


def list_users() -> list[tuple[int, str, str]]:
    """Return all users sorted by id."""
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT id, name, email FROM users ORDER BY id"
        )
        rows = cursor.fetchall()
        return [(int(r[0]), str(r[1]), str(r[2])) for r in rows]
