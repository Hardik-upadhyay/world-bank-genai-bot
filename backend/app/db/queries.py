"""
Database Query Functions
--------------------------
All queries are parameterized and scoped to user context for security.
"""
import logging
from app.db.database import get_connection

logger = logging.getLogger(__name__)


# ── User Queries ───────────────────────────────────────────────────────────────

def get_user_by_username(username: str) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_user_by_id(user_id: int) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id, username, role, full_name, email, created_at FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


# ── Customer Profile ───────────────────────────────────────────────────────────

def get_customer_profile(user_id: int) -> dict | None:
    """Get customer profile strictly scoped to this user."""
    conn = get_connection()
    try:
        row = conn.execute("""
            SELECT c.*, u.full_name, u.email
            FROM customers c
            JOIN users u ON c.user_id = u.id
            WHERE c.user_id = ?
        """, (user_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_customer_by_id_for_manager(customer_db_id: int) -> dict | None:
    """Manager-only: Fetch any customer by their DB id."""
    conn = get_connection()
    try:
        row = conn.execute("""
            SELECT c.*, u.full_name, u.email
            FROM customers c
            JOIN users u ON c.user_id = u.id
            WHERE c.id = ?
        """, (customer_db_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


# ── Accounts ──────────────────────────────────────────────────────────────────

def get_accounts(user_id: int) -> list[dict]:
    """Get all accounts for the authenticated customer only."""
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT a.*
            FROM accounts a
            JOIN customers c ON a.customer_id = c.id
            WHERE c.user_id = ?
            ORDER BY a.opened_date DESC
        """, (user_id,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_account_summary(user_id: int) -> dict:
    """Aggregate summary: total balance, account count."""
    conn = get_connection()
    try:
        row = conn.execute("""
            SELECT COUNT(*) as account_count, SUM(a.balance) as total_balance
            FROM accounts a
            JOIN customers c ON a.customer_id = c.id
            WHERE c.user_id = ?
        """, (user_id,)).fetchone()
        return dict(row) if row else {"account_count": 0, "total_balance": 0}
    finally:
        conn.close()


# ── Transactions ──────────────────────────────────────────────────────────────

def get_transactions(user_id: int, limit: int = 10) -> list[dict]:
    """Get recent transactions strictly scoped to this user."""
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT t.*, a.account_number, a.account_type
            FROM transactions t
            JOIN accounts a ON t.account_id = a.id
            JOIN customers c ON a.customer_id = c.id
            WHERE c.user_id = ?
            ORDER BY t.date DESC
            LIMIT ?
        """, (user_id, limit)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ── Manager Operations ────────────────────────────────────────────────────────

def list_all_customers() -> list[dict]:
    """Manager-only: List all customers with their account summaries."""
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT c.id, c.customer_id, u.full_name, u.email, u.username,
                   c.kyc_status, c.created_at,
                   COUNT(a.id) as account_count,
                   COALESCE(SUM(a.balance), 0) as total_balance
            FROM customers c
            JOIN users u ON c.user_id = u.id
            LEFT JOIN accounts a ON a.customer_id = c.id
            GROUP BY c.id
            ORDER BY c.created_at DESC
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def create_customer_user(
    username: str,
    password_hash: str,
    full_name: str,
    email: str,
    customer_id: str,
    phone: str,
    address: str,
    account_type: str,
    initial_balance: float,
    currency: str,
    branch: str,
    manager_user_id: int,
) -> dict:
    """Manager-only: Create a new user + customer + initial account."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        # 1. Insert user
        cur.execute("""
            INSERT INTO users (username, password_hash, role, full_name, email)
            VALUES (?, ?, 'customer', ?, ?)
        """, (username, password_hash, full_name, email))
        new_user_id = cur.lastrowid

        # 2. Insert customer profile
        cur.execute("""
            INSERT INTO customers (user_id, customer_id, phone, address, created_by)
            VALUES (?, ?, ?, ?, ?)
        """, (new_user_id, customer_id, phone, address, manager_user_id))
        new_customer_id = cur.lastrowid

        # 3. Insert initial account
        import random, string
        acc_no = "WB" + "".join(random.choices(string.digits, k=10))
        cur.execute("""
            INSERT INTO accounts (customer_id, account_number, account_type, balance, currency, branch)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (new_customer_id, acc_no, account_type, initial_balance, currency, branch))

        conn.commit()
        return {"user_id": new_user_id, "customer_db_id": new_customer_id, "account_number": acc_no}
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
