"""
Seed Script – World Bank AI Assistant
----------------------------------------
Creates all DB tables and inserts:
  - 1 Bank Manager account
  - 3 Customer accounts with accounts and transactions

Run from backend/:
    python -m app.db.seed
"""
import sys
import random
import string
from pathlib import Path

# Ensure app is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.db.database import init_db, get_connection
from passlib.context import CryptContext

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def random_ref():
    return "REF" + "".join(random.choices(string.ascii_uppercase + string.digits, k=10))


def seed():
    print("Initializing database schema...")
    init_db()
    conn = get_connection()

    try:
        cur = conn.cursor()

        # ── 1. Manager ─────────────────────────────────────────────────────────
        cur.execute("DELETE FROM transactions")
        cur.execute("DELETE FROM accounts")
        cur.execute("DELETE FROM customers")
        cur.execute("DELETE FROM users")
        conn.commit()

        cur.execute("""
            INSERT INTO users (username, password_hash, role, full_name, email)
            VALUES (?, ?, 'manager', ?, ?)
        """, (
            "manager",
            pwd_ctx.hash("manager123"),
            "James Wilson",
            "james.wilson@worldbank.org"
        ))
        manager_id = cur.lastrowid
        print(f"  Created manager: username=manager, password=manager123 (id={manager_id})")

        # ── 2. Customers ───────────────────────────────────────────────────────
        customers = [
            {
                "username": "alice",
                "password": "alice123",
                "full_name": "Alice Chen",
                "email": "alice.chen@example.com",
                "customer_id": "WB-CUST-001",
                "phone": "+1-555-0101",
                "address": "42 Maple Street, Washington DC 20001, USA",
                "accounts": [
                    {"type": "Savings", "balance": 24750.00, "currency": "USD", "branch": "Washington HQ"},
                    {"type": "Fixed Deposit", "balance": 50000.00, "currency": "USD", "branch": "Washington HQ"},
                ],
            },
            {
                "username": "rahul",
                "password": "rahul123",
                "full_name": "Rahul Sharma",
                "email": "rahul.sharma@example.com",
                "customer_id": "WB-CUST-002",
                "phone": "+91-98765-43210",
                "address": "15 MG Road, New Delhi 110001, India",
                "accounts": [
                    {"type": "Current", "balance": 125000.00, "currency": "USD", "branch": "New Delhi Office"},
                    {"type": "Savings", "balance": 8420.50, "currency": "USD", "branch": "New Delhi Office"},
                ],
            },
            {
                "username": "sofia",
                "password": "sofia123",
                "full_name": "Sofía Martínez",
                "email": "sofia.martinez@example.com",
                "customer_id": "WB-CUST-003",
                "phone": "+52-55-1234-5678",
                "address": "Av. Reforma 222, Mexico City 06600, Mexico",
                "accounts": [
                    {"type": "Savings", "balance": 15300.75, "currency": "USD", "branch": "Mexico City Office"},
                ],
            },
        ]

        TRANSACTIONS_TEMPLATE = [
            ("Credit", 5000.00, "Salary credit – March 2026"),
            ("Debit", 1200.00, "Rent payment"),
            ("Credit", 250.00, "Interest credit Q1 2026"),
            ("Debit", 450.75, "Utility bills"),
            ("Credit", 3000.00, "Wire transfer received"),
            ("Debit", 800.00, "Online shopping – Amazon"),
            ("Debit", 120.50, "Insurance premium"),
            ("Credit", 500.00, "Freelance income"),
        ]

        for c_data in customers:
            cur.execute("""
                INSERT INTO users (username, password_hash, role, full_name, email)
                VALUES (?, ?, 'customer', ?, ?)
            """, (c_data["username"], pwd_ctx.hash(c_data["password"]), c_data["full_name"], c_data["email"]))
            user_id = cur.lastrowid

            cur.execute("""
                INSERT INTO customers (user_id, customer_id, phone, address, created_by)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, c_data["customer_id"], c_data["phone"], c_data["address"], manager_id))
            cust_db_id = cur.lastrowid

            for acc in c_data["accounts"]:
                acc_no = "WB" + "".join(random.choices(string.digits, k=10))
                cur.execute("""
                    INSERT INTO accounts (customer_id, account_number, account_type, balance, currency, branch)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (cust_db_id, acc_no, acc["type"], acc["balance"], acc["currency"], acc["branch"]))
                acc_id = cur.lastrowid

                # Seed transactions for first account of each customer
                bal = acc["balance"]
                for txn_type, amount, desc in TRANSACTIONS_TEMPLATE[:5]:
                    bal_after = bal + amount if txn_type == "Credit" else bal - amount
                    cur.execute("""
                        INSERT INTO transactions (account_id, type, amount, currency, description, reference_no, balance_after)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (acc_id, txn_type, amount, acc["currency"], desc, random_ref(), round(bal_after, 2)))
                    bal = bal_after

            print(f"  Created customer: username={c_data['username']}, password={c_data['password']}")

        conn.commit()
        print("\nSeeding complete!")
        print("\nCredentials summary:")
        print("  Manager  : username=manager   | password=manager123")
        print("  Customer1: username=alice     | password=alice123")
        print("  Customer2: username=rahul     | password=rahul123")
        print("  Customer3: username=sofia     | password=sofia123")

    except Exception as e:
        conn.rollback()
        print(f"Seed failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    seed()
