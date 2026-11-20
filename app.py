# ==============================================================================
# 🏛️ TaxMate Enterprise ERP Suite v6.7 (Full Master Build - Zero-Error Edition)
# ==============================================================================

import hashlib
import hmac
import html
import io
import math
import os
import sqlite3
import uuid
from datetime import date, datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

try:
    import qrcode
except ImportError:
    qrcode = None

# ------------------------------------------------------------------------------
# 1. PAGE CONFIGURATION & ENTERPRISE LIGHT 3D THEME
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="TaxMate Enterprise ERP Suite v6.7 Next-Gen",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Sarabun', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        -webkit-tap-highlight-color: transparent;
    }

    .stApp {
        background-color: #F8FAFC;
        color: #0F172A;
    }

    .hero-container-3d-light {
        background: linear-gradient(135deg, #FFFFFF 0%, #EFF6FF 50%, #DBEAFE 100%);
        border: 1px solid #CBD5E1;
        border-radius: 28px;
        padding: 40px 32px;
        text-align: center;
        margin-bottom: 28px;
        color: #0F172A;
        box-shadow: 0 20px 40px -15px rgba(37, 99, 235, 0.12), 0 10px 20px -10px rgba(0, 0, 0, 0.04);
        position: relative;
        overflow: hidden;
    }
    .hero-badge-pill-3d {
        display: inline-block;
        background: #FFFFFF;
        color: #2563EB;
        font-size: 13px;
        font-weight: 800;
        padding: 8px 24px;
        border-radius: 9999px;
        letter-spacing: 1.5px;
        margin-bottom: 16px;
        box-shadow: 0 4px 14px rgba(37, 99, 235, 0.15);
        border: 1px solid #BFDBFE;
    }
    .hero-title-main-light {
        font-size: 38px;
        font-weight: 800;
        color: #1E3A8A;
        margin: 0 0 12px 0;
        letter-spacing: -0.5px;
        line-height: 1.25;
    }
    .hero-subtitle-light {
        font-size: 18px;
        font-weight: 700;
        color: #2563EB;
        margin-bottom: 16px;
    }
    .hero-desc-text-light {
        font-size: 15.5px;
        color: #475569;
        max-width: 900px;
        margin: 0 auto 24px auto;
        line-height: 1.7;
    }

    .feature-card-3d {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        padding: 24px;
        border-radius: 22px;
        text-align: left;
        color: #0F172A;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        height: 100%;
    }
    .feature-card-3d:hover {
        transform: translateY(-6px);
        box-shadow: 0 20px 30px -10px rgba(37, 99, 235, 0.15);
        border-color: #93C5FD;
    }
    .feature-card-3d b {
        color: #1D4ED8;
        display: block;
        margin-bottom: 6px;
        font-size: 17px;
    }

    .icon-box-3d {
        width: 72px;
        height: 72px;
        margin: 0 0 16px 0;
        display: flex;
        align-items: center;
        justify-content: center;
        background: #EFF6FF;
        border-radius: 18px;
        border: 1px solid #BFDBFE;
        box-shadow: inset 0 2px 4px rgba(255,255,255,0.8), 0 6px 12px rgba(37,99,235,0.08);
    }

    [data-testid="stMetricValue"] {
        font-size: 26px !important;
        font-weight: 800 !important;
        color: #1E3A8A !important;
    }
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #E2E8F0 !important;
    }
    .stButton>button, .stFormSubmitButton>button {
        border-radius: 14px !important;
        font-weight: 700 !important;
        min-height: 46px !important;
        font-size: 15px !important;
    }
    .stButton>button[kind="primary"], .stFormSubmitButton>button[kind="primary"] {
        background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%) !important;
        border: none !important;
        color: #FFFFFF !important;
        width: 100%;
        box-shadow: 0 6px 18px rgba(37, 99, 235, 0.25);
    }
    .receipt-paper {
        background-color: #FFFFFF;
        border: 2px dashed #94A3B8;
        padding: 24px;
        border-radius: 16px;
        font-family: 'Courier New', Courier, monospace;
        color: #0F172A;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03);
    }
</style>
""",
    unsafe_allow_html=True,
)

# ------------------------------------------------------------------------------
# 2. FAIL-SAFE DATABASE ENGINE & HELPERS
# ------------------------------------------------------------------------------
APP_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.environ.get(
    "TAXMATE_DB_FILE", os.path.join(APP_DIRECTORY, "taxmate_erp_v5.db")
)
if not os.path.isabs(DB_FILE):
    DB_FILE = os.path.join(APP_DIRECTORY, DB_FILE)

RESETTABLE_TABLE_GROUPS = {
    "🧾 ยอดขายและใบกำกับภาษี (Sales & Payments)": [
        "sales_payments",
        "sales",
    ],
    "📦 สินค้าและประวัติสต็อก (Products & Inventory)": [
        "inventory_movements",
        "products",
    ],
    "🤝 ลูกค้าสัมพันธ์ (CRM & VIP)": ["crm_customers"],
    "🛍️ ใบสั่งซื้อ (Purchase Orders)": ["purchase_orders"],
    "💸 ค่าใช้จ่าย (Expenses)": ["expenses"],
    "👥 พนักงานและรอบเงินเดือน (HR & Payroll)": [
        "payroll_items",
        "payroll_runs",
        "employees",
    ],
    "📒 สมุดรายวันบัญชี (Journal Entries)": ["journal_entries"],
    "🛡️ รายการขออนุมัติ (Approvals)": ["approvals"],
    "📜 ประวัติการใช้งาน (Audit Logs)": ["audit_logs"],
}

ALL_TRANSACTION_TABLES = [
    "sales_payments",
    "sales",
    "inventory_movements",
    "products",
    "crm_customers",
    "purchase_orders",
    "expenses",
    "payroll_items",
    "payroll_runs",
    "employees",
    "journal_entries",
    "approvals",
    "audit_logs",
]

ALLOWED_RESET_TABLES = set(ALL_TRANSACTION_TABLES) | {"users"}


def get_db_connection():
    conn = sqlite3.connect(DB_FILE, timeout=20)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def safe_rollback(conn):
    if conn is not None:
        try:
            if conn.in_transaction:
                conn.rollback()
        except sqlite3.Error:
            pass


def safe_text(value) -> str:
    return html.escape("" if value is None else str(value))


def ensure_column(cursor, table_name, column_name, declaration):
    columns = {
        row["name"] for row in cursor.execute(f'PRAGMA table_info("{table_name}")')
    }
    if column_name not in columns:
        cursor.execute(
            f'ALTER TABLE "{table_name}" ADD COLUMN "{column_name}" {declaration}'
        )


def table_exists(cursor, table_name: str) -> bool:
    return (
        cursor.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table_name,),
        ).fetchone()
        is not None
    )


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    rounds = 260_000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, rounds)
    return f"pbkdf2_sha256${rounds}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    if not stored_hash or not isinstance(stored_hash, str):
        return False
    if stored_hash.startswith("pbkdf2_sha256$"):
        try:
            _, rounds, salt_hex, digest_hex = stored_hash.split("$", 3)
            actual = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                bytes.fromhex(salt_hex),
                int(rounds),
            )
            return hmac.compare_digest(actual.hex(), digest_hex)
        except (ValueError, TypeError):
            return False
    return hmac.compare_digest(
        hashlib.sha256(password.encode("utf-8")).hexdigest(), stored_hash
    )


def generate_promptpay_payload(target_id: str, amount: float = None) -> str:
    target = str(target_id or "").replace("-", "").strip()
    if not target.isdigit() or len(target) not in (10, 13, 15):
        raise ValueError(
            "กรุณาระบุ PromptPay เบอร์มือถือ 10 หลัก เลขประจำตัว 13 หลัก หรือ e-Wallet 15 หลัก"
        )
    if len(target) == 10 and not target.startswith("0"):
        raise ValueError("เบอร์มือถือ PromptPay ต้องขึ้นต้นด้วย 0")
    if amount is not None and (
        not math.isfinite(float(amount)) or float(amount) <= 0
    ):
        raise ValueError("จำนวนเงิน PromptPay ต้องมากกว่า 0")

    target_type = "01" if len(target) == 10 else ("02" if len(target) == 13 else "03")
    target_fmt = ("0066" + target[1:]) if target_type == "01" else target

    tag29 = f"0016A000000677010111{target_type}{len(target_fmt):02d}{target_fmt}"
    payload = f"00020101021229{len(tag29):02d}{tag29}5303764"
    if amount and amount > 0:
        amt_str = f"{float(amount):.2f}"
        payload += f"54{len(amt_str):02d}{amt_str}"
    payload += "5802TH5911TaxMate ERP6304"

    crc = 0xFFFF
    for char in payload.encode("ascii"):
        crc ^= char << 8
        for _ in range(8):
            crc = (
                ((crc << 1) ^ 0x1021) & 0xFFFF
                if crc & 0x8000
                else (crc << 1) & 0xFFFF
            )
    return payload + f"{crc:04X}"


def make_qr_png_bytes(payload: str) -> bytes:
    if qrcode is None:
        raise RuntimeError(
            'ยังไม่ได้ติดตั้งแพ็กเกจ qrcode กรุณารันคำสั่ง: pip install "qrcode[pil]"'
        )
    buf = io.BytesIO()
    qrcode.make(payload).save(buf, format="PNG")
    return buf.getvalue()


def archive_legacy_table(cursor, table_name, required_columns):
    if not table_exists(cursor, table_name):
        return None

    columns = {
        row["name"] for row in cursor.execute(f'PRAGMA table_info("{table_name}")')
    }
    if required_columns.issubset(columns):
        return None

    suffix = 1
    while True:
        archive_name = f"{table_name}_legacy_v{suffix}"
        if not table_exists(cursor, archive_name):
            break
        suffix += 1
    cursor.execute(f'ALTER TABLE "{table_name}" RENAME TO "{archive_name}"')
    return archive_name


def migrate_legacy_purchase_orders(cursor, archive_name):
    if not archive_name:
        return
    legacy_rows = cursor.execute(f'SELECT * FROM "{archive_name}"').fetchall()
    item_columns = (
        {
            row["name"]
            for row in cursor.execute("PRAGMA table_info(purchase_order_items)")
        }
        if table_exists(cursor, "purchase_order_items")
        else set()
    )
    product_columns = {
        row["name"] for row in cursor.execute("PRAGMA table_info(products)")
    }

    for row in legacy_rows:
        row_data = dict(row)
        order_id = row_data.get("id")
        items = []
        quantity = row_data.get("qty")
        if order_id is not None and {"purchase_order_id", "quantity"}.issubset(
            item_columns
        ):
            item_query = (
                "SELECT poi.quantity"
                + (
                    ", p.name AS product_name"
                    if "product_id" in item_columns and "name" in product_columns
                    else ""
                )
                + " FROM purchase_order_items poi"
            )
            if "product_id" in item_columns and "name" in product_columns:
                item_query += " LEFT JOIN products p ON p.id = poi.product_id"
            item_query += " WHERE poi.purchase_order_id = ?"
            items = cursor.execute(item_query, (order_id,)).fetchall()
            if quantity is None:
                quantity = sum(int(item["quantity"] or 0) for item in items)
        item_name = row_data.get("item_name")
        if not item_name and items:
            item_names = [
                item["product_name"]
                for item in items
                if "product_name" in item.keys() and item["product_name"]
            ]
            item_name = ", ".join(dict.fromkeys(item_names))
        cursor.execute(
            """INSERT OR IGNORE INTO purchase_orders
               (po_no, vendor_name, item_name, qty, total_amount, status,
                branch, requested_by, approved_by, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                row_data.get("po_no")
                or row_data.get("po_number")
                or f"PO-LEGACY-{order_id}",
                row_data.get("vendor_name") or row_data.get("supplier") or "ไม่ระบุ",
                item_name or "รายการเดิม (ดูข้อมูลสำรอง)",
                max(int(quantity or 1), 1),
                float(row_data.get("total_amount") or row_data.get("total") or 0),
                row_data.get("status") or "Pending",
                row_data.get("branch") or "สำนักงานใหญ่",
                row_data.get("requested_by"),
                row_data.get("approved_by"),
                row_data.get("created_at"),
            ),
        )


def migrate_legacy_expenses(cursor, archive_name):
    if not archive_name:
        return
    legacy_rows = cursor.execute(f'SELECT * FROM "{archive_name}"').fetchall()
    for row in legacy_rows:
        row_data = dict(row)
        expense_id = row_data.get("id")
        cursor.execute(
            """INSERT OR IGNORE INTO expenses
               (exp_no, category, description, amount, approved_by, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                row_data.get("exp_no")
                or row_data.get("expense_no")
                or f"EXP-LEGACY-{expense_id}",
                row_data.get("category") or "อื่นๆ",
                row_data.get("description")
                or row_data.get("title")
                or "รายการเดิม (ดูข้อมูลสำรอง)",
                float(row_data.get("amount") or row_data.get("total") or 0),
                row_data.get("approved_by") or row_data.get("created_by"),
                row_data.get("created_at"),
            ),
        )


def init_db():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        # Table 1: Users
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL,
            department TEXT NOT NULL,
            email TEXT,
            status TEXT DEFAULT 'Active',
            allowed_modules TEXT NOT NULL DEFAULT 'all',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )"""
        )
        ensure_column(cursor, "users", "department", "TEXT NOT NULL DEFAULT ''")
        ensure_column(cursor, "users", "email", "TEXT")
        ensure_column(cursor, "users", "status", "TEXT NOT NULL DEFAULT 'Active'")
        ensure_column(
            cursor, "users", "allowed_modules", "TEXT NOT NULL DEFAULT 'all'"
        )

        # Table 2: Sales
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_no TEXT UNIQUE NOT NULL,
            customer TEXT NOT NULL,
            customer_tax_id TEXT,
            amount REAL NOT NULL,
            tax REAL NOT NULL,
            total REAL NOT NULL,
            status TEXT NOT NULL,
            branch TEXT DEFAULT 'สำนักงานใหญ่',
            payment_method TEXT DEFAULT 'โอนเงินผ่านธนาคาร',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )"""
        )
        ensure_column(cursor, "sales", "customer_tax_id", "TEXT")
        ensure_column(cursor, "sales", "branch", "TEXT DEFAULT 'สำนักงานใหญ่'")
        ensure_column(
            cursor, "sales", "payment_method", "TEXT DEFAULT 'โอนเงินผ่านธนาคาร'"
        )
        ensure_column(cursor, "sales", "created_at", "TIMESTAMP")
        cursor.execute(
            "UPDATE sales SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL"
        )

        # Table 3: Products & Movements
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            stock INTEGER NOT NULL,
            category TEXT NOT NULL,
            branch TEXT DEFAULT 'สำนักงานใหญ่',
            min_stock INTEGER DEFAULT 10
        )"""
        )
        ensure_column(cursor, "products", "min_stock", "INTEGER DEFAULT 10")
        cursor.execute("UPDATE products SET min_stock = 10 WHERE min_stock IS NULL")

        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS inventory_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL REFERENCES products(id),
            movement_type TEXT NOT NULL CHECK (movement_type IN ('Receipt', 'Issue')),
            quantity INTEGER NOT NULL CHECK (quantity > 0),
            balance_after INTEGER NOT NULL CHECK (balance_after >= 0),
            reference TEXT NOT NULL,
            created_by TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )"""
        )

        # Table 4: CRM Customers
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS crm_customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cust_code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            tier TEXT DEFAULT 'Silver',
            points INTEGER DEFAULT 0
        )"""
        )

        # Table 5: Purchase Orders
        legacy_purchase_orders = archive_legacy_table(
            cursor,
            "purchase_orders",
            {"po_no", "vendor_name", "item_name", "qty", "total_amount", "status"},
        )
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS purchase_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            po_no TEXT UNIQUE NOT NULL,
            vendor_name TEXT NOT NULL,
            item_name TEXT NOT NULL,
            qty INTEGER NOT NULL,
            total_amount REAL NOT NULL,
            status TEXT DEFAULT 'Pending',
            branch TEXT DEFAULT 'สำนักงานใหญ่',
            requested_by TEXT,
            approved_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )"""
        )
        ensure_column(
            cursor, "purchase_orders", "branch", "TEXT DEFAULT 'สำนักงานใหญ่'"
        )
        ensure_column(cursor, "purchase_orders", "requested_by", "TEXT")
        ensure_column(cursor, "purchase_orders", "approved_by", "TEXT")
        migrate_legacy_purchase_orders(cursor, legacy_purchase_orders)

        # Table 6: Expenses
        legacy_expenses = archive_legacy_table(
            cursor,
            "expenses",
            {"exp_no", "category", "description", "amount", "approved_by"},
        )
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exp_no TEXT UNIQUE NOT NULL,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            approved_by TEXT,
            status TEXT NOT NULL DEFAULT 'Pending Approval',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )"""
        )
        ensure_column(
            cursor, "expenses", "status", "TEXT NOT NULL DEFAULT 'Pending Approval'"
        )
        migrate_legacy_expenses(cursor, legacy_expenses)
        cursor.execute(
            """UPDATE expenses SET status = 'Approved'
               WHERE status = 'Pending Approval' AND approved_by IS NOT NULL"""
        )

        # Table 7: Employees & Payroll
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            emp_code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            position TEXT NOT NULL,
            salary REAL NOT NULL,
            department TEXT NOT NULL,
            status TEXT DEFAULT 'Active'
        )"""
        )

        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS payroll_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            period TEXT UNIQUE NOT NULL,
            status TEXT NOT NULL DEFAULT 'Draft',
            created_by TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            paid_at TIMESTAMP
        )"""
        )

        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS payroll_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payroll_run_id INTEGER NOT NULL REFERENCES payroll_runs(id),
            employee_id INTEGER NOT NULL REFERENCES employees(id),
            gross_pay REAL NOT NULL CHECK (gross_pay >= 0),
            deductions REAL NOT NULL DEFAULT 0 CHECK (deductions >= 0),
            net_pay REAL NOT NULL CHECK (net_pay >= 0),
            UNIQUE(payroll_run_id, employee_id)
        )"""
        )

        # Table 8: Journal Entries
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS journal_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_date TEXT NOT NULL,
            account_code TEXT NOT NULL,
            account_name TEXT NOT NULL,
            debit REAL DEFAULT 0.0,
            credit REAL DEFAULT 0.0,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )"""
        )

        # Table 9: Approvals & Sales Payments
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS approvals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_type TEXT NOT NULL,
            title TEXT NOT NULL,
            amount REAL NOT NULL,
            requested_by TEXT NOT NULL,
            status TEXT DEFAULT 'Pending Approval',
            approved_by TEXT,
            document_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )"""
        )
        ensure_column(cursor, "approvals", "approved_by", "TEXT")
        ensure_column(cursor, "approvals", "document_id", "INTEGER")

        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS sales_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER NOT NULL REFERENCES sales(id),
            amount REAL NOT NULL CHECK (amount > 0),
            payment_method TEXT NOT NULL,
            received_by TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )"""
        )

        # Table 10: Audit Logs
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_name TEXT NOT NULL,
            action TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )"""
        )

        # เปิดใช้งานทุกบัญชีที่มีอยู่ในฐานข้อมูลให้อัตโนมัติ
        cursor.execute(
            "UPDATE users SET status = 'Active' WHERE status IS NULL OR status != 'Active'"
        )

        conn.commit()
    finally:
        conn.close()


def log_audit_action(user_name, action):
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO audit_logs (user_name, action) VALUES (?, ?)",
            (str(user_name or "System"), str(action)),
        )
        conn.commit()
    except sqlite3.Error:
        safe_rollback(conn)
    finally:
        conn.close()


def get_table_row_counts():
    conn = get_db_connection()
    try:
        counts = {}
        for table in ALL_TRANSACTION_TABLES + ["users"]:
            counts[table] = int(
                conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            )
        return counts
    finally:
        conn.close()


def reset_database_tables(table_names, actor=None, include_extra_tables=False):
    target_set = set(table_names)
    invalid_tables = target_set - ALLOWED_RESET_TABLES
    if invalid_tables:
        raise ValueError(f"ไม่พบตารางที่อนุญาตให้ลบ: {', '.join(sorted(invalid_tables))}")

    conn = get_db_connection()
    try:
        # ปิด Foreign Key ชั่วคราวก่อนเริ่ม Transaction เพื่อป้องกัน Error จากตารางเก่าตกค้าง
        conn.execute("PRAGMA foreign_keys = OFF")
        cursor = conn.cursor()
        cursor.execute("BEGIN IMMEDIATE")

        if include_extra_tables:
            db_tables = [
                row["name"]
                for row in cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
                ).fetchall()
            ]
            if "users" in target_set:
                ordered_targets = db_tables
            else:
                ordered_targets = [t for t in db_tables if t != "users"]
        else:
            deletion_order = ALL_TRANSACTION_TABLES + ["users"]
            ordered_targets = [
                t
                for t in deletion_order
                if t in target_set and table_exists(cursor, t)
            ]

        if not ordered_targets:
            raise ValueError("กรุณาเลือกข้อมูลอย่างน้อย 1 รายการที่ต้องการลบ")

        # ลบคำขออนุมัติที่ผูกกับ PO / Expense หากมีการลบเฉพาะหมวดนั้น
        if "purchase_orders" in target_set and "approvals" not in target_set:
            cursor.execute(
                "DELETE FROM approvals WHERE doc_type = 'PO' AND document_id IS NOT NULL"
            )
        if "expenses" in target_set and "approvals" not in target_set:
            cursor.execute(
                "DELETE FROM approvals WHERE doc_type = 'EXPENSE' AND document_id IS NOT NULL"
            )

        has_sequence = table_exists(cursor, "sqlite_sequence")
        deleted_total = 0
        for table in ordered_targets:
            cursor.execute(f'DELETE FROM "{table}"')
            deleted_total += max(cursor.rowcount, 0)
            if has_sequence:
                cursor.execute("DELETE FROM sqlite_sequence WHERE name = ?", (table,))

        if actor and "audit_logs" not in target_set and "users" not in target_set:
            cursor.execute(
                "INSERT INTO audit_logs (user_name, action) VALUES (?, ?)",
                (str(actor), f"ล้างข้อมูลตาราง: {', '.join(ordered_targets)}"),
            )

        conn.commit()
        return deleted_total, ordered_targets
    except Exception:
        safe_rollback(conn)
        raise
    finally:
        try:
            conn.execute("PRAGMA foreign_keys = ON")
        except sqlite3.Error:
            pass
        conn.close()


def delete_single_record(table_name: str, record_id: int, actor: str):
    allowed = {
        "sales",
        "products",
        "crm_customers",
        "purchase_orders",
        "expenses",
        "employees",
        "journal_entries",
        "approvals",
        "users",
    }
    if table_name not in allowed:
        raise ValueError("ไม่สามารถลบข้อมูลจากตารางนี้ได้")

    conn = get_db_connection()
    try:
        conn.execute("PRAGMA foreign_keys = OFF")
        cursor = conn.cursor()
        cursor.execute("BEGIN IMMEDIATE")

        if table_name == "sales":
            cursor.execute("DELETE FROM sales_payments WHERE sale_id = ?", (record_id,))
        elif table_name == "products":
            cursor.execute(
                "DELETE FROM inventory_movements WHERE product_id = ?", (record_id,)
            )
            if table_exists(cursor, "purchase_order_items"):
                cursor.execute(
                    "DELETE FROM purchase_order_items WHERE product_id = ?",
                    (record_id,),
                )
        elif table_name == "employees":
            cursor.execute(
                "DELETE FROM payroll_items WHERE employee_id = ?", (record_id,)
            )
        elif table_name == "purchase_orders":
            cursor.execute(
                "DELETE FROM approvals WHERE doc_type = 'PO' AND document_id = ?",
                (record_id,),
            )
        elif table_name == "expenses":
            cursor.execute(
                "DELETE FROM approvals WHERE doc_type = 'EXPENSE' AND document_id = ?",
                (record_id,),
            )

        cursor.execute(f'DELETE FROM "{table_name}" WHERE id = ?', (record_id,))
        if cursor.rowcount != 1:
            raise ValueError("ไม่พบรายการที่ต้องการลบ หรือรายการนี้ถูกลบไปแล้ว")

        cursor.execute(
            "INSERT INTO audit_logs (user_name, action) VALUES (?, ?)",
            (str(actor), f"ลบรายการ ID #{record_id} จากตาราง {table_name}"),
        )
        conn.commit()
    except Exception:
        safe_rollback(conn)
        raise
    finally:
        try:
            conn.execute("PRAGMA foreign_keys = ON")
        except sqlite3.Error:
            pass
        conn.close()


def record_sale_payment(sale_id, amount, payment_method, actor):
    amount = round(float(amount), 2)
    if not math.isfinite(amount) or amount <= 0:
        raise ValueError("ยอดรับชำระต้องมากกว่า 0")

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("BEGIN IMMEDIATE")
        sale = cursor.execute(
            "SELECT doc_no, total, status FROM sales WHERE id = ?", (sale_id,)
        ).fetchone()
        if not sale:
            raise ValueError("ไม่พบเอกสารขาย")
        if sale["status"] == "ชำระแล้ว":
            raise ValueError("เอกสารนี้ชำระครบแล้ว")
        paid = float(
            cursor.execute(
                "SELECT COALESCE(SUM(amount), 0) FROM sales_payments WHERE sale_id = ?",
                (sale_id,),
            ).fetchone()[0]
        )
        due = round(float(sale["total"]) - paid, 2)
        if due <= 0:
            raise ValueError("เอกสารนี้ชำระครบแล้ว")
        if amount > due:
            raise ValueError(f"ยอดรับชำระเกินยอดคงค้าง ฿{due:,.2f}")

        cursor.execute(
            """INSERT INTO sales_payments
               (sale_id, amount, payment_method, received_by)
               VALUES (?, ?, ?, ?)""",
            (sale_id, amount, payment_method, actor),
        )
        debit_account = (
            ("11200", "เงินรับผ่านบัตร")
            if payment_method == "บัตรเครดิต"
            else ("11100", "เงินสด/เงินฝากธนาคาร")
        )
        journal_description = f"รับชำระลูกหนี้ {sale['doc_no']}"
        cursor.executemany(
            """INSERT INTO journal_entries
               (entry_date, account_code, account_name, debit, credit, description)
               VALUES (?, ?, ?, ?, ?, ?)""",
            [
                (
                    date.today().isoformat(),
                    debit_account[0],
                    debit_account[1],
                    amount,
                    0.0,
                    journal_description,
                ),
                (
                    date.today().isoformat(),
                    "11300",
                    "ลูกหนี้การค้า",
                    0.0,
                    amount,
                    journal_description,
                ),
            ],
        )
        if round(paid + amount, 2) >= round(float(sale["total"]), 2):
            cursor.execute(
                "UPDATE sales SET status = 'ชำระแล้ว' WHERE id = ?", (sale_id,)
            )
        conn.commit()
        return max(round(due - amount, 2), 0.0)
    except Exception:
        safe_rollback(conn)
        raise
    finally:
        conn.close()


def adjust_inventory_stock(product_id, movement_type, quantity, reference, actor):
    if movement_type not in ("Receipt", "Issue"):
        raise ValueError("ประเภทการปรับสต็อกไม่ถูกต้อง")
    try:
        numeric_quantity = float(quantity)
    except (TypeError, ValueError):
        raise ValueError("จำนวนสินค้าต้องเป็นจำนวนเต็มมากกว่า 0") from None
    if (
        not math.isfinite(numeric_quantity)
        or not numeric_quantity.is_integer()
        or numeric_quantity < 1
    ):
        raise ValueError("จำนวนสินค้าต้องมากกว่า 0")
    quantity = int(numeric_quantity)
    if not isinstance(reference, str) or not reference.strip():
        raise ValueError("กรุณาระบุเหตุผลหรือเลขอ้างอิง")

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("BEGIN IMMEDIATE")
        product = cursor.execute(
            "SELECT stock FROM products WHERE id = ?", (product_id,)
        ).fetchone()
        if not product:
            raise ValueError("ไม่พบสินค้าในระบบ")
        current_stock = int(product["stock"])
        if movement_type == "Issue" and quantity > current_stock:
            raise ValueError(f"สต็อกไม่เพียงพอ คงเหลือ {current_stock} ชิ้น")
        new_stock = (
            current_stock + quantity
            if movement_type == "Receipt"
            else current_stock - quantity
        )
        cursor.execute(
            "UPDATE products SET stock = ? WHERE id = ? AND stock = ?",
            (new_stock, product_id, current_stock),
        )
        if cursor.rowcount != 1:
            raise ValueError("สต็อกเปลี่ยนแปลงแล้ว กรุณาโหลดหน้าใหม่")
        cursor.execute(
            """INSERT INTO inventory_movements
               (product_id, movement_type, quantity, balance_after, reference, created_by)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (product_id, movement_type, quantity, new_stock, reference.strip(), actor),
        )
        conn.commit()
        return new_stock
    except Exception:
        safe_rollback(conn)
        raise
    finally:
        conn.close()


def transition_approval(approval_id, status, actor):
    if status not in ("Approved", "Rejected"):
        raise ValueError("สถานะการอนุมัติไม่ถูกต้อง")

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("BEGIN IMMEDIATE")
        approval = cursor.execute(
            """SELECT doc_type, document_id FROM approvals
               WHERE id = ? AND status = 'Pending Approval'""",
            (approval_id,),
        ).fetchone()
        if not approval:
            raise ValueError("คำขอนี้ถูกดำเนินการแล้วหรือไม่พบในระบบ")

        cursor.execute(
            """UPDATE approvals SET status = ?, approved_by = ?
               WHERE id = ? AND status = 'Pending Approval'""",
            (status, actor, approval_id),
        )
        if cursor.rowcount != 1:
            raise ValueError("สถานะคำขอเปลี่ยนแปลงแล้ว กรุณาโหลดหน้าใหม่")

        if approval["doc_type"] == "PO" and approval["document_id"] is not None:
            cursor.execute(
                """UPDATE purchase_orders SET status = ?, approved_by = ?
                   WHERE id = ? AND status = 'Pending Approval'""",
                (status, actor, approval["document_id"]),
            )
        elif approval["doc_type"] == "EXPENSE" and approval["document_id"] is not None:
            expense = cursor.execute(
                """SELECT category, description, amount FROM expenses
                   WHERE id = ? AND status = 'Pending Approval'""",
                (approval["document_id"],),
            ).fetchone()
            if expense:
                cursor.execute(
                    """UPDATE expenses
                       SET status = ?, approved_by = CASE WHEN ? = 'Approved' THEN ? ELSE NULL END
                       WHERE id = ? AND status = 'Pending Approval'""",
                    (status, status, actor, approval["document_id"]),
                )
                if status == "Approved":
                    description = f"รับรู้ค่าใช้จ่าย {expense['description']}"
                    cursor.executemany(
                        """INSERT INTO journal_entries
                           (entry_date, account_code, account_name, debit, credit, description)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        [
                            (
                                date.today().isoformat(),
                                "61000",
                                f"ค่าใช้จ่าย - {expense['category']}",
                                float(expense["amount"]),
                                0.0,
                                description,
                            ),
                            (
                                date.today().isoformat(),
                                "21100",
                                "เจ้าหนี้ค่าใช้จ่าย",
                                0.0,
                                float(expense["amount"]),
                                description,
                            ),
                        ],
                    )

        conn.commit()
    except Exception:
        safe_rollback(conn)
        raise
    finally:
        conn.close()


def parse_payroll_period(period):
    cleaned = str(period or "").strip()
    try:
        parsed = datetime.strptime(cleaned, "%Y-%m")
    except ValueError as error:
        raise ValueError("กรุณาระบุรอบเงินเดือนเป็นรูปแบบ YYYY-MM") from error
    if parsed.strftime("%Y-%m") != cleaned:
        raise ValueError("กรุณาระบุรอบเงินเดือนเป็นรูปแบบ YYYY-MM")
    return cleaned


def generated_text_input(label, key, value_factory):
    pending_key = f"_pending_{key}"
    if pending_key in st.session_state:
        st.session_state[key] = st.session_state.pop(pending_key)
    if key not in st.session_state:
        st.session_state[key] = value_factory()
    return st.text_input(label, key=key)


def queue_generated_text_input(key, value):
    st.session_state[f"_pending_{key}"] = value


def create_payroll_run(period, actor):
    period = parse_payroll_period(period)
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute(
            "INSERT INTO payroll_runs (period, created_by) VALUES (?, ?)",
            (period, actor),
        )
        run_id = cursor.lastrowid
        employees = cursor.execute(
            "SELECT id, salary FROM employees WHERE status = 'Active'"
        ).fetchall()
        if not employees:
            raise ValueError("ไม่มีพนักงานที่ใช้งานอยู่สำหรับรอบเงินเดือนนี้")
        cursor.executemany(
            """INSERT INTO payroll_items
               (payroll_run_id, employee_id, gross_pay, deductions, net_pay)
               VALUES (?, ?, ?, 0, ?)""",
            [
                (
                    run_id,
                    employee["id"],
                    round(float(employee["salary"]), 2),
                    round(float(employee["salary"]), 2),
                )
                for employee in employees
            ],
        )
        conn.commit()
        return run_id, len(employees)
    except Exception:
        safe_rollback(conn)
        raise
    finally:
        conn.close()


def save_payroll_deduction(run_id, employee_id, deduction):
    deduction = float(deduction)
    if not math.isfinite(deduction) or deduction < 0:
        raise ValueError("ยอดหักต้องเป็นจำนวนเงินที่ไม่ติดลบ")
    deduction = round(deduction, 2)
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("BEGIN IMMEDIATE")
        run = cursor.execute(
            "SELECT status FROM payroll_runs WHERE id = ?", (run_id,)
        ).fetchone()
        item = cursor.execute(
            """SELECT id, gross_pay FROM payroll_items
               WHERE payroll_run_id = ? AND employee_id = ?""",
            (run_id, employee_id),
        ).fetchone()
        if not run or run["status"] != "Draft" or not item:
            raise ValueError("ไม่พบรายการเงินเดือนแบบร่างนี้")
        gross = float(item["gross_pay"])
        if deduction > gross:
            raise ValueError(f"ยอดหักต้องไม่เกินเงินเดือนก่อนหัก ฿{gross:,.2f}")
        cursor.execute(
            """UPDATE payroll_items SET deductions = ?, net_pay = ?
               WHERE id = ?""",
            (deduction, round(gross - deduction, 2), item["id"]),
        )
        conn.commit()
    except Exception:
        safe_rollback(conn)
        raise
    finally:
        conn.close()


def pay_payroll_run(run_id):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("BEGIN IMMEDIATE")
        run = cursor.execute(
            "SELECT period, status FROM payroll_runs WHERE id = ?", (run_id,)
        ).fetchone()
        if not run or run["status"] != "Draft":
            raise ValueError("รอบเงินเดือนนี้ถูกจ่ายไปแล้วหรือไม่มีอยู่ในระบบ")
        totals = cursor.execute(
            """SELECT COUNT(*), COALESCE(SUM(gross_pay), 0),
                      COALESCE(SUM(deductions), 0), COALESCE(SUM(net_pay), 0)
               FROM payroll_items WHERE payroll_run_id = ?""",
            (run_id,),
        ).fetchone()
        count, gross, deductions, net = totals
        gross, deductions, net = map(float, (gross, deductions, net))
        if count == 0:
            raise ValueError("ไม่มีรายการเงินเดือนในรอบนี้")
        if not math.isclose(gross, deductions + net, abs_tol=0.01):
            raise ValueError("ยอดเงินเดือนและรายการหักไม่สมดุล")

        entry_date = date.today().isoformat()
        journal_entries = [
            (
                entry_date,
                "51000",
                "ค่าใช้จ่ายเงินเดือน",
                gross,
                0.0,
                f"เงินเดือนรอบ {run['period']}",
            ),
            (
                entry_date,
                "11100",
                "เงินสด/เงินฝากธนาคาร",
                0.0,
                net,
                f"จ่ายเงินเดือนรอบ {run['period']}",
            ),
        ]
        if deductions:
            journal_entries.append(
                (
                    entry_date,
                    "21400",
                    "หนี้สินรายการหักเงินเดือน",
                    0.0,
                    deductions,
                    f"ตั้งหนี้สินรายการหักเงินเดือน {run['period']}",
                )
            )
        cursor.executemany(
            """INSERT INTO journal_entries
               (entry_date, account_code, account_name, debit, credit, description)
               VALUES (?, ?, ?, ?, ?, ?)""",
            journal_entries,
        )
        cursor.execute(
            """UPDATE payroll_runs SET status = 'Paid', paid_at = CURRENT_TIMESTAMP
               WHERE id = ? AND status = 'Draft'""",
            (run_id,),
        )
        if cursor.rowcount != 1:
            raise ValueError("สถานะรอบเงินเดือนเปลี่ยนแปลงแล้ว กรุณาโหลดหน้าใหม่")
        conn.commit()
        return net
    except Exception:
        safe_rollback(conn)
        raise
    finally:
        conn.close()


try:
    init_db()
except (sqlite3.Error, TypeError, ValueError) as error:
    st.error(f"ไม่สามารถเตรียมฐานข้อมูล ERP ได้: {error}")
    st.stop()

# ------------------------------------------------------------------------------
# 3. AUTHENTICATION & LANDING PAGE
# ------------------------------------------------------------------------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user = None

if not st.session_state.authenticated:
    conn = get_db_connection()
    try:
        user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    finally:
        conn.close()

    if user_count == 0:
        st.markdown("## 🛡️ ตั้งค่าผู้ดูแลระบบคนแรก")
        st.info("สร้างบัญชีผู้ดูแลระบบก่อนเริ่มใช้งาน TaxMate ERP")
        with st.form("initial_admin_setup_form"):
            initial_username = st.text_input("ชื่อผู้ดูแลระบบ (Username)")
            initial_name = st.text_input("ชื่อ-นามสกุล")
            initial_email = st.text_input("อีเมล")
            initial_password = st.text_input(
                "รหัสผ่าน (อย่างน้อย 4 ตัวอักษร)", type="password"
            )
            initial_password_confirm = st.text_input(
                "ยืนยันรหัสผ่าน", type="password"
            )
            create_initial_admin = st.form_submit_button(
                "สร้างบัญชีผู้ดูแลระบบ", type="primary"
            )
        if create_initial_admin:
            if not all(
                v.strip() for v in (initial_username, initial_name, initial_email)
            ):
                st.error("กรุณากรอกชื่อผู้ใช้ ชื่อ-นามสกุล และอีเมลให้ครบ")
            elif len(initial_password) < 4:
                st.error("รหัสผ่านต้องมีอย่างน้อย 4 ตัวอักษร")
            elif initial_password != initial_password_confirm:
                st.error("รหัสผ่านและการยืนยันรหัสผ่านไม่ตรงกัน")
            else:
                created_user = None
                conn = get_db_connection()
                try:
                    conn.execute("BEGIN IMMEDIATE")
                    if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]:
                        raise ValueError("มีบัญชีผู้ใช้แล้ว กรุณาเข้าสู่ระบบ")
                    conn.execute(
                        """INSERT INTO users
                           (username, password_hash, full_name, role, department, email, status)
                           VALUES (?, ?, ?, 'Admin', 'บริหารและจัดการ', ?, 'Active')""",
                        (
                            initial_username.strip(),
                            hash_password(initial_password),
                            initial_name.strip(),
                            initial_email.strip(),
                        ),
                    )
                    conn.commit()
                    row = conn.execute(
                        "SELECT * FROM users WHERE username = ?",
                        (initial_username.strip(),),
                    ).fetchone()
                    created_user = dict(row) if row else None
                except ValueError as error:
                    safe_rollback(conn)
                    st.error(str(error))
                except sqlite3.IntegrityError:
                    safe_rollback(conn)
                    st.error("ชื่อผู้ใช้นี้มีอยู่แล้ว")
                except sqlite3.Error as error:
                    safe_rollback(conn)
                    st.error(f"สร้างบัญชีผู้ดูแลระบบไม่สำเร็จ: {error}")
                finally:
                    conn.close()

                if created_user:
                    st.session_state.authenticated = True
                    st.session_state.user = created_user
                    log_audit_action(
                        initial_name.strip(), "สร้างบัญชีผู้ดูแลระบบเริ่มต้น"
                    )
                    st.success("สร้างบัญชีผู้ดูแลระบบเรียบร้อยแล้ว")
                    st.rerun()
        st.stop()

    with st.sidebar:
        st.markdown(
            """
        <div style="padding: 10px 0;">
            <div style="font-size: 40px; margin-bottom: 2px;">🏛️</div>
            <h2 style="margin: 0; color: #0F172A; font-weight: 800; font-size: 21px;">TaxMate ERP v6.7</h2>
        </div>
        """,
            unsafe_allow_html=True,
        )
        init_nav = st.radio("📍 เมนูระบบ:", ["🏠 หน้าแรก (Overview)", "🔑 เข้าสู่ระบบ"])
        st.divider()
        st.caption("🟢 สถานะฐานข้อมูล: เชื่อมต่อ SQLite พร้อมใช้งาน")

    if init_nav == "🏠 หน้าแรก (Overview)":
        st.markdown(
            """
        <div class="hero-container-3d-light">
            <span class="hero-badge-pill-3d">🏛️ NEXT-GEN LIGHT 3D ERP v6.7</span>
            <div class="hero-title-main-light">TaxMate Enterprise ERP Suite</div>
            <div class="hero-subtitle-light">High-Speed Financial & Compliance Management Platform</div>
            <div class="hero-desc-text-light">ศูนย์กลางบริหารจัดการบัญชี ภาษีไทย e-Tax สต็อกสินค้า CRM ประมาณการรายได้ จัดซื้อ คุมงบประมาณ เงินเดือน ระบบขออนุมัติ และศูนย์จัดการล้างข้อมูลครบวงจร</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        st.markdown("### 🧊 ฟีเจอร์หลักและสถาปัตยกรรม 3D ERP")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(
                """
            <div class="feature-card-3d">
                <div class="icon-box-3d">
                    <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#2563EB" stroke-width="2"><line x1="12" y1="20" x2="12" y2="10"></line><line x1="18" y1="20" x2="18" y2="4"></line><line x1="6" y1="20" x2="6" y2="16"></line></svg>
                </div>
                <b>📊 Financial Analytics & GL</b>
                <span style="font-size: 13.5px; color: #475569;">ลงบัญชีอัตโนมัติ พร้อมงบทดลอง งบกำไรขาดทุน และวิเคราะห์แนวโน้มรายได้แบบ Interactive</span>
            </div>
            """,
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown(
                """
            <div class="feature-card-3d">
                <div class="icon-box-3d">
                    <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#2563EB" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"></rect><rect x="7" y="7" width="3" height="3"></rect><rect x="14" y="7" width="3" height="3"></rect><rect x="7" y="14" width="3" height="3"></rect></svg>
                </div>
                <b>🧾 e-Tax & Dynamic QR</b>
                <span style="font-size: 13.5px; color: #475569;">ออกใบกำกับภาษี VAT 7% พร้อมระบบรับชำระหนี้ และสร้าง Dynamic PromptPay QR Code ทันที</span>
            </div>
            """,
                unsafe_allow_html=True,
            )
        with c3:
            st.markdown(
                """
            <div class="feature-card-3d">
                <div class="icon-box-3d">
                    <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#2563EB" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>
                </div>
                <b>🤝 Smart CRM, WMS & Payroll</b>
                <span style="font-size: 13.5px; color: #475569;">จัดการลูกค้า VIP สต็อกสินค้าแจ้งเตือนของใกล้หมด และรอบจ่ายเงินเดือนพนักงานครบวงจร</span>
            </div>
            """,
                unsafe_allow_html=True,
            )
    else:
        st.markdown("## 🔑 ศูนย์ยืนยันตัวตน (Authentication Center)")
        tab_login, tab_register = st.tabs(
            ["🔑 เข้าสู่ระบบ (Sign In)", "📝 ลงทะเบียนผู้ใช้งานใหม่ (Sign Up)"]
        )

        with tab_login:
            with st.form("login_form"):
                u = st.text_input("ชื่อผู้ใช้งาน (Username)")
                p = st.text_input("รหัสผ่าน (Password)", type="password")
                if st.form_submit_button("เข้าสู่ระบบ", type="primary"):
                    conn = None
                    database_error = False
                    user = None
                    try:
                        conn = get_db_connection()
                        user = conn.execute(
                            "SELECT * FROM users WHERE username = ?", (u.strip(),)
                        ).fetchone()
                    except sqlite3.Error as error:
                        st.error(f"เข้าสู่ระบบไม่สำเร็จเนื่องจากฐานข้อมูลขัดข้อง: {error}")
                        database_error = True
                    finally:
                        if conn:
                            conn.close()

                    if not database_error:
                        if user and verify_password(p, user["password_hash"]):
                            if str(user["status"] or "").strip().casefold() != "active":
                                conn_act = get_db_connection()
                                try:
                                    conn_act.execute(
                                        "UPDATE users SET status = 'Active' WHERE id = ?",
                                        (user["id"],),
                                    )
                                    conn_act.commit()
                                finally:
                                    conn_act.close()
                            user_dict = dict(user)
                            user_dict["status"] = "Active"
                            st.session_state.authenticated = True
                            st.session_state.user = user_dict
                            st.session_state["login_success_message"] = (
                                f"ยินดีต้อนรับคุณ {user['full_name']}"
                            )
                            log_audit_action(user["full_name"], "เข้าสู่ระบบสำเร็จ")
                            st.rerun()
                        else:
                            st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")

        with tab_register:
            st.info("ลงทะเบียนบัญชีผู้ใช้งานใหม่เพื่อเข้าสู่ระบบได้ทันที")
            with st.form("reg_form"):
                r_u = st.text_input("Username:")
                r_fn = st.text_input("ชื่อ-นามสกุล:")
                r_em = st.text_input("อีเมล:")
                r_role = st.selectbox(
                    "บทบาท (Role):",
                    ["Admin", "Executive", "Accounting", "POS", "HR"],
                )
                r_p1 = st.text_input(
                    "รหัสผ่าน (อย่างน้อย 4 ตัวอักษร):", type="password"
                )
                r_p2 = st.text_input("ยืนยันรหัสผ่าน:", type="password")
                if st.form_submit_button("สร้างบัญชีใหม่", type="primary"):
                    if not r_u.strip() or not r_fn.strip() or not r_em.strip():
                        st.error("กรุณากรอกชื่อผู้ใช้ ชื่อ-นามสกุล และอีเมลให้ครบ")
                    elif len(r_p1) < 4:
                        st.error("รหัสผ่านต้องมีอย่างน้อย 4 ตัวอักษร")
                    elif r_p1 != r_p2:
                        st.error("รหัสผ่านและการยืนยันรหัสผ่านไม่ตรงกัน")
                    else:
                        registered = False
                        conn = None
                        try:
                            conn = get_db_connection()
                            conn.execute(
                                """INSERT INTO users
                                   (username, password_hash, full_name, role, department, email, status)
                                   VALUES (?, ?, ?, ?, 'ทั่วไป', ?, 'Active')""",
                                (
                                    r_u.strip(),
                                    hash_password(r_p1),
                                    r_fn.strip(),
                                    r_role,
                                    r_em.strip(),
                                ),
                            )
                            conn.commit()
                            registered = True
                        except sqlite3.IntegrityError:
                            safe_rollback(conn)
                            st.error("ชื่อผู้ใช้นี้มีอยู่แล้ว")
                        except sqlite3.Error as error:
                            safe_rollback(conn)
                            st.error(f"สร้างบัญชีผู้ใช้ไม่สำเร็จ: {error}")
                        finally:
                            if conn:
                                conn.close()

                        if registered:
                            log_audit_action(
                                r_fn.strip(),
                                f"สมัครบัญชีผู้ใช้ใหม่: {r_u.strip()} ({r_role}/Active)",
                            )
                            st.success("สร้างบัญชีเรียบร้อยแล้ว สามารถเข้าสู่ระบบได้ทันที")
    st.stop()

# ------------------------------------------------------------------------------
# 4. MAIN SYSTEM APPLICATION NAVIGATION (LOGGED IN)
# ------------------------------------------------------------------------------
conn = None
try:
    conn = get_db_connection()
    current_user = conn.execute(
        "SELECT * FROM users WHERE id = ?", (st.session_state.user.get("id"),)
    ).fetchone()
except sqlite3.Error as error:
    st.error(f"ไม่สามารถตรวจสอบสถานะบัญชีได้: {error}")
    st.stop()
finally:
    if conn:
        conn.close()

if not current_user:
    st.session_state.clear()
    st.session_state.authenticated = False
    st.session_state.user = None
    st.error("ไม่พบบัญชีนี้ในระบบ กรุณาเข้าสู่ระบบใหม่อีกครั้ง")
    st.stop()

st.session_state.user = dict(current_user)
login_success_message = st.session_state.pop("login_success_message", None)
if login_success_message:
    st.success(login_success_message)

st.sidebar.title("🏛️ TaxMate ERP Suite")
st.sidebar.markdown(f"👤 **{safe_text(st.session_state.user.get('full_name'))}**")
st.sidebar.caption(
    f"Role: `{safe_text(st.session_state.user.get('role'))}` | "
    f"Dept: `{safe_text(st.session_state.user.get('department'))}`"
)
st.sidebar.markdown("---")

ALL_ROLES = {"Admin", "Super Admin", "Executive", "Accounting", "POS", "HR"}

menu_permissions = {
    "📊 Dashboard Overview": ALL_ROLES,
    "🧾 e-Tax Invoice & Dynamic QR": {
        "Admin",
        "Super Admin",
        "Executive",
        "Accounting",
        "POS",
    },
    "🤝 ระบบลูกค้าสัมพันธ์ (CRM & VIP)": {
        "Admin",
        "Super Admin",
        "Executive",
        "Accounting",
        "POS",
    },
    "📈 คาดการณ์ทางการเงิน (Forecast)": {
        "Admin",
        "Super Admin",
        "Executive",
        "Accounting",
    },
    "🛍️ จัดซื้อและคู่ค้า (Purchase Orders)": {
        "Admin",
        "Super Admin",
        "Executive",
        "Accounting",
    },
    "💸 คุมงบประมาณและค่าใช้จ่าย (Expenses)": {
        "Admin",
        "Super Admin",
        "Executive",
        "Accounting",
    },
    "📦 Smart Inventory WMS": {"Admin", "Super Admin", "Accounting", "POS"},
    "👥 HR & Payroll": {"Admin", "Super Admin", "HR"},
    "📒 บันทึกบัญชีและงบการเงิน (GL)": {"Admin", "Super Admin", "Accounting"},
    "🛡️ ระบบขออนุมัติ (E-Approval)": {
        "Admin",
        "Super Admin",
        "Executive",
        "Accounting",
        "HR",
    },
    "⚙️ Admin Settings & Audit Logs": {"Admin", "Super Admin"},
    "🗑️ ล้างข้อมูลระบบ (Reset Data)": ALL_ROLES,
}

user_role = st.session_state.user.get("role", "")
available_menus = [
    menu for menu, roles in menu_permissions.items() if user_role in roles
]
if not available_menus:
    available_menus = list(menu_permissions.keys())

app_menu = st.sidebar.radio("ระบบงานหลัก", available_menus)

st.sidebar.markdown("---")
if st.sidebar.button("🚪 ออกจากระบบ", use_container_width=True):
    log_audit_action(st.session_state.user["full_name"], "ออกจากระบบ")
    st.session_state.clear()
    st.session_state.authenticated = False
    st.session_state.user = None
    st.rerun()

st.title(app_menu)

# ------------------------------------------------------------------------------
# MODULE 1: DASHBOARD OVERVIEW
# ------------------------------------------------------------------------------
if app_menu == "📊 Dashboard Overview":
    conn = get_db_connection()
    try:
        df_sales = pd.read_sql_query("SELECT * FROM sales", conn)
        df_prod = pd.read_sql_query("SELECT * FROM products", conn)
        df_exp = pd.read_sql_query(
            "SELECT * FROM expenses WHERE status = 'Approved'", conn
        )
        pending_approvals_count = conn.execute(
            "SELECT COUNT(*) FROM approvals WHERE status = 'Pending Approval'"
        ).fetchone()[0]
    finally:
        conn.close()

    m1, m2, m3, m4, m5 = st.columns(5)
    tot_rev = float(df_sales["total"].fillna(0).sum()) if not df_sales.empty else 0.0
    tot_tax = float(df_sales["tax"].fillna(0).sum()) if not df_sales.empty else 0.0
    tot_exp = float(df_exp["amount"].fillna(0).sum()) if not df_exp.empty else 0.0
    tot_stock = int(df_prod["stock"].fillna(0).sum()) if not df_prod.empty else 0

    m1.metric("ยอดขายรวมสุทธิ", f"฿{tot_rev:,.2f}")
    m2.metric("ภาษีขาย VAT 7%", f"฿{tot_tax:,.2f}")
    m3.metric("ค่าใช้จ่ายอนุมัติแล้ว", f"฿{tot_exp:,.2f}")
    m4.metric("สินค้าในสต็อก", f"{tot_stock:,} ชิ้น")
    m5.metric("รออนุมัติ", f"{pending_approvals_count} รายการ")

    if not df_prod.empty:
        low_stock_df = df_prod[
            df_prod["stock"].fillna(0) <= df_prod["min_stock"].fillna(10)
        ]
        if not low_stock_df.empty:
            st.warning(
                f"⚠️ พบสินค้าต่ำกว่าเกณฑ์ขั้นต่ำ {len(low_stock_df)} รายการ: "
                + ", ".join(
                    f"{r.name} (เหลือ {int(r.stock)})"
                    for r in low_stock_df.itertuples()
                )
            )

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📈 แนวโน้มรายได้ และภาษี VAT")
        if not df_sales.empty:
            chart_sales = df_sales.copy()
            chart_sales["amount"] = chart_sales["amount"].fillna(0.0)
            chart_sales["tax"] = chart_sales["tax"].fillna(0.0)
            fig = px.bar(
                chart_sales,
                x="doc_no",
                y=["amount", "tax"],
                title="มูลค่าก่อน VAT และภาษีขายแยกตามเอกสาร",
                barmode="stack",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("ยังไม่มีข้อมูลการขายในระบบ")
    with c2:
        st.subheader("📊 สัดส่วนสถานะการชำระเงิน")
        if not df_sales.empty:
            fig_p = px.pie(df_sales, names="status", values="total", hole=0.4)
            st.plotly_chart(fig_p, use_container_width=True)
        else:
            st.info("ยังไม่มีข้อมูลสถานะการชำระเงิน")

# ------------------------------------------------------------------------------
# MODULE 2: E-TAX INVOICE & DYNAMIC QR
# ------------------------------------------------------------------------------
elif app_menu == "🧾 e-Tax Invoice & Dynamic QR":
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📝 ออกใบกำกับภาษีใหม่")
        with st.form("etax_form"):
            d_no = generated_text_input(
                "เลขที่เอกสาร",
                "etax_doc_no",
                lambda: f"INV-{date.today():%Y%m%d}-{uuid.uuid4().hex[:8].upper()}",
            )
            cust = st.text_input("ชื่อลูกค้า / นิติบุคคล", "บริษัท สยามเทคโนโลยี จำกัด")
            amt = st.number_input(
                "มูลค่าสินค้า/บริการ (บาท)", min_value=0.01, value=10000.0, step=500.0
            )
            amt = round(float(amt), 2)
            pay_method = st.selectbox(
                "ช่องทางชำระเงิน",
                ["โอนเงินผ่านธนาคาร", "PromptPay", "บัตรเครดิต", "เงินสด"],
            )
            promptpay_id = st.text_input(
                "PromptPay เบอร์มือถือ/เลขผู้เสียภาษี (กรณีเลือก PromptPay)",
                placeholder="เช่น 0812345678 หรือเลขประจำตัว 13 หลัก",
                help="ระบุเลข PromptPay ของผู้รับเงินเพื่อสร้าง QR สำหรับเอกสารนี้",
            )
            st_val = st.selectbox(
                "สถานะ",
                ["ชำระแล้ว", "รอชำระ"],
                index=1,
                help="เลือกชำระแล้วเฉพาะเมื่อได้รับเงินเรียบร้อย",
            )

            vat = round(amt * 0.07, 2)
            tot = round(amt + vat, 2)

            if st.form_submit_button("💾 บันทึกและออกใบกำกับภาษี", type="primary"):
                valid_input = True
                if not d_no.strip() or not cust.strip():
                    st.error("กรุณาระบุเลขที่เอกสารและชื่อลูกค้า")
                    valid_input = False
                elif pay_method == "PromptPay":
                    if not promptpay_id.strip():
                        st.error("กรุณาระบุเลข PromptPay เพื่อสร้าง QR")
                        valid_input = False
                    else:
                        try:
                            generate_promptpay_payload(promptpay_id, tot)
                        except ValueError as error:
                            st.error(str(error))
                            valid_input = False

                if valid_input:
                    saved_sale = False
                    conn = get_db_connection()
                    try:
                        cursor = conn.cursor()
                        cursor.execute("BEGIN IMMEDIATE")
                        cursor.execute(
                            """INSERT INTO sales
                               (doc_no, customer, amount, tax, total, status, payment_method)
                               VALUES (?, ?, ?, ?, ?, ?, ?)""",
                            (
                                d_no.strip(),
                                cust.strip(),
                                amt,
                                vat,
                                tot,
                                st_val,
                                pay_method,
                            ),
                        )
                        sale_id = cursor.lastrowid
                        if st_val != "ชำระแล้ว":
                            debit_code, debit_name = "11300", "ลูกหนี้การค้า"
                        elif pay_method == "บัตรเครดิต":
                            debit_code, debit_name = "11200", "เงินรับผ่านบัตร"
                        else:
                            debit_code, debit_name = "11100", "เงินสด/เงินฝากธนาคาร"

                        if st_val == "ชำระแล้ว":
                            cursor.execute(
                                """INSERT INTO sales_payments
                                   (sale_id, amount, payment_method, received_by)
                                   VALUES (?, ?, ?, ?)""",
                                (
                                    sale_id,
                                    tot,
                                    pay_method,
                                    st.session_state.user["full_name"],
                                ),
                            )
                        journal_rows = [
                            (
                                date.today().isoformat(),
                                debit_code,
                                debit_name,
                                tot,
                                0.0,
                                f"รับรู้ยอดขาย {d_no.strip()}",
                            ),
                            (
                                date.today().isoformat(),
                                "41100",
                                "รายได้จากการขาย",
                                0.0,
                                amt,
                                f"รับรู้ยอดขาย {d_no.strip()}",
                            ),
                            (
                                date.today().isoformat(),
                                "21300",
                                "ภาษีขาย",
                                0.0,
                                vat,
                                f"ภาษีขาย 7% {d_no.strip()}",
                            ),
                        ]
                        cursor.executemany(
                            """INSERT INTO journal_entries
                               (entry_date, account_code, account_name, debit, credit, description)
                               VALUES (?, ?, ?, ?, ?, ?)""",
                            journal_rows,
                        )
                        conn.commit()
                        saved_sale = True
                    except sqlite3.IntegrityError:
                        safe_rollback(conn)
                        st.error("เลขที่เอกสารนี้มีอยู่แล้ว")
                    except sqlite3.Error as error:
                        safe_rollback(conn)
                        st.error(f"บันทึกใบกำกับภาษีไม่สำเร็จ: {error}")
                    finally:
                        conn.close()

                    if saved_sale:
                        log_audit_action(
                            st.session_state.user["full_name"],
                            f"ออกใบกำกับภาษี {d_no.strip()}",
                        )
                        queue_generated_text_input(
                            "etax_doc_no",
                            f"INV-{date.today():%Y%m%d}-{uuid.uuid4().hex[:8].upper()}",
                        )
                        st.success(f"บันทึกเอกสาร {d_no.strip()} เรียบร้อยแล้ว!")
                        st.rerun()

    with c2:
        st.subheader("🧾 ตัวอย่างเอกสาร Printable View")
        safe_document_no = safe_text(d_no)
        safe_customer = safe_text(cust)
        st.markdown(
            f"""
        <div class="receipt-paper">
            <h3 style="text-align:center; margin-bottom:5px;">ใบกำกับภาษี / ใบเสร็จรับเงิน</h3>
            <p style="text-align:center; font-size:12px; color:#64748B;">TAX INVOICE / RECEIPT</p>
            <hr>
            <p><b>เลขที่:</b> {safe_document_no}</p>
            <p><b>ลูกค้า:</b> {safe_customer}</p>
            <p><b>มูลค่าก่อน VAT:</b> ฿{amt:,.2f}</p>
            <p><b>ภาษี VAT 7%:</b> ฿{vat:,.2f}</p>
            <h4 style="color:#2563EB;">ยอดรวมสุทธิ: ฿{tot:,.2f}</h4>
        </div>
        """,
            unsafe_allow_html=True,
        )

        if pay_method == "PromptPay" and promptpay_id.strip():
            try:
                payload = generate_promptpay_payload(promptpay_id, tot)
                qr_png = make_qr_png_bytes(payload)
            except (ValueError, RuntimeError) as error:
                st.error(str(error))
            else:
                st.subheader("💳 Dynamic PromptPay QR Code")
                st.image(
                    qr_png,
                    caption=f"สแกนชำระเงิน ฿{tot:,.2f}",
                    width=260,
                )
        else:
            st.info("เลือกช่องทาง PromptPay และระบุเลขผู้รับเงินเพื่อสร้าง QR Code")

    st.markdown("---")
    st.subheader("📋 รายการใบกำกับภาษีในระบบ")
    conn = get_db_connection()
    try:
        df_all_sales = pd.read_sql_query(
            """SELECT doc_no, customer, amount, tax, total, status,
                      payment_method, created_at
               FROM sales ORDER BY id DESC""",
            conn,
        )
        raw_open_sales = conn.execute(
            """SELECT s.id, s.doc_no, s.customer, s.total,
                      COALESCE(p.paid, 0) AS paid
               FROM sales s
               LEFT JOIN (
                   SELECT sale_id, SUM(amount) AS paid
                   FROM sales_payments GROUP BY sale_id
               ) p ON p.sale_id = s.id
               WHERE s.status != 'ชำระแล้ว'
                 AND ROUND(s.total - COALESCE(p.paid, 0), 2) >= 0.01
               ORDER BY s.id DESC"""
        ).fetchall()
    finally:
        conn.close()

    st.dataframe(df_all_sales, use_container_width=True, hide_index=True)
    if not df_all_sales.empty:
        st.download_button(
            "⬇️ ดาวน์โหลดรายงานขาย (CSV)",
            df_all_sales.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"taxmate_sales_{date.today().isoformat()}.csv",
            mime="text/csv",
        )

    open_sales = [
        row
        for row in raw_open_sales
        if round(float(row["total"]) - float(row["paid"]), 2) >= 0.01
    ]
    if open_sales:
        st.subheader("💳 รับชำระใบแจ้งหนี้ค้างรับ")
        sale_options = {
            f"{row['doc_no']} · {row['customer']} · "
            f"ค้าง ฿{round(float(row['total']) - float(row['paid']), 2):,.2f}": row
            for row in open_sales
        }
        selected_sale_label = st.selectbox(
            "เลือกเอกสารค้างชำระ",
            list(sale_options),
            key="receive_payment_sale",
        )
        selected_sale = sale_options[selected_sale_label]
        due_amount = round(
            float(selected_sale["total"]) - float(selected_sale["paid"]), 2
        )
        with st.form("receive_invoice_payment_form"):
            receive_method = st.selectbox(
                "ช่องทางรับชำระ",
                ["เงินสด", "โอนเงินผ่านธนาคาร", "บัตรเครดิต", "PromptPay"],
            )
            receive_amount = st.number_input(
                f"ยอดรับชำระ (ยอดคงค้าง ฿{due_amount:,.2f})",
                min_value=0.01,
                value=due_amount,
                key=f"receive_amount_{selected_sale['id']}",
            )
            receive_payment = st.form_submit_button("บันทึกรับชำระ", type="primary")
        if receive_payment:
            try:
                remaining = record_sale_payment(
                    selected_sale["id"],
                    receive_amount,
                    receive_method,
                    st.session_state.user["full_name"],
                )
            except (ValueError, sqlite3.Error) as error:
                st.error(str(error))
            else:
                log_audit_action(
                    st.session_state.user["full_name"],
                    f"รับชำระ {selected_sale['doc_no']} ฿{receive_amount:,.2f}",
                )
                st.success(f"รับชำระแล้ว · ยอดคงค้าง ฿{remaining:,.2f}")
                st.rerun()

# ------------------------------------------------------------------------------
# MODULE 3: CRM & VIP SYSTEM
# ------------------------------------------------------------------------------
elif app_menu == "🤝 ระบบลูกค้าสัมพันธ์ (CRM & VIP)":
    st.subheader("🤝 บริหารจัดการลูกค้า คะแนนสะสม และสถานะ VIP")

    c1, c2 = st.columns([1.2, 1])
    with c1:
        with st.expander("➕ ลงทะเบียนลูกค้าใหม่", expanded=True):
            with st.form("crm_form"):
                c_code = generated_text_input(
                    "รหัสลูกค้า",
                    "crm_customer_code",
                    lambda: f"CUST-{uuid.uuid4().hex[:8].upper()}",
                )
                c_name = st.text_input("ชื่อบริษัท / คุณลูกค้า")
                c_phone = st.text_input("เบอร์โทรศัพท์")
                c_email = st.text_input("อีเมล")
                c_tier = st.selectbox(
                    "ระดับสิทธิประโยชน์ (Tier)",
                    ["Silver", "Gold", "Platinum", "Diamond"],
                )
                c_points = st.number_input(
                    "คะแนนสะสมเริ่มต้น", min_value=0, value=100, step=50
                )

                if st.form_submit_button("บันทึกข้อมูลลูกค้า", type="primary"):
                    if not c_code.strip() or not c_name.strip():
                        st.error("กรุณาระบุรหัสและชื่อลูกค้า")
                    else:
                        saved_crm = False
                        conn = get_db_connection()
                        try:
                            conn.execute(
                                """INSERT INTO crm_customers
                                   (cust_code, name, phone, email, tier, points)
                                   VALUES (?, ?, ?, ?, ?, ?)""",
                                (
                                    c_code.strip(),
                                    c_name.strip(),
                                    c_phone.strip(),
                                    c_email.strip(),
                                    c_tier,
                                    int(c_points),
                                ),
                            )
                            conn.commit()
                            saved_crm = True
                        except sqlite3.IntegrityError:
                            safe_rollback(conn)
                            st.error("รหัสลูกค้านี้มีอยู่แล้ว")
                        except sqlite3.Error as error:
                            safe_rollback(conn)
                            st.error(f"บันทึกข้อมูลลูกค้าไม่สำเร็จ: {error}")
                        finally:
                            conn.close()

                        if saved_crm:
                            log_audit_action(
                                st.session_state.user["full_name"],
                                f"เพิ่มลูกค้าใหม่ {c_name.strip()}",
                            )
                            queue_generated_text_input(
                                "crm_customer_code",
                                f"CUST-{uuid.uuid4().hex[:8].upper()}",
                            )
                            st.success("บันทึกข้อมูลลูกค้าเรียบร้อยแล้ว!")
                            st.rerun()

    conn = get_db_connection()
    try:
        df_crm = pd.read_sql_query(
            "SELECT * FROM crm_customers ORDER BY id DESC", conn
        )
    finally:
        conn.close()

    with c2:
        if not df_crm.empty:
            fig_crm = px.pie(
                df_crm,
                names="tier",
                title="สัดส่วนระดับสมาชิกลูกค้า (CRM Tier)",
                hole=0.35,
            )
            st.plotly_chart(fig_crm, use_container_width=True)
        else:
            st.info("ยังไม่มีข้อมูลลูกค้าในระบบ")

    st.markdown("---")
    st.subheader("📋 รายชื่อลูกค้าและสิทธิประโยชน์ VIP")
    st.dataframe(df_crm, use_container_width=True, hide_index=True)

# ------------------------------------------------------------------------------
# MODULE 4: FINANCIAL FORECAST
# ------------------------------------------------------------------------------
elif app_menu == "📈 คาดการณ์ทางการเงิน (Forecast)":
    st.subheader("📈 วิเคราะห์และประมาณการรายได้จากข้อมูลขายจริง")

    conn = get_db_connection()
    try:
        df_sales_fc = pd.read_sql_query(
            """SELECT COALESCE(strftime('%Y-%m', created_at), strftime('%Y-%m', 'now')) AS period,
                      SUM(total) AS total
               FROM sales
               GROUP BY COALESCE(strftime('%Y-%m', created_at), strftime('%Y-%m', 'now'))
               ORDER BY period""",
            conn,
        )
    finally:
        conn.close()

    f1, f2, f3 = st.columns(3)
    current_rev = (
        float(df_sales_fc["total"].fillna(0).sum()) if not df_sales_fc.empty else 0.0
    )
    monthly_baseline = (
        float(df_sales_fc["total"].fillna(0).tail(3).mean())
        if not df_sales_fc.empty
        else 0.0
    )
    f1.metric("รายได้ปัจจุบันสะสม", f"฿{current_rev:,.2f}")
    f2.metric("ประมาณการเดือนถัดไป (เฉลี่ยสูงสุด 3 เดือน)", f"฿{monthly_baseline:,.2f}")
    f3.metric("จำนวนเดือนที่มีข้อมูลขาย", f"{len(df_sales_fc)} เดือน")

    st.markdown("---")
    st.subheader("📊 ประมาณการ 6 เดือนข้างหน้า")
    if df_sales_fc.empty:
        st.info("ยังไม่มีข้อมูลยอดขายสำหรับคำนวณประมาณการ")
    else:
        growth_pct = st.slider(
            "สมมติฐานอัตราเติบโตต่อเดือน (%)",
            min_value=-20,
            max_value=30,
            value=0,
            step=1,
        )
        today = date.today()
        forecast_months = []
        forecast_values = []
        for offset in range(1, 7):
            month_index = today.month - 1 + offset
            forecast_months.append(
                f"{today.year + month_index // 12:04d}-{month_index % 12 + 1:02d}"
            )
            forecast_values.append(
                round(monthly_baseline * ((1 + growth_pct / 100.0) ** offset), 2)
            )

        fig_fc = go.Figure()
        fig_fc.add_trace(
            go.Scatter(
                x=forecast_months,
                y=forecast_values,
                mode="lines+markers",
                name="ประมาณการยอดขาย",
                line=dict(color="#2563EB", width=4),
            )
        )
        fig_fc.update_layout(
            title=f"ประมาณการยอดขาย 6 เดือน (อัตราเติบโตสมมติ {growth_pct:+d}% ต่อเดือน)",
            xaxis_title="เดือน",
            yaxis_title="ยอดขายโดยประมาณ (บาท)",
        )
        st.plotly_chart(fig_fc, use_container_width=True)
        st.caption(
            "คำนวณจากฐานเฉลี่ยย้อนหลังไม่เกิน 3 เดือนล่าสุดตามสมมติฐานที่เลือก "
            "เพื่อช่วยวางแผนเบื้องต้นเท่านั้น"
        )

# ------------------------------------------------------------------------------
# MODULE 5: PURCHASE ORDERS & VENDORS
# ------------------------------------------------------------------------------
elif app_menu == "🛍️ จัดซื้อและคู่ค้า (Purchase Orders)":
    st.subheader("🛍️ ระบบออกใบสั่งซื้อ (PO) และจัดการซัพพลายเออร์")

    with st.expander("➕ สร้างใบสั่งซื้อ (PO) ใหม่", expanded=True):
        with st.form("po_form"):
            po_num = generated_text_input(
                "เลขที่ PO",
                "purchase_order_number",
                lambda: f"PO-{date.today():%Y%m%d}-{uuid.uuid4().hex[:8].upper()}",
            )
            v_name = st.text_input("ชื่อซัพพลายเออร์ / คู่ค้า", "บริษัท ซัพพลายฮับ จำกัด")
            i_name = st.text_input("รายการสินค้า / บริการที่สั่งซื้อ")
            qty = st.number_input("จำนวน", value=1, min_value=1, step=1)
            tot_price = st.number_input(
                "ราคารวม (บาท)", min_value=0.01, value=10000.0, step=1000.0
            )

            if st.form_submit_button("ส่งใบสั่งซื้อขออนุมัติ (PO)", type="primary"):
                if not all(v.strip() for v in (po_num, v_name, i_name)):
                    st.error("กรุณากรอกเลขที่ PO ผู้ขาย และรายการสินค้า")
                else:
                    saved_po = False
                    conn = get_db_connection()
                    try:
                        cursor = conn.cursor()
                        cursor.execute("BEGIN IMMEDIATE")
                        cursor.execute(
                            """INSERT INTO purchase_orders
                               (po_no, vendor_name, item_name, qty, total_amount,
                                status, requested_by)
                               VALUES (?, ?, ?, ?, ?, 'Pending Approval', ?)""",
                            (
                                po_num.strip(),
                                v_name.strip(),
                                i_name.strip(),
                                int(qty),
                                round(float(tot_price), 2),
                                st.session_state.user["full_name"],
                            ),
                        )
                        po_id = cursor.lastrowid
                        cursor.execute(
                            """INSERT INTO approvals
                               (doc_type, title, amount, requested_by, status, document_id)
                               VALUES ('PO', ?, ?, ?, 'Pending Approval', ?)""",
                            (
                                f"{po_num.strip()} · {v_name.strip()} · {i_name.strip()}",
                                round(float(tot_price), 2),
                                st.session_state.user["full_name"],
                                po_id,
                            ),
                        )
                        conn.commit()
                        saved_po = True
                    except sqlite3.IntegrityError:
                        safe_rollback(conn)
                        st.error("เลขที่ PO นี้มีอยู่แล้ว")
                    except sqlite3.Error as error:
                        safe_rollback(conn)
                        st.error(f"บันทึกใบสั่งซื้อไม่สำเร็จ: {error}")
                    finally:
                        conn.close()

                    if saved_po:
                        log_audit_action(
                            st.session_state.user["full_name"],
                            f"สร้าง PO {po_num.strip()}",
                        )
                        queue_generated_text_input(
                            "purchase_order_number",
                            f"PO-{date.today():%Y%m%d}-{uuid.uuid4().hex[:8].upper()}",
                        )
                        st.success(f"บันทึกใบสั่งซื้อ {po_num.strip()} และส่งขออนุมัติแล้ว!")
                        st.rerun()

    conn = get_db_connection()
    try:
        df_po = pd.read_sql_query(
            "SELECT * FROM purchase_orders ORDER BY id DESC", conn
        )
    finally:
        conn.close()
    st.dataframe(df_po, use_container_width=True, hide_index=True)

# ------------------------------------------------------------------------------
# MODULE 6: BUDGETING & EXPENSES
# ------------------------------------------------------------------------------
elif app_menu == "💸 คุมงบประมาณและค่าใช้จ่าย (Expenses)":
    st.subheader("💸 ระบบบันทึกและคุมค่าใช้จ่ายองค์กร (Expense Tracker)")

    c1, c2 = st.columns([1, 1])
    with c1:
        with st.form("exp_form"):
            e_num = generated_text_input(
                "เลขที่ใบสำคัญจ่าย",
                "expense_number",
                lambda: f"EXP-{date.today():%Y%m%d}-{uuid.uuid4().hex[:8].upper()}",
            )
            e_cat = st.selectbox(
                "หมวดหมู่ค่าใช้จ่าย",
                ["ค่าสาธารณูปโภค", "ค่าการตลาด", "ค่าเช่าสถานที่", "อุปกรณ์สำนักงาน", "อื่นๆ"],
            )
            e_desc = st.text_input("รายละเอียดค่าใช้จ่าย")
            e_amt = st.number_input(
                "จำนวนเงิน (บาท)", min_value=0.01, value=1000.0, step=100.0
            )

            if st.form_submit_button("บันทึกและส่งขออนุมัติค่าใช้จ่าย", type="primary"):
                if not e_num.strip() or not e_desc.strip():
                    st.error("กรุณาระบุเลขที่ใบสำคัญและรายละเอียด")
                else:
                    saved_exp = False
                    conn = get_db_connection()
                    try:
                        cursor = conn.cursor()
                        cursor.execute("BEGIN IMMEDIATE")
                        cursor.execute(
                            """INSERT INTO expenses
                               (exp_no, category, description, amount, approved_by, status)
                               VALUES (?, ?, ?, ?, NULL, 'Pending Approval')""",
                            (
                                e_num.strip(),
                                e_cat,
                                e_desc.strip(),
                                round(float(e_amt), 2),
                            ),
                        )
                        expense_id = cursor.lastrowid
                        cursor.execute(
                            """INSERT INTO approvals
                               (doc_type, title, amount, requested_by, status, document_id)
                               VALUES ('EXPENSE', ?, ?, ?, 'Pending Approval', ?)""",
                            (
                                f"{e_num.strip()} · {e_cat} · {e_desc.strip()}",
                                round(float(e_amt), 2),
                                st.session_state.user["full_name"],
                                expense_id,
                            ),
                        )
                        conn.commit()
                        saved_exp = True
                    except sqlite3.IntegrityError:
                        safe_rollback(conn)
                        st.error("เลขที่ใบสำคัญจ่ายนี้มีอยู่แล้ว")
                    except sqlite3.Error as error:
                        safe_rollback(conn)
                        st.error(f"บันทึกค่าใช้จ่ายไม่สำเร็จ: {error}")
                    finally:
                        conn.close()

                    if saved_exp:
                        log_audit_action(
                            st.session_state.user["full_name"],
                            f"บันทึกค่าใช้จ่าย {e_num.strip()}",
                        )
                        queue_generated_text_input(
                            "expense_number",
                            f"EXP-{date.today():%Y%m%d}-{uuid.uuid4().hex[:8].upper()}",
                        )
                        st.success(f"บันทึกค่าใช้จ่าย {e_num.strip()} และส่งขออนุมัติเรียบร้อย!")
                        st.rerun()

    conn = get_db_connection()
    try:
        df_exp = pd.read_sql_query("SELECT * FROM expenses ORDER BY id DESC", conn)
    finally:
        conn.close()

    with c2:
        if not df_exp.empty:
            fig_exp = px.pie(
                df_exp,
                names="category",
                values="amount",
                title="สัดส่วนค่าใช้จ่ายตามหมวดหมู่",
                hole=0.35,
            )
            st.plotly_chart(fig_exp, use_container_width=True)
        else:
            st.info("ยังไม่มีข้อมูลค่าใช้จ่ายในระบบ")

    st.markdown("---")
    st.subheader("📋 รายการบันทึกค่าใช้จ่ายทั้งหมด")
    st.dataframe(df_exp, use_container_width=True, hide_index=True)

# ------------------------------------------------------------------------------
# MODULE 7: SMART INVENTORY WMS
# ------------------------------------------------------------------------------
elif app_menu == "📦 Smart Inventory WMS":
    st.subheader("📦 จัดการสต็อกสินค้า (Inventory Control)")

    with st.expander("➕ เพิ่มรายการสินค้าใหม่"):
        with st.form("add_prod_form"):
            p_sku = generated_text_input(
                "รหัสสินค้า (SKU)",
                "product_sku",
                lambda: f"SKU-{uuid.uuid4().hex[:8].upper()}",
            )
            p_name = st.text_input("ชื่อสินค้า")
            p_price = st.number_input("ราคาขาย (บาท)", min_value=0.0, value=1000.0)
            p_stock = st.number_input("จำนวนสต็อกเริ่มต้น", min_value=0, value=10, step=1)
            p_min_stock = st.number_input(
                "จุดแจ้งเตือนสต็อกต่ำ (Min Stock)", min_value=0, value=5, step=1
            )
            p_cat = st.selectbox(
                "หมวดหมู่", ["Software", "Hardware", "Service", "General"]
            )

            if st.form_submit_button("บันทึกสินค้าใหม่", type="primary"):
                if not p_sku.strip() or not p_name.strip():
                    st.error("กรุณาระบุรหัสสินค้าและชื่อสินค้า")
                else:
                    saved_prod = False
                    conn = get_db_connection()
                    try:
                        cursor = conn.cursor()
                        cursor.execute("BEGIN IMMEDIATE")
                        cursor.execute(
                            """INSERT INTO products
                               (sku, name, price, stock, category, min_stock)
                               VALUES (?, ?, ?, ?, ?, ?)""",
                            (
                                p_sku.strip(),
                                p_name.strip(),
                                round(float(p_price), 2),
                                int(p_stock),
                                p_cat,
                                int(p_min_stock),
                            ),
                        )
                        product_id = cursor.lastrowid
                        if int(p_stock) > 0:
                            cursor.execute(
                                """INSERT INTO inventory_movements
                                   (product_id, movement_type, quantity, balance_after,
                                    reference, created_by)
                                   VALUES (?, 'Receipt', ?, ?, 'ยอดตั้งต้น', ?)""",
                                (
                                    product_id,
                                    int(p_stock),
                                    int(p_stock),
                                    st.session_state.user["full_name"],
                                ),
                            )
                        conn.commit()
                        saved_prod = True
                    except sqlite3.IntegrityError:
                        safe_rollback(conn)
                        st.error("รหัสสินค้านี้มีอยู่แล้ว")
                    except sqlite3.Error as error:
                        safe_rollback(conn)
                        st.error(f"บันทึกสินค้าไม่สำเร็จ: {error}")
                    finally:
                        conn.close()

                    if saved_prod:
                        log_audit_action(
                            st.session_state.user["full_name"],
                            f"เพิ่มสินค้า {p_sku.strip()}",
                        )
                        queue_generated_text_input(
                            "product_sku", f"SKU-{uuid.uuid4().hex[:8].upper()}"
                        )
                        st.success("เพิ่มสินค้าเรียบร้อยแล้ว!")
                        st.rerun()

    conn = get_db_connection()
    try:
        df_prod = pd.read_sql_query("SELECT * FROM products ORDER BY name", conn)
    finally:
        conn.close()

    if not df_prod.empty:
        low_df = df_prod[df_prod["stock"].fillna(0) <= df_prod["min_stock"].fillna(10)]
        if not low_df.empty:
            st.warning(f"⚠️ มีสินค้าใกล้หมด {len(low_df)} รายการ กรุณาตรวจสอบและสั่งซื้อเพิ่ม")

    st.dataframe(df_prod, use_container_width=True, hide_index=True)

    if not df_prod.empty:
        stock_options = {
            f"{row.sku} · {row.name} · คงเหลือ {int(row.stock)} ชิ้น": int(row.id)
            for row in df_prod.itertuples()
        }
        st.subheader("🔄 ปรับยอดรับเข้า / เบิกออกสินค้า")
        with st.form("inventory_adjustment_form"):
            selected_product_label = st.selectbox("เลือกสินค้า", list(stock_options))
            movement_type = st.selectbox(
                "ประเภทรายการ",
                ["Receipt", "Issue"],
                format_func=lambda v: "รับเข้า" if v == "Receipt" else "เบิกออก",
            )
            movement_quantity = st.number_input("จำนวน", min_value=1, value=1, step=1)
            movement_reference = st.text_input("เหตุผล / เลขอ้างอิง")
            save_movement = st.form_submit_button(
                "บันทึกการเคลื่อนไหวสต็อก", type="primary"
            )
        if save_movement:
            try:
                updated_stock = adjust_inventory_stock(
                    stock_options[selected_product_label],
                    movement_type,
                    movement_quantity,
                    movement_reference,
                    st.session_state.user["full_name"],
                )
            except (ValueError, sqlite3.Error) as error:
                st.error(str(error))
            else:
                log_audit_action(
                    st.session_state.user["full_name"],
                    f"ปรับสต็อก {selected_product_label} เป็น {updated_stock} ชิ้น",
                )
                st.success(f"บันทึกแล้ว · คงเหลือ {updated_stock} ชิ้น")
                st.rerun()

    conn = get_db_connection()
    try:
        df_movements = pd.read_sql_query(
            """SELECT m.created_at AS 'เวลา', p.sku AS 'SKU', p.name AS 'สินค้า',
                      m.movement_type AS 'ประเภท', m.quantity AS 'จำนวน',
                      m.balance_after AS 'คงเหลือหลังรายการ',
                      m.reference AS 'เหตุผล/เลขอ้างอิง', m.created_by AS 'ผู้บันทึก'
               FROM inventory_movements m
               JOIN products p ON p.id = m.product_id
               ORDER BY m.id DESC LIMIT 1000""",
            conn,
        )
    finally:
        conn.close()
    st.subheader("📋 ประวัติการเคลื่อนไหวสต็อก")
    st.dataframe(df_movements, use_container_width=True, hide_index=True)

# ------------------------------------------------------------------------------
# MODULE 8: HR & PAYROLL
# ------------------------------------------------------------------------------
elif app_menu == "👥 HR & Payroll":
    st.subheader("👥 บริหารทรัพยากรบุคคลและเงินเดือน")

    with st.expander("➕ เพิ่มพนักงานใหม่"):
        with st.form("add_emp_form"):
            e_code = generated_text_input(
                "รหัสพนักงาน",
                "employee_code",
                lambda: f"EMP-{uuid.uuid4().hex[:8].upper()}",
            )
            e_name = st.text_input("ชื่อ-นามสกุล")
            e_pos = st.text_input("ตำแหน่งงาน")
            e_sal = st.number_input(
                "เงินเดือน (บาท)", min_value=0.0, value=30000.0, step=1000.0
            )
            e_dept = st.selectbox(
                "แผนกงาน", ["บริหาร", "บัญชีและการเงิน", "การขาย", "ทรัพยากรบุคคล", "ไอที"]
            )

            if st.form_submit_button("บันทึกพนักงานใหม่", type="primary"):
                if not all(v.strip() for v in (e_code, e_name, e_pos)):
                    st.error("กรุณากรอกรหัส ชื่อ และตำแหน่งพนักงาน")
                else:
                    saved_emp = False
                    conn = get_db_connection()
                    try:
                        conn.execute(
                            """INSERT INTO employees
                               (emp_code, name, position, salary, department)
                               VALUES (?, ?, ?, ?, ?)""",
                            (
                                e_code.strip(),
                                e_name.strip(),
                                e_pos.strip(),
                                round(float(e_sal), 2),
                                e_dept,
                            ),
                        )
                        conn.commit()
                        saved_emp = True
                    except sqlite3.IntegrityError:
                        safe_rollback(conn)
                        st.error("รหัสพนักงานนี้มีอยู่แล้ว")
                    except sqlite3.Error as error:
                        safe_rollback(conn)
                        st.error(f"บันทึกพนักงานไม่สำเร็จ: {error}")
                    finally:
                        conn.close()

                    if saved_emp:
                        log_audit_action(
                            st.session_state.user["full_name"],
                            f"เพิ่มพนักงาน {e_code.strip()}",
                        )
                        queue_generated_text_input(
                            "employee_code", f"EMP-{uuid.uuid4().hex[:8].upper()}"
                        )
                        st.success("เพิ่มข้อมูลพนักงานเรียบร้อยแล้ว!")
                        st.rerun()

    conn = get_db_connection()
    try:
        df_emp = pd.read_sql_query("SELECT * FROM employees ORDER BY emp_code", conn)
    finally:
        conn.close()
    st.dataframe(df_emp, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("💸 จัดการรอบจ่ายเงินเดือน")
    with st.form("create_payroll_run_form"):
        payroll_period = st.text_input(
            "รอบเงินเดือน (YYYY-MM)", value=date.today().strftime("%Y-%m")
        )
        create_payroll = st.form_submit_button("สร้างรอบเงินเดือนแบบร่าง")
    if create_payroll:
        try:
            _, employee_count = create_payroll_run(
                payroll_period, st.session_state.user["full_name"]
            )
        except ValueError as error:
            st.error(str(error))
        except sqlite3.IntegrityError:
            st.error("มีรอบเงินเดือนนี้อยู่แล้ว")
        except sqlite3.Error as error:
            st.error(f"สร้างรอบเงินเดือนไม่สำเร็จ: {error}")
        else:
            log_audit_action(
                st.session_state.user["full_name"],
                f"สร้างรอบเงินเดือน {payroll_period.strip()}",
            )
            st.success(f"สร้างรอบเงินเดือนแล้วสำหรับพนักงาน {employee_count} คน")
            st.rerun()

    conn = get_db_connection()
    try:
        payroll_runs = conn.execute(
            "SELECT id, period, status, created_at FROM payroll_runs ORDER BY period DESC"
        ).fetchall()
    finally:
        conn.close()

    if payroll_runs:
        run_options = {
            f"{row['period']} · {row['status']}": row["id"] for row in payroll_runs
        }
        selected_run_label = st.selectbox(
            "เลือกรอบเงินเดือน", list(run_options), key="selected_payroll_run"
        )
        selected_run_id = run_options[selected_run_label]

        conn = get_db_connection()
        try:
            payroll_items = conn.execute(
                """SELECT pi.employee_id, e.emp_code, e.name,
                          pi.gross_pay, pi.deductions, pi.net_pay
                   FROM payroll_items pi
                   JOIN employees e ON e.id = pi.employee_id
                   WHERE pi.payroll_run_id = ?
                   ORDER BY e.emp_code""",
                (selected_run_id,),
            ).fetchall()
        finally:
            conn.close()

        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "รหัสพนักงาน": row["emp_code"],
                        "ชื่อ": row["name"],
                        "เงินเดือน": row["gross_pay"],
                        "รายการหัก": row["deductions"],
                        "เงินสุทธิ": row["net_pay"],
                    }
                    for row in payroll_items
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )

        if selected_run_label.endswith("· Draft") and payroll_items:
            employee_options = {
                f"{row['emp_code']} · {row['name']}": row for row in payroll_items
            }
            selected_employee_label = st.selectbox(
                "เลือกพนักงานเพื่อแก้ไขยอดหัก",
                list(employee_options),
                key=f"payroll_emp_select_{selected_run_id}",
            )
            selected_employee = employee_options[selected_employee_label]
            gross_val = float(selected_employee["gross_pay"])
            current_ded = min(float(selected_employee["deductions"]), gross_val)

            with st.form("save_payroll_deduction_form"):
                deduction = st.number_input(
                    f"ยอดหัก (ประกันสังคม / ภาษี / อื่นๆ · สูงสุด ฿{gross_val:,.2f})",
                    min_value=0.0,
                    value=current_ded,
                    step=100.0,
                    key=(
                        f"payroll_deduction_{selected_run_id}_"
                        f"{selected_employee['employee_id']}"
                    ),
                )
                save_deduction = st.form_submit_button("บันทึกยอดหัก")
            if save_deduction:
                try:
                    save_payroll_deduction(
                        selected_run_id,
                        selected_employee["employee_id"],
                        deduction,
                    )
                except (ValueError, sqlite3.Error) as error:
                    st.error(str(error))
                else:
                    log_audit_action(
                        st.session_state.user["full_name"],
                        f"บันทึกยอดหักรอบเงินเดือน {selected_run_label}",
                    )
                    st.success("บันทึกยอดหักแล้ว")
                    st.rerun()

            if st.button(
                "ยืนยันจ่ายเงินเดือนและบันทึกบัญชีอัตโนมัติ",
                type="primary",
                key="payroll_run_button",
            ):
                try:
                    net_pay = pay_payroll_run(selected_run_id)
                except (ValueError, sqlite3.Error) as error:
                    st.error(str(error))
                else:
                    log_audit_action(
                        st.session_state.user["full_name"],
                        f"จ่ายเงินเดือนรอบ {selected_run_label} ฿{net_pay:,.2f}",
                    )
                    st.success("จ่ายเงินเดือนและบันทึกบัญชีเรียบร้อยแล้ว")
                    st.rerun()

# ------------------------------------------------------------------------------
# MODULE 9: JOURNAL ENTRIES & FINANCIAL STATEMENTS (GL)
# ------------------------------------------------------------------------------
elif app_menu == "📒 บันทึกบัญชีและงบการเงิน (GL)":
    t_journal, t_tb, t_pl = st.tabs(
        [
            "📒 สมุดรายวันทั่วไป (Journal)",
            "⚖️ งบทดลอง (Trial Balance)",
            "📊 งบกำไรขาดทุนเบื้องต้น (P&L)",
        ]
    )

    conn = get_db_connection()
    try:
        df_j = pd.read_sql_query(
            "SELECT * FROM journal_entries ORDER BY id DESC", conn
        )
    finally:
        conn.close()

    with t_journal:
        with st.form("journal_form"):
            c1, c2 = st.columns(2)
            with c1:
                j_date = st.date_input("วันที่ลงรายการ", date.today())
                j_debit_code = st.text_input("รหัสบัญชีเดบิต", "11100")
                j_debit_name = st.text_input("ชื่อบัญชีเดบิต", "เงินสด/เงินฝากธนาคาร")
            with c2:
                j_amount = st.number_input("จำนวนเงิน (บาท)", min_value=0.01, value=1000.0)
                j_credit_code = st.text_input("รหัสบัญชีเครดิต", "41100")
                j_credit_name = st.text_input("ชื่อบัญชีเครดิต", "รายได้จากการขาย")
            j_desc = st.text_input("คำอธิบายรายการ")

            if st.form_submit_button("บันทึกรายการบัญชีคู่ (Double-Entry)", type="primary"):
                j_amount = round(float(j_amount), 2)
                required_fields = (
                    j_debit_code,
                    j_debit_name,
                    j_credit_code,
                    j_credit_name,
                    j_desc,
                )
                if not all(v.strip() for v in required_fields):
                    st.error("กรุณากรอกบัญชีเดบิต บัญชีเครดิต และคำอธิบายให้ครบ")
                elif j_debit_code.strip() == j_credit_code.strip():
                    st.error("บัญชีเดบิตและเครดิตต้องเป็นคนละบัญชี")
                else:
                    saved_journal = False
                    conn = get_db_connection()
                    try:
                        conn.executemany(
                            """INSERT INTO journal_entries
                               (entry_date, account_code, account_name, debit, credit, description)
                               VALUES (?, ?, ?, ?, ?, ?)""",
                            [
                                (
                                    str(j_date),
                                    j_debit_code.strip(),
                                    j_debit_name.strip(),
                                    j_amount,
                                    0.0,
                                    j_desc.strip(),
                                ),
                                (
                                    str(j_date),
                                    j_credit_code.strip(),
                                    j_credit_name.strip(),
                                    0.0,
                                    j_amount,
                                    j_desc.strip(),
                                ),
                            ],
                        )
                        conn.commit()
                        saved_journal = True
                    except sqlite3.Error as error:
                        safe_rollback(conn)
                        st.error(f"บันทึกรายการบัญชีไม่สำเร็จ: {error}")
                    finally:
                        conn.close()

                    if saved_journal:
                        log_audit_action(
                            st.session_state.user["full_name"],
                            f"บันทึกสมุดรายวัน {j_date} จำนวน ฿{j_amount:,.2f}",
                        )
                        st.success("บันทึกรายการเดบิตและเครดิตที่สมดุลเรียบร้อยแล้ว!")
                        st.rerun()

        st.dataframe(df_j, use_container_width=True, hide_index=True)
        if not df_j.empty:
            st.download_button(
                "⬇️ ดาวน์โหลดสมุดรายวัน (CSV)",
                df_j.to_csv(index=False).encode("utf-8-sig"),
                file_name=f"taxmate_journal_{date.today().isoformat()}.csv",
                mime="text/csv",
            )

    with t_tb:
        if df_j.empty:
            st.info("ยังไม่มีรายการบัญชีสำหรับสรุปงบทดลอง")
        else:
            df_j_clean = df_j.copy()
            df_j_clean["debit"] = df_j_clean["debit"].fillna(0.0)
            df_j_clean["credit"] = df_j_clean["credit"].fillna(0.0)
            tb = (
                df_j_clean.groupby(["account_code", "account_name"], as_index=False)[
                    ["debit", "credit"]
                ]
                .sum()
                .sort_values("account_code")
            )
            tb["net_balance"] = tb["debit"] - tb["credit"]
            total_dr = float(tb["debit"].sum())
            total_cr = float(tb["credit"].sum())

            k1, k2, k3 = st.columns(3)
            k1.metric("รวมเดบิต (Total Debit)", f"฿{total_dr:,.2f}")
            k2.metric("รวมเครดิต (Total Credit)", f"฿{total_cr:,.2f}")
            k3.metric(
                "สถานะงบทดลอง",
                "สมดุล" if math.isclose(total_dr, total_cr, abs_tol=0.01) else "ไม่สมดุล",
            )
            st.dataframe(tb, use_container_width=True, hide_index=True)

    with t_pl:
        if df_j.empty:
            st.info("ยังไม่มีรายการบัญชีสำหรับสรุปงบกำไรขาดทุน")
        else:
            codes = df_j["account_code"].fillna("").astype(str)
            rev_df = df_j[codes.str.startswith("4")]
            exp_df = df_j[codes.str.startswith(("5", "6"))]
            total_revenue = float(
                rev_df["credit"].fillna(0).sum() - rev_df["debit"].fillna(0).sum()
            )
            total_expense = float(
                exp_df["debit"].fillna(0).sum() - exp_df["credit"].fillna(0).sum()
            )
            net_profit = total_revenue - total_expense

            p1, p2, p3 = st.columns(3)
            p1.metric("รายได้รวม (หมวด 4)", f"฿{total_revenue:,.2f}")
            p2.metric("ต้นทุนและค่าใช้จ่ายรวม (หมวด 5-6)", f"฿{total_expense:,.2f}")
            p3.metric("กำไร (ขาดทุน) สุทธิ", f"฿{net_profit:,.2f}")

            pl_chart = pd.DataFrame(
                {
                    "รายการ": ["รายได้รวม", "ค่าใช้จ่ายรวม", "กำไรสุทธิ"],
                    "จำนวนเงิน": [total_revenue, total_expense, net_profit],
                }
            )
            st.plotly_chart(
                px.bar(
                    pl_chart,
                    x="รายการ",
                    y="จำนวนเงิน",
                    title="สรุปงบกำไรขาดทุนเบื้องต้น",
                ),
                use_container_width=True,
            )

# ------------------------------------------------------------------------------
# MODULE 10: E-APPROVAL
# ------------------------------------------------------------------------------
elif app_menu == "🛡️ ระบบขออนุมัติ (E-Approval)":
    st.subheader("🛡️ รายการขออนุมัติจัดซื้อ ค่าใช้จ่าย และเอกสารภายใน")

    with st.form("approval_form"):
        a_type = st.selectbox("ประเภทเอกสาร", ["PO", "EXPENSE", "LEAVE"])
        a_title = st.text_input("เรื่องที่ขออนุมัติ")
        a_amt = st.number_input(
            "จำนวนเงินงบประมาณ (บาท)", min_value=0.01, value=5000.0
        )

        if st.form_submit_button("ส่งคำขออนุมัติ", type="primary"):
            if not a_title.strip():
                st.error("กรุณาระบุเรื่องที่ขออนุมัติ")
            else:
                saved_app = False
                approval_conn = get_db_connection()
                try:
                    approval_conn.execute(
                        """INSERT INTO approvals
                           (doc_type, title, amount, requested_by, status)
                           VALUES (?, ?, ?, ?, 'Pending Approval')""",
                        (
                            a_type,
                            a_title.strip(),
                            round(float(a_amt), 2),
                            st.session_state.user["full_name"],
                        ),
                    )
                    approval_conn.commit()
                    saved_app = True
                except sqlite3.Error as error:
                    safe_rollback(approval_conn)
                    st.error(f"ส่งคำขออนุมัติไม่สำเร็จ: {error}")
                finally:
                    approval_conn.close()

                if saved_app:
                    log_audit_action(
                        st.session_state.user["full_name"],
                        f"ส่งคำขออนุมัติ: {a_title.strip()}",
                    )
                    st.success("ส่งคำขออนุมัติเรียบร้อยแล้ว!")
                    st.rerun()

    conn = get_db_connection()
    try:
        pending_approvals = conn.execute(
            """SELECT id, doc_type, title, amount, requested_by
               FROM approvals WHERE status = 'Pending Approval' ORDER BY id"""
        ).fetchall()
        df_app = pd.read_sql_query(
            "SELECT * FROM approvals ORDER BY id DESC LIMIT 2000", conn
        )
    finally:
        conn.close()

    if pending_approvals:
        approval_options = {
            f"#{row['id']} · {row['doc_type']} · {row['title']} · "
            f"฿{float(row['amount']):,.2f} · {row['requested_by']}": row["id"]
            for row in pending_approvals
        }
        st.subheader("⚖️ พิจารณาคำขอที่รออนุมัติ")
        with st.form("review_approval_form"):
            selected_approval = st.selectbox(
                "เลือกคำขอที่รอดำเนินการ", list(approval_options)
            )
            decision = st.radio(
                "ผลการพิจารณา", ["อนุมัติ", "ปฏิเสธ"], horizontal=True
            )
            review_approval = st.form_submit_button(
                "บันทึกผลการพิจารณา", type="primary"
            )
        if review_approval:
            target_status = "Approved" if decision == "อนุมัติ" else "Rejected"
            try:
                transition_approval(
                    approval_options[selected_approval],
                    target_status,
                    st.session_state.user["full_name"],
                )
            except (ValueError, sqlite3.Error) as error:
                st.error(str(error))
            else:
                log_audit_action(
                    st.session_state.user["full_name"],
                    f"{decision}คำขอ {selected_approval}",
                )
                st.success("บันทึกผลการพิจารณาเรียบร้อยแล้ว")
                st.rerun()
    else:
        st.info("ไม่มีคำขอที่รอการพิจารณา")

    st.dataframe(df_app, use_container_width=True, hide_index=True)

# ------------------------------------------------------------------------------
# MODULE 11: ADMIN SETTINGS & AUDIT LOGS
# ------------------------------------------------------------------------------
elif app_menu == "⚙️ Admin Settings & Audit Logs":
    st.subheader("⚙️ ผู้ใช้งานในระบบและ Audit Trail")
    a1, a2 = st.tabs(["👥 ผู้ใช้งานทั้งหมด", "📜 Audit Logs"])

    conn = get_db_connection()
    try:
        df_u = pd.read_sql_query(
            """SELECT id, username, full_name, role, department, email, status
               FROM users ORDER BY id""",
            conn,
        )
        user_rows = conn.execute(
            """SELECT id, username, full_name, role, status
               FROM users ORDER BY username"""
        ).fetchall()
        df_log = pd.read_sql_query(
            "SELECT * FROM audit_logs ORDER BY id DESC LIMIT 2000", conn
        )
    finally:
        conn.close()

    with a1:
        with st.expander("➕ ลงทะเบียนผู้ใช้งานใหม่", expanded=False):
            with st.form("admin_create_user_form"):
                new_username = st.text_input("ชื่อผู้ใช้", key="admin_new_username")
                new_full_name = st.text_input(
                    "ชื่อ-นามสกุล", key="admin_new_full_name"
                )
                new_email = st.text_input("อีเมล", key="admin_new_email")
                new_department = st.text_input("แผนก", key="admin_new_department")
                new_role = st.selectbox(
                    "บทบาท",
                    ["POS", "Accounting", "HR", "Executive", "Admin"],
                    key="admin_new_role",
                )
                new_status = st.selectbox(
                    "สถานะบัญชี",
                    ["Active", "Pending"],
                    format_func=lambda v: (
                        "เปิดใช้งานทันที" if v == "Active" else "รออนุมัติ"
                    ),
                    key="admin_new_status",
                )
                new_password = st.text_input(
                    "รหัสผ่าน (อย่างน้อย 4 ตัวอักษร)",
                    type="password",
                    key="admin_new_password",
                )
                new_password_confirm = st.text_input(
                    "ยืนยันรหัสผ่าน",
                    type="password",
                    key="admin_new_password_confirm",
                )
                create_user = st.form_submit_button(
                    "ลงทะเบียนผู้ใช้งาน", type="primary"
                )

            if create_user:
                required_fields = (
                    new_username,
                    new_full_name,
                    new_email,
                    new_department,
                )
                if not all(v.strip() for v in required_fields):
                    st.error("กรุณากรอกชื่อผู้ใช้ ชื่อ-นามสกุล อีเมล และแผนกให้ครบ")
                elif len(new_password) < 4:
                    st.error("รหัสผ่านต้องมีอย่างน้อย 4 ตัวอักษร")
                elif new_password != new_password_confirm:
                    st.error("รหัสผ่านและการยืนยันรหัสผ่านไม่ตรงกัน")
                else:
                    created_ok = False
                    create_conn = get_db_connection()
                    try:
                        create_conn.execute("BEGIN IMMEDIATE")
                        create_conn.execute(
                            """INSERT INTO users
                               (username, password_hash, full_name, role, department,
                                email, status)
                               VALUES (?, ?, ?, ?, ?, ?, ?)""",
                            (
                                new_username.strip(),
                                hash_password(new_password),
                                new_full_name.strip(),
                                new_role,
                                new_department.strip(),
                                new_email.strip(),
                                new_status,
                            ),
                        )
                        create_conn.commit()
                        created_ok = True
                    except sqlite3.IntegrityError:
                        safe_rollback(create_conn)
                        st.error("ชื่อผู้ใช้นี้มีอยู่แล้ว")
                    except sqlite3.Error as error:
                        safe_rollback(create_conn)
                        st.error(f"ลงทะเบียนผู้ใช้งานไม่สำเร็จ: {error}")
                    finally:
                        create_conn.close()

                    if created_ok:
                        log_audit_action(
                            current_user["full_name"],
                            f"ลงทะเบียนผู้ใช้ {new_username.strip()} ({new_role}/{new_status})",
                        )
                        st.success(
                            f"ลงทะเบียนผู้ใช้ {new_username.strip()} เรียบร้อยแล้ว"
                        )
                        st.rerun()

        st.subheader("👥 บัญชีผู้ใช้งานทั้งหมด")
        st.dataframe(df_u, use_container_width=True, hide_index=True)

        if user_rows:
            user_options = {
                f"{row['username']} · {row['full_name']} · {row['status']}": row
                for row in user_rows
            }
            selected_user_label = st.selectbox(
                "เลือกบัญชีเพื่อแก้ไขบทบาท สถานะ หรือรหัสผ่าน",
                list(user_options),
                key="admin_user_choice",
            )
            target_user = user_options[selected_user_label]
            role_options = ["Admin", "Executive", "Accounting", "POS", "HR"]
            status_options = ["Active", "Pending", "Inactive"]
            is_self = int(target_user["id"]) == int(current_user["id"])

            with st.form("admin_user_update_form"):
                edit_role = st.selectbox(
                    "บทบาท",
                    role_options,
                    index=(
                        role_options.index(target_user["role"])
                        if target_user["role"] in role_options
                        else 0
                    ),
                    disabled=is_self,
                    key=f"admin_edit_role_{target_user['id']}",
                )
                edit_status = st.selectbox(
                    "สถานะ",
                    status_options,
                    index=(
                        status_options.index(target_user["status"])
                        if target_user["status"] in status_options
                        else 0
                    ),
                    disabled=is_self,
                    key=f"admin_edit_status_{target_user['id']}",
                )
                reset_password = st.text_input(
                    "ตั้งรหัสผ่านใหม่ (เว้นว่างหากไม่เปลี่ยน)",
                    type="password",
                    key=f"admin_reset_password_{target_user['id']}",
                )
                save_user = st.form_submit_button("บันทึกบัญชีผู้ใช้", type="primary")

            if save_user:
                if reset_password and len(reset_password) < 4:
                    st.error("รหัสผ่านใหม่ต้องมีอย่างน้อย 4 ตัวอักษร")
                else:
                    updated_ok = False
                    admin_conn = get_db_connection()
                    try:
                        admin_cursor = admin_conn.cursor()
                        admin_cursor.execute("BEGIN IMMEDIATE")
                        latest_user = admin_cursor.execute(
                            "SELECT role, status FROM users WHERE id = ?",
                            (target_user["id"],),
                        ).fetchone()
                        if not latest_user:
                            raise ValueError("ไม่พบบัญชีผู้ใช้นี้แล้ว")
                        removing_active_admin = (
                            latest_user["role"] in ("Admin", "Super Admin")
                            and latest_user["status"] == "Active"
                            and (edit_role != "Admin" or edit_status != "Active")
                        )
                        if removing_active_admin:
                            active_admin_count = admin_cursor.execute(
                                """SELECT COUNT(*) FROM users
                                   WHERE role IN ('Admin', 'Super Admin')
                                     AND status = 'Active'"""
                            ).fetchone()[0]
                            if active_admin_count <= 1:
                                raise ValueError(
                                    "ไม่สามารถลดสิทธิ์หรือปิดใช้งานผู้ดูแลระบบคนสุดท้ายได้"
                                )
                        if reset_password:
                            admin_cursor.execute(
                                """UPDATE users SET role = ?, status = ?, password_hash = ?
                                   WHERE id = ?""",
                                (
                                    edit_role,
                                    edit_status,
                                    hash_password(reset_password),
                                    target_user["id"],
                                ),
                            )
                        else:
                            admin_cursor.execute(
                                "UPDATE users SET role = ?, status = ? WHERE id = ?",
                                (edit_role, edit_status, target_user["id"]),
                            )
                        admin_conn.commit()
                        updated_ok = True
                    except (ValueError, sqlite3.Error) as error:
                        safe_rollback(admin_conn)
                        st.error(str(error))
                    finally:
                        admin_conn.close()

                    if updated_ok:
                        log_audit_action(
                            current_user["full_name"],
                            f"ปรับบัญชี {target_user['username']} เป็น {edit_role}/{edit_status}",
                        )
                        st.success("บันทึกบัญชีผู้ใช้แล้ว")
                        st.rerun()

    with a2:
        st.dataframe(df_log, use_container_width=True, hide_index=True)
        if not df_log.empty:
            st.download_button(
                "⬇️ ดาวน์โหลด Audit Logs (CSV)",
                df_log.to_csv(index=False).encode("utf-8-sig"),
                file_name=f"taxmate_audit_logs_{date.today().isoformat()}.csv",
                mime="text/csv",
            )

# ------------------------------------------------------------------------------
# MODULE 12: RESET / DELETE DATA MANAGER (FULL + PARTIAL + SINGLE ITEM)
# ------------------------------------------------------------------------------
elif app_menu == "🗑️ ล้างข้อมูลระบบ (Reset Data)":
    st.subheader("🗑️ ศูนย์จัดการและลบข้อมูลในระบบทั้งหมด")
    st.warning("⚠️ การลบข้อมูลจะลบออกจากฐานข้อมูล SQLite ทันทีและไม่สามารถกู้คืนได้")

    counts = get_table_row_counts()
    total_tx_rows = sum(counts[t] for t in ALL_TRANSACTION_TABLES)

    c_sum1, c_sum2, c_sum3 = st.columns(3)
    c_sum1.metric("ข้อมูลธุรกรรมทั้งหมด", f"{total_tx_rows:,} รายการ")
    c_sum2.metric("บัญชีผู้ใช้งาน", f"{counts['users']:,} บัญชี")
    c_sum3.metric("รวมข้อมูลทั้งหมดในระบบ", f"{total_tx_rows + counts['users']:,} รายการ")

    summary_rows = [
        {"ตารางข้อมูล": "ยอดขาย / ใบกำกับภาษี (sales)", "จำนวนรายการ": counts["sales"]},
        {"ตารางข้อมูล": "ประวัติรับชำระเงิน (sales_payments)", "จำนวนรายการ": counts["sales_payments"]},
        {"ตารางข้อมูล": "สินค้าในคลัง (products)", "จำนวนรายการ": counts["products"]},
        {"ตารางข้อมูล": "การเคลื่อนไหวสต็อก (inventory_movements)", "จำนวนรายการ": counts["inventory_movements"]},
        {"ตารางข้อมูล": "ลูกค้า CRM (crm_customers)", "จำนวนรายการ": counts["crm_customers"]},
        {"ตารางข้อมูล": "ใบสั่งซื้อ PO (purchase_orders)", "จำนวนรายการ": counts["purchase_orders"]},
        {"ตารางข้อมูล": "ค่าใช้จ่าย (expenses)", "จำนวนรายการ": counts["expenses"]},
        {"ตารางข้อมูล": "พนักงาน (employees)", "จำนวนรายการ": counts["employees"]},
        {"ตารางข้อมูล": "รอบเงินเดือน (payroll_runs / items)", "จำนวนรายการ": counts["payroll_runs"] + counts["payroll_items"]},
        {"ตารางข้อมูล": "สมุดรายวันบัญชี (journal_entries)", "จำนวนรายการ": counts["journal_entries"]},
        {"ตารางข้อมูล": "รายการขออนุมัติ (approvals)", "จำนวนรายการ": counts["approvals"]},
        {"ตารางข้อมูล": "ประวัติการใช้งาน (audit_logs)", "จำนวนรายการ": counts["audit_logs"]},
        {"ตารางข้อมูล": "บัญชีผู้ใช้งาน (users)", "จำนวนรายการ": counts["users"]},
    ]
    st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)

    st.markdown("---")
    tab_all, tab_partial, tab_single = st.tabs(
        [
            "🔥 ลบข้อมูลทั้งหมดในระบบ",
            "🧹 ลบข้อมูลเฉพาะหมวดหมู่",
            "🎯 ลบข้อมูลทีละรายการ",
        ]
    )

    with tab_all:
        col_tx, col_factory = st.columns(2)

        with col_tx:
            st.markdown("#### 1. ล้างข้อมูลธุรกรรมทั้งหมด (เก็บบัญชีผู้ใช้ไว้)")
            st.caption(
                "ลบยอดขาย สต็อก ลูกค้า ใบสั่งซื้อ ค่าใช้จ่าย พนักงาน เงินเดือน สมุดรายวัน "
                "คำขออนุมัติ และ Audit Logs ทั้งหมด โดยยังเข้าสู่ระบบด้วยบัญชีเดิมได้"
            )
            with st.form("reset_all_transactions_form"):
                confirm_tx_check = st.checkbox(
                    "ยืนยันล้างข้อมูลธุรกรรมทั้งหมดให้เหลือ 0"
                )
                submit_tx_reset = st.form_submit_button(
                    "🧹 ล้างข้อมูลธุรกรรมทั้งหมด", type="primary"
                )
            if submit_tx_reset:
                if not confirm_tx_check:
                    st.error("กรุณาติ๊กถูกเพื่อยืนยันก่อนลบ")
                else:
                    try:
                        deleted_rows, _ = reset_database_tables(
                            ALL_TRANSACTION_TABLES,
                            include_extra_tables=True,
                        )
                    except (ValueError, sqlite3.Error) as error:
                        st.error(f"ล้างข้อมูลไม่สำเร็จ: {error}")
                    else:
                        st.success(
                            f"ล้างข้อมูลธุรกรรมทั้งหมดเรียบร้อยแล้ว ({deleted_rows:,} รายการ)"
                        )
                        st.rerun()

        with col_factory:
            st.markdown("#### 2. ล้างข้อมูลทั้งหมดรวมบัญชีผู้ใช้ (Factory Reset)")
            st.caption(
                "ลบข้อมูลทุกตารางในฐานข้อมูลรวมถึงบัญชีผู้ใช้งานทั้งหมด "
                "ระบบจะออกจากระบบและพาไปหน้าตั้งค่าผู้ดูแลระบบคนแรกใหม่"
            )
            with st.form("factory_reset_form"):
                confirm_factory_check = st.checkbox(
                    "ยืนยันลบข้อมูลและบัญชีผู้ใช้ทั้งหมดอย่างถาวร"
                )
                submit_factory_reset = st.form_submit_button(
                    "🔥 ล้างข้อมูลทั้งหมด (Factory Reset)", type="primary"
                )
            if submit_factory_reset:
                if not confirm_factory_check:
                    st.error("กรุณาติ๊กถูกเพื่อยืนยันก่อนลบ")
                else:
                    try:
                        reset_database_tables(
                            ALL_TRANSACTION_TABLES + ["users"],
                            include_extra_tables=True,
                        )
                    except (ValueError, sqlite3.Error) as error:
                        st.error(f"ล้างข้อมูลทั้งหมดไม่สำเร็จ: {error}")
                    else:
                        st.session_state.clear()
                        st.session_state.authenticated = False
                        st.session_state.user = None
                        st.rerun()

    with tab_partial:
        with st.form("partial_reset_form"):
            selected_groups = st.multiselect(
                "เลือกหมวดข้อมูลที่ต้องการลบ",
                list(RESETTABLE_TABLE_GROUPS.keys()),
            )
            confirm_partial = st.checkbox(
                "ยืนยันการลบข้อมูลในหมวดที่เลือกทั้งหมดอย่างถาวร"
            )
            submit_partial = st.form_submit_button(
                "🗑️ ลบข้อมูลเฉพาะหมวดที่เลือก", type="primary"
            )
        if submit_partial:
            if not selected_groups:
                st.error("กรุณาเลือกอย่างน้อย 1 หมวดข้อมูล")
            elif not confirm_partial:
                st.error("กรุณาติ๊กถูกเพื่อยืนยันการลบข้อมูล")
            else:
                tables_to_clear = []
                for group_name in selected_groups:
                    tables_to_clear.extend(RESETTABLE_TABLE_GROUPS[group_name])
                try:
                    deleted_rows, cleared_tables = reset_database_tables(
                        tables_to_clear,
                        actor=st.session_state.user["full_name"],
                    )
                except (ValueError, sqlite3.Error) as error:
                    st.error(f"ลบข้อมูลไม่สำเร็จ: {error}")
                else:
                    st.success(
                        f"ลบข้อมูลเรียบร้อยแล้ว ({deleted_rows:,} รายการ จาก {len(cleared_tables)} ตาราง)"
                    )
                    st.rerun()

    with tab_single:
        single_delete_config = {
            "🧾 ใบกำกับภาษี (Sales)": (
                "sales",
                "SELECT id, doc_no || ' · ' || customer || ' · ฿' || printf('%.2f', total) AS label FROM sales ORDER BY id DESC",
            ),
            "📦 สินค้า (Products)": (
                "products",
                "SELECT id, sku || ' · ' || name || ' · คงเหลือ ' || stock AS label FROM products ORDER BY id DESC",
            ),
            "🤝 ลูกค้า (CRM)": (
                "crm_customers",
                "SELECT id, cust_code || ' · ' || name || ' · ' || tier AS label FROM crm_customers ORDER BY id DESC",
            ),
            "🛍️ ใบสั่งซื้อ (Purchase Orders)": (
                "purchase_orders",
                "SELECT id, po_no || ' · ' || vendor_name || ' · ' || item_name AS label FROM purchase_orders ORDER BY id DESC",
            ),
            "💸 ค่าใช้จ่าย (Expenses)": (
                "expenses",
                "SELECT id, exp_no || ' · ' || category || ' · ' || description AS label FROM expenses ORDER BY id DESC",
            ),
            "👥 พนักงาน (Employees)": (
                "employees",
                "SELECT id, emp_code || ' · ' || name || ' · ' || position AS label FROM employees ORDER BY id DESC",
            ),
            "📒 สมุดรายวัน (Journal)": (
                "journal_entries",
                "SELECT id, entry_date || ' · ' || account_code || ' ' || account_name || ' · ' || COALESCE(description, '') AS label FROM journal_entries ORDER BY id DESC",
            ),
            "🛡️ คำขออนุมัติ (Approvals)": (
                "approvals",
                "SELECT id, doc_type || ' · ' || title || ' · ' || status AS label FROM approvals ORDER BY id DESC",
            ),
            "👤 บัญชีผู้ใช้งานอื่น (Users)": (
                "users",
                f"SELECT id, username || ' · ' || full_name || ' · ' || role AS label FROM users WHERE id != {int(current_user['id'])} ORDER BY id DESC",
            ),
        }

        chosen_category = st.selectbox(
            "เลือกหมวดหมู่ที่ต้องการลบรายรายการ",
            list(single_delete_config.keys()),
            key="single_delete_category",
        )
        table_key, query_sql = single_delete_config[chosen_category]

        conn = get_db_connection()
        try:
            item_rows = conn.execute(query_sql).fetchall()
        finally:
            conn.close()

        if not item_rows:
            st.info("ไม่มีรายการให้ลบในหมวดนี้")
        else:
            item_map = {
                f"#{row['id']} · {row['label']}": int(row["id"])
                for row in item_rows
            }
            selected_item_label = st.selectbox(
                "เลือกรายการที่ต้องการลบ",
                list(item_map.keys()),
                key=f"single_delete_item_{table_key}",
            )
            if st.button("🗑️ ลบรายการนี้ถาวร", type="primary", key="confirm_single_del"):
                try:
                    delete_single_record(
                        table_key,
                        item_map[selected_item_label],
                        st.session_state.user["full_name"],
                    )
                except (ValueError, sqlite3.Error) as error:
                    st.error(f"ลบรายการไม่สำเร็จ: {error}")
                else:
                    st.success(f"ลบรายการ {selected_item_label} เรียบร้อยแล้ว")
                    st.rerun()