"""
SQLite Database Schema & Setup
--------------------------------
Tables: users, customers, accounts, transactions, chat_sessions, chat_messages
"""
import sqlite3
import logging
from pathlib import Path
from app.config import settings

logger = logging.getLogger(__name__)


def get_db_path() -> str:
    backend_dir = Path(__file__).resolve().parents[2]
    return str(backend_dir / "world_bank.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create all tables if they don't exist."""
    conn = get_connection()
    try:
        cur = conn.cursor()

        cur.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT    NOT NULL UNIQUE,
            password_hash TEXT  NOT NULL,
            role        TEXT    NOT NULL CHECK(role IN ('customer','manager')),
            full_name   TEXT    NOT NULL,
            email       TEXT,
            created_at  TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS customers (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL UNIQUE REFERENCES users(id),
            customer_id     TEXT    NOT NULL UNIQUE,
            phone           TEXT,
            address         TEXT,
            date_of_birth   TEXT,
            kyc_status      TEXT    DEFAULT 'Verified',
            created_by      INTEGER REFERENCES users(id),
            created_at      TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS accounts (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id     INTEGER NOT NULL REFERENCES customers(id),
            account_number  TEXT    NOT NULL UNIQUE,
            account_type    TEXT    NOT NULL,
            balance         REAL    NOT NULL DEFAULT 0,
            currency        TEXT    NOT NULL DEFAULT 'USD',
            branch          TEXT,
            status          TEXT    DEFAULT 'Active',
            opened_date     TEXT    DEFAULT (date('now'))
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id      INTEGER NOT NULL REFERENCES accounts(id),
            type            TEXT    NOT NULL,
            amount          REAL    NOT NULL,
            currency        TEXT    NOT NULL DEFAULT 'USD',
            description     TEXT,
            date            TEXT    DEFAULT (datetime('now')),
            reference_no    TEXT    NOT NULL UNIQUE,
            balance_after   REAL
        );

        CREATE TABLE IF NOT EXISTS chat_sessions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id),
            title       TEXT    NOT NULL DEFAULT 'New Conversation',
            created_at  TEXT    DEFAULT (datetime('now')),
            updated_at  TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS chat_messages (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  INTEGER NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
            role        TEXT    NOT NULL CHECK(role IN ('user','assistant')),
            content     TEXT    NOT NULL,
            model_used  TEXT,
            created_at  TEXT    DEFAULT (datetime('now'))
        );
        """)
        conn.commit()
        logger.info("Database initialized successfully.")
    finally:
        conn.close()
