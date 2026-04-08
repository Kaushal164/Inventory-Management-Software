from __future__ import annotations

import hashlib
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AppConfig:
    db_path: Path


def default_config() -> AppConfig:
    # Put DB in project root beside README/requirements by default.
    root = Path(__file__).resolve().parents[1]
    return AppConfig(db_path=root / "inventory.db")


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'user',
  is_active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  sku TEXT UNIQUE,
  name TEXT NOT NULL,
  unit TEXT NOT NULL DEFAULT 'pcs',
  price REAL NOT NULL DEFAULT 0,
  cost REAL NOT NULL DEFAULT 0,
  stock REAL NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS services (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  code TEXT UNIQUE,
  name TEXT NOT NULL,
  price REAL NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sales (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  invoice_no TEXT UNIQUE,
  customer_name TEXT,
  created_by INTEGER,
  created_at TEXT NOT NULL,
  total REAL NOT NULL DEFAULT 0,
  FOREIGN KEY(created_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS sale_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  sale_id INTEGER NOT NULL,
  item_type TEXT NOT NULL CHECK(item_type IN ('product','service')),
  item_id INTEGER NOT NULL,
  description TEXT,
  qty REAL NOT NULL DEFAULT 1,
  unit_price REAL NOT NULL DEFAULT 0,
  line_total REAL NOT NULL DEFAULT 0,
  FOREIGN KEY(sale_id) REFERENCES sales(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS purchases (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  bill_no TEXT UNIQUE,
  supplier_name TEXT,
  created_by INTEGER,
  created_at TEXT NOT NULL,
  total REAL NOT NULL DEFAULT 0,
  FOREIGN KEY(created_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS purchase_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  purchase_id INTEGER NOT NULL,
  product_id INTEGER NOT NULL,
  description TEXT,
  qty REAL NOT NULL DEFAULT 1,
  unit_cost REAL NOT NULL DEFAULT 0,
  line_total REAL NOT NULL DEFAULT 0,
  FOREIGN KEY(purchase_id) REFERENCES purchases(id) ON DELETE CASCADE,
  FOREIGN KEY(product_id) REFERENCES products(id)
);
"""


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)
    ensure_default_admin(conn)


def ensure_default_admin(conn: sqlite3.Connection) -> None:
    # Default credentials per user request:
    # admin / admin123
    username = "admin"
    password = "admin123"
    password_hash = sha256_hex(password)
    now = utc_now_iso()
    row = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    if row is None:
        conn.execute(
            "INSERT INTO users (username, password_hash, role, is_active, created_at) VALUES (?,?,?,?,?)",
            (username, password_hash, "admin", 1, now),
        )
        conn.commit()


def verify_login(conn: sqlite3.Connection, username: str, password: str) -> dict[str, Any] | None:
    u = conn.execute(
        "SELECT id, username, password_hash, role, is_active FROM users WHERE username = ?",
        (username.strip(),),
    ).fetchone()
    if u is None:
        return None
    if int(u["is_active"]) != 1:
        return None
    if sha256_hex(password) != u["password_hash"]:
        return None
    return {"id": int(u["id"]), "username": str(u["username"]), "role": str(u["role"])}


def q(conn: sqlite3.Connection, sql: str, args: Iterable[Any] = ()) -> list[sqlite3.Row]:
    return list(conn.execute(sql, tuple(args)).fetchall())


def exec1(conn: sqlite3.Connection, sql: str, args: Iterable[Any] = ()) -> int:
    cur = conn.execute(sql, tuple(args))
    conn.commit()
    return int(cur.lastrowid)

