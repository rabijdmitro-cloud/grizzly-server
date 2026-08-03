from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

DB_PATH = Path(__file__).resolve().parent / "app.db"


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, ddl_type: str) -> None:
    """Add a missing column to an existing table without failing startup."""
    cursor = conn.execute(f"PRAGMA table_info({table})")
    existing = {str(row[1]).lower() for row in cursor.fetchall()}
    if column.lower() in existing:
        return
    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}")


def init_db() -> None:
    """Create/upgrade required tables to match WPF SQL expectations."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                legal_name TEXT,
                edrpou TEXT,
                contact_person TEXT,
                phone TEXT,
                email TEXT,
                manager TEXT,
                status TEXT,
                comments TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS contracts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                number TEXT,
                client_id INTEGER,
                date_start TEXT,
                date_end TEXT,
                status TEXT,
                service_type TEXT,
                manager TEXT,
                comments TEXT,
                FOREIGN KEY(client_id) REFERENCES clients(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS objects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                contract_id INTEGER,
                full_name TEXT,
                work_conditions TEXT,
                date_start TEXT,
                date_end TEXT,
                subdivision TEXT,
                dfo TEXT,
                guard_work_mode TEXT,
                salary_rate REAL,
                temporary_object TEXT,
                fixed_salary REAL,
                edrpou TEXT,
                call_import_code TEXT,
                address TEXT,
                coordinates TEXT,
                type TEXT,
                chief TEXT,
                direction TEXT,
                security_chief TEXT,
                contact_person TEXT,
                work_mode TEXT,
                status TEXT,
                instruction TEXT,
                special_conditions TEXT,
                dispatcher_comment TEXT,
                external_code TEXT,
                site_phone TEXT,
                active_alert TEXT,
                FOREIGN KEY(contract_id) REFERENCES contracts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                object_id INTEGER,
                type TEXT,
                work_mode TEXT,
                guards_count INTEGER,
                control_interval_min INTEGER,
                rate REAL,
                requirements TEXT,
                instruction TEXT,
                status TEXT,
                FOREIGN KEY(object_id) REFERENCES objects(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                position TEXT,
                subdivision TEXT,
                dfo TEXT,
                status TEXT,
                phone TEXT,
                documents TEXT,
                qualifications TEXT,
                rate TEXT,
                external_code TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS shifts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER,
                employee_id INTEGER,
                planned_start TEXT,
                planned_end TEXT,
                actual_start TEXT,
                actual_end TEXT,
                status TEXT,
                next_control_time TEXT,
                FOREIGN KEY(post_id) REFERENCES posts(id),
                FOREIGN KEY(employee_id) REFERENCES employees(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                datetime TEXT NOT NULL,
                type TEXT NOT NULL,
                object_id INTEGER,
                employee_id INTEGER,
                dispatcher TEXT,
                description TEXT,
                status TEXT DEFAULT 'pending',
                FOREIGN KEY(object_id) REFERENCES objects(id),
                FOREIGN KEY(employee_id) REFERENCES employees(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS timesheet (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER,
                date TEXT,
                post_id INTEGER,
                object_id INTEGER,
                day_hours REAL,
                night_hours REAL,
                holiday_hours REAL,
                overtime_hours REAL,
                status TEXT,
                FOREIGN KEY(employee_id) REFERENCES employees(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS timetable_cells (
                employee_id INTEGER,
                cell_date TEXT,
                value TEXT,
                PRIMARY KEY (employee_id, cell_date)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cameras (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                object_id INTEGER,
                name TEXT,
                protocol TEXT,
                ip_address TEXT,
                port TEXT,
                stream_path TEXT,
                login TEXT,
                password TEXT,
                notes TEXT,
                status TEXT,
                FOREIGN KEY(object_id) REFERENCES objects(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS location_pings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER,
                shift_id INTEGER,
                lat REAL,
                lon REAL,
                accuracy REAL,
                source TEXT,
                datetime TEXT,
                FOREIGN KEY(employee_id) REFERENCES employees(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                datetime TEXT,
                role TEXT,
                action TEXT,
                details TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_name TEXT NOT NULL UNIQUE,
                role_name TEXT NOT NULL,
                access_code TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1
            )
            """
        )

        # Legacy schema upgrade path for old app.db files.
        _ensure_column(conn, "objects", "contract_id", "INTEGER")
        _ensure_column(conn, "objects", "full_name", "TEXT")
        _ensure_column(conn, "objects", "work_conditions", "TEXT")
        _ensure_column(conn, "objects", "date_start", "TEXT")
        _ensure_column(conn, "objects", "date_end", "TEXT")
        _ensure_column(conn, "objects", "guard_work_mode", "TEXT")
        _ensure_column(conn, "objects", "salary_rate", "REAL")
        _ensure_column(conn, "objects", "temporary_object", "TEXT")
        _ensure_column(conn, "objects", "fixed_salary", "REAL")
        _ensure_column(conn, "objects", "edrpou", "TEXT")
        _ensure_column(conn, "objects", "coordinates", "TEXT")
        _ensure_column(conn, "objects", "type", "TEXT")
        _ensure_column(conn, "objects", "chief", "TEXT")
        _ensure_column(conn, "objects", "contact_person", "TEXT")
        _ensure_column(conn, "objects", "work_mode", "TEXT")
        _ensure_column(conn, "objects", "status", "TEXT")
        _ensure_column(conn, "objects", "instruction", "TEXT")
        _ensure_column(conn, "objects", "special_conditions", "TEXT")
        _ensure_column(conn, "objects", "dispatcher_comment", "TEXT")
        _ensure_column(conn, "objects", "site_phone", "TEXT")
        _ensure_column(conn, "objects", "active_alert", "TEXT")

        _ensure_column(conn, "employees", "position", "TEXT")
        _ensure_column(conn, "employees", "documents", "TEXT")
        _ensure_column(conn, "employees", "qualifications", "TEXT")
        _ensure_column(conn, "employees", "external_code", "TEXT")
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
