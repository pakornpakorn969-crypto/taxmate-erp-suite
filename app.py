# ==============================================================================
# 🏛️ TaxMate Enterprise ERP Suite v7.0 (All-in-One Single-File Edition)
# ==============================================================================

import hashlib
import hmac
import html
import io
import math
import os
import sqlite3
import tempfile
import uuid
from datetime import date, datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

try:
    import qrcode
    from PIL import Image  # noqa: F401
except ImportError:
    qrcode = None

# ------------------------------------------------------------------------------
# 1. PAGE CONFIG & THEME
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="TaxMate Enterprise ERP Suite v7.0",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Sarabun', 'Inter', -apple-system, sans-serif; }
    .stApp { background-color: #F8FAFC; color: #0F172A; }
    .hero-box {
        background: linear-gradient(135deg, #FFFFFF 0%, #EFF6FF 50%, #DBEAFE 100%);
        border: 1px solid #CBD5E1; border-radius: 24px; padding: 36px 28px;
        text-align: center; margin-bottom: 24px;
        box-shadow: 0 18px 36px -14px rgba(37, 99, 235, 0.14);
    }
    .hero-pill {
        display: inline-block; background: #FFFFFF; color: #2563EB; font-size: 13px;
        font-weight: 800; padding: 6px 20px; border-radius: 9999px;
        border: 1px solid #BFDBFE; margin-bottom: 14px;
    }
    .hero-title { font-size: 36px; font-weight: 800; color: #1E3A8A; margin: 0 0 10px 0; }
    .hero-sub { font-size: 17px; font-weight: 700; color: #2563EB; margin-bottom: 12px; }
    .hero-desc { font-size: 15px; color: #475569; max-width: 860px; margin: 0 auto; line-height: 1.7; }
    .card-3d {
        background: #FFFFFF; border: 1px solid #E2E8F0; padding: 22px; border-radius: 20px;
        box-shadow: 0 8px 20px -6px rgba(0, 0, 0, 0.05); height: 100%;
    }
    .card-3d b { color: #1D4ED8; display: block; margin-bottom: 6px; font-size: 16.5px; }
    .portal-banner {
        background: #FFFFFF; border: 1px solid #E2E8F0; border-left: 6px solid #2563EB;
        border-radius: 16px; padding: 18px 22px; margin-bottom: 18px;
        box-shadow: 0 4px 12px rgba(15, 23, 42, 0.04);
    }
    .badge-admin {
        display: inline-block; background: #DBEAFE; color: #1E40AF; border: 1px solid #93C5FD;
        padding: 4px 12px; border-radius: 9999px; font-size: 12.5px; font-weight: 700; margin-bottom: 8px;
    }
    .badge-user {
        display: inline-block; background: #DCFCE7; color: #166534; border: 1px solid #86EFAC;
        padding: 4px 12px; border-radius: 9999px; font-size: 12.5px; font-weight: 700; margin-bottom: 8px;
    }
    .receipt-paper {
        background: #FFFFFF; border: 2px dashed #94A3B8; padding: 22px; border-radius: 16px;
        font-family: 'Courier New', Courier, monospace; color: #0F172A;
    }
    [data-testid="stMetricValue"] { font-size: 25px !important; font-weight: 800 !important; color: #1E3A8A !important; }
    section[data-testid="stSidebar"] { background-color: #FFFFFF !important; border-right: 1px solid #E2E8F0 !important; }
    .stButton>button, .stFormSubmitButton>button { border-radius: 12px !important; font-weight: 700 !important; min-height: 44px !important; }
    .stButton>button[kind="primary"], .stFormSubmitButton>button[kind="primary"] {
        background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%) !important;
        border: none !important; color: #FFFFFF !important; width: 100%;
    }
</style>
""",
    unsafe_allow_html=True,
)

# ------------------------------------------------------------------------------
# 2. CONSTANTS & DATABASE PATH
# ------------------------------------------------------------------------------
APP_DIR = os.path.dirname(os.path.abspath(__file__))


def resolve_db_path() -> str:
    env_path = os.environ.get("TAXMATE_DB_FILE")
    if env_path:
        path = env_path if os.path.isabs(env_path) else os.path.join(APP_DIR, env_path)
        os.makedirs(os.path.dirname(path) or APP_DIR, exist_ok=True)
        return path
    default_path = os.path.join(APP_DIR, "taxmate_erp_v5.db")
    if os.access(APP_DIR, os.W_OK):
        return default_path
    return os.path.join(tempfile.gettempdir(), "taxmate_erp_v5.db")


DB_FILE = resolve_db_path()

ROLE_LABELS = {
    "Super Admin": "Super Admin (ผู้ดูแลระบบสูงสุด)",
    "Admin": "Admin (ผู้ดูแลระบบ)",
    "User": "User (ผู้ใช้งานทั่วไป)",
    "Executive": "Executive (ผู้บริหาร)",
    "Accounting": "Accounting (ฝ่ายบัญชี)",
    "POS": "POS (ฝ่ายขาย / หน้าร้าน)",
    "HR": "HR (ฝ่ายบุคคล)",
}
REGISTER_ROLES = ["Admin", "User", "Executive", "Accounting", "POS", "HR"]
ADMIN_EDIT_ROLES = ["Super Admin", "Admin", "User", "Executive", "Accounting", "POS", "HR"]
ADMIN_ROLES = {"Admin", "Super Admin"}
APPROVER_ROLES = {"Admin", "Super Admin", "Executive", "Accounting", "HR"}
ALL_ROLES = set(ADMIN_EDIT_ROLES)

RESET_GROUPS = {
    "🧾 ยอดขายและใบกำกับภาษี (Sales & Payments)": ["sales_payments", "sales"],
    "📦 สินค้าและประวัติสต็อก (Products & Inventory)": ["inventory_movements", "products"],
    "🤝 ลูกค้าสัมพันธ์ (CRM & VIP)": ["crm_customers"],
    "🛍️ ใบสั่งซื้อ (Purchase Orders)": ["purchase_orders"],
    "💸 ค่าใช้จ่าย (Expenses)": ["expenses"],
    "👥 พนักงานและรอบเงินเดือน (HR & Payroll)": ["payroll_items", "payroll_runs", "employees"],
    "📒 สมุดรายวันบัญชี (Journal Entries)": ["journal_entries"],
    "🛡️ รายการขออนุมัติ (Approvals)": ["approvals"],
    "📜 ประวัติการใช้งาน (Audit Logs)": ["audit_logs"],
}
ALL_TX_TABLES = [
    "sales_payments", "sales", "inventory_movements", "products",
    "crm_customers", "purchase_orders", "expenses",
    "payroll_items", "payroll_runs", "employees",
    "journal_entries", "approvals", "audit_logs",
]
ALLOWED_RESET_TABLES = set(ALL_TX_TABLES) | {"users"}


# ------------------------------------------------------------------------------
# 3. HELPER & SECURITY FUNCTIONS
# ------------------------------------------------------------------------------
def role_label(code: str) -> str:
    return ROLE_LABELS.get(code, str(code))


def safe_text(val) -> str:
    return html.escape("" if val is None else str(val))


def set_flash(level: str, msg: str):
    st.session_state["_flash"] = (level, msg)


def show_flash():
    flash = st.session_state.pop("_flash", None)
    if not flash:
        return
    level, msg = flash
    getattr(st, level if level in ("success", "warning", "error", "info") else "info")(msg)


def get_conn():
    conn = sqlite3.connect(DB_FILE, timeout=20, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 20000")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def safe_rollback(conn):
    if conn is not None:
        try:
            if conn.in_transaction:
                conn.rollback()
        except sqlite3.Error:
            pass


def table_exists(cur, name: str) -> bool:
    return cur.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def ensure_col(cur, table: str, col: str, decl: str):
    cols = {r["name"] for r in cur.execute(f'PRAGMA table_info("{table}")')}
    if col not in cols:
        cur.execute(f'ALTER TABLE "{table}" ADD COLUMN "{col}" {decl}')


def hash_password(pw: str) -> str:
    salt = os.urandom(16)
    rounds = 260_000
    digest = hashlib.pbkdf2_hmac("sha256", pw.encode("utf-8"), salt, rounds)
    return f"pbkdf2_sha256${rounds}${salt.hex()}${digest.hex()}"


def verify_password(pw: str, stored: str) -> bool:
    if not stored or not isinstance(stored, str):
        return False
    if stored.startswith("pbkdf2_sha256$"):
        try:
            _, rounds, salt_hex, digest_hex = stored.split("$", 3)
            actual = hashlib.pbkdf2_hmac(
                "sha256", pw.encode("utf-8"), bytes.fromhex(salt_hex), int(rounds)
            )
            return hmac.compare_digest(actual.hex(), digest_hex)
        except (ValueError, TypeError):
            return False
    return hmac.compare_digest(hashlib.sha256(pw.encode("utf-8")).hexdigest(), stored)


def gen_input(label: str, key: str, factory):
    pending = f"_pending_{key}"
    if pending in st.session_state:
        st.session_state[key] = st.session_state.pop(pending)
    if key not in st.session_state:
        st.session_state[key] = factory()
    return st.text_input(label, key=key)


def queue_input(key: str, value: str):
    st.session_state[f"_pending_{key}"] = value


def promptpay_payload(target_id: str, amount: float = None) -> str:
    target = str(target_id or "").replace("-", "").replace(" ", "").strip()
    if not target.isdigit() or len(target) not in (10, 13, 15):
        raise ValueError("กรุณาระบุ PromptPay เบอร์มือถือ 10 หลัก เลขประจำตัว 13 หลัก หรือ e-Wallet 15 หลัก")
    if len(target) == 10 and not target.startswith("0"):
        raise ValueError("เบอร์มือถือ PromptPay ต้องขึ้นต้นด้วย 0")
    if amount is not None and (not math.isfinite(float(amount)) or float(amount) <= 0):
        raise ValueError("จำนวนเงิน PromptPay ต้องมากกว่า 0")
    t_type = "01" if len(target) == 10 else ("02" if len(target) == 13 else "03")
    t_fmt = ("0066" + target[1:]) if t_type == "01" else target
    poi = "12" if (amount and float(amount) > 0) else "11"
    tag29 = f"0016A000000677010111{t_type}{len(t_fmt):02d}{t_fmt}"
    payload = f"0002010102{poi}29{len(tag29):02d}{tag29}5303764"
    if amount and float(amount) > 0:
        amt_str = f"{float(amount):.2f}"
        payload += f"54{len(amt_str):02d}{amt_str}"
    payload += "5802TH5911TaxMate ERP6304"
    crc = 0xFFFF
    for ch in payload.encode("ascii"):
        crc ^= ch << 8
        for _ in range(8):
            crc = (((crc << 1) ^ 0x1021) & 0xFFFF) if (crc & 0x8000) else ((crc << 1) & 0xFFFF)
    return payload + f"{crc:04X}"


def qr_png_bytes(payload: str) -> bytes:
    if qrcode is None:
        raise RuntimeError("ยังไม่ได้ติดตั้งแพ็กเกจ qrcode[pil] กรุณาตรวจสอบ requirements.txt")
    buf = io.BytesIO()
    qr = qrcode.QRCode(border=2, box_size=8)
    qr.add_data(payload)
    qr.make(fit=True)
    qr.make_image(fill_color="black", back_color="white").save(buf, format="PNG")
    return buf.getvalue()


# ------------------------------------------------------------------------------
# 4. DATABASE INITIALIZATION & DOMAIN TRANSACTIONS
# ------------------------------------------------------------------------------
def init_db():
    conn = get_conn()
    try:
        try:
            conn.execute("PRAGMA journal_mode = WAL")
        except sqlite3.Error:
            pass
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                role TEXT NOT NULL,
                department TEXT NOT NULL DEFAULT 'ทั่วไป',
                email TEXT,
                status TEXT NOT NULL DEFAULT 'Active',
                allowed_modules TEXT NOT NULL DEFAULT 'all',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
        ensure_col(cur, "users", "department", "TEXT NOT NULL DEFAULT 'ทั่วไป'")
        ensure_col(cur, "users", "email", "TEXT")
        ensure_col(cur, "users", "status", "TEXT NOT NULL DEFAULT 'Active'")
        ensure_col(cur, "users", "allowed_modules", "TEXT NOT NULL DEFAULT 'all'")
        cur.execute("UPDATE users SET status = 'Active' WHERE status IS NULL OR TRIM(status) = ''")

        cur.execute("""
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
            )""")
        ensure_col(cur, "sales", "customer_tax_id", "TEXT")
        ensure_col(cur, "sales", "branch", "TEXT DEFAULT 'สำนักงานใหญ่'")
        ensure_col(cur, "sales", "payment_method", "TEXT DEFAULT 'โอนเงินผ่านธนาคาร'")
        ensure_col(cur, "sales", "created_at", "TIMESTAMP")
        cur.execute("UPDATE sales SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS sales_payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sale_id INTEGER NOT NULL REFERENCES sales(id),
                amount REAL NOT NULL CHECK (amount > 0),
                payment_method TEXT NOT NULL,
                received_by TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sku TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                stock INTEGER NOT NULL,
                category TEXT NOT NULL,
                branch TEXT DEFAULT 'สำนักงานใหญ่',
                min_stock INTEGER DEFAULT 10
            )""")
        ensure_col(cur, "products", "min_stock", "INTEGER DEFAULT 10")
        cur.execute("UPDATE products SET min_stock = 10 WHERE min_stock IS NULL")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS inventory_movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL REFERENCES products(id),
                movement_type TEXT NOT NULL CHECK (movement_type IN ('Receipt', 'Issue')),
                quantity INTEGER NOT NULL CHECK (quantity > 0),
                balance_after INTEGER NOT NULL CHECK (balance_after >= 0),
                reference TEXT NOT NULL,
                created_by TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS crm_customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cust_code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                phone TEXT,
                email TEXT,
                tier TEXT DEFAULT 'Silver',
                points INTEGER DEFAULT 0
            )""")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS purchase_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                po_no TEXT UNIQUE NOT NULL,
                vendor_name TEXT NOT NULL,
                item_name TEXT NOT NULL,
                qty INTEGER NOT NULL,
                total_amount REAL NOT NULL,
                status TEXT DEFAULT 'Pending Approval',
                branch TEXT DEFAULT 'สำนักงานใหญ่',
                requested_by TEXT,
                approved_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
        ensure_col(cur, "purchase_orders", "branch", "TEXT DEFAULT 'สำนักงานใหญ่'")
        ensure_col(cur, "purchase_orders", "requested_by", "TEXT")
        ensure_col(cur, "purchase_orders", "approved_by", "TEXT")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exp_no TEXT UNIQUE NOT NULL,
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                amount REAL NOT NULL,
                approved_by TEXT,
                status TEXT NOT NULL DEFAULT 'Pending Approval',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
        ensure_col(cur, "expenses", "status", "TEXT NOT NULL DEFAULT 'Pending Approval'")
        cur.execute("UPDATE expenses SET status = 'Approved' WHERE status = 'Pending Approval' AND approved_by IS NOT NULL")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                emp_code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                position TEXT NOT NULL,
                salary REAL NOT NULL,
                department TEXT NOT NULL,
                status TEXT DEFAULT 'Active'
            )""")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS payroll_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                period TEXT UNIQUE NOT NULL,
                status TEXT NOT NULL DEFAULT 'Draft',
                created_by TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                paid_at TIMESTAMP
            )""")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS payroll_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                payroll_run_id INTEGER NOT NULL REFERENCES payroll_runs(id),
                employee_id INTEGER NOT NULL REFERENCES employees(id),
                gross_pay REAL NOT NULL CHECK (gross_pay >= 0),
                deductions REAL NOT NULL DEFAULT 0 CHECK (deductions >= 0),
                net_pay REAL NOT NULL CHECK (net_pay >= 0),
                UNIQUE(payroll_run_id, employee_id)
            )""")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS journal_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_date TEXT NOT NULL,
                account_code TEXT NOT NULL,
                account_name TEXT NOT NULL,
                debit REAL DEFAULT 0.0,
                credit REAL DEFAULT 0.0,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")

        cur.execute("""
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
            )""")
        ensure_col(cur, "approvals", "approved_by", "TEXT")
        ensure_col(cur, "approvals", "document_id", "INTEGER")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_name TEXT NOT NULL,
                action TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")

        conn.commit()
    finally:
        conn.close()


def log_audit(user_name: str, action: str):
    conn = get_conn()
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


def get_row_counts() -> dict:
    conn = get_conn()
    try:
        return {
            t: int(conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0])
            for t in ALL_TX_TABLES + ["users"]
        }
    finally:
        conn.close()


def reset_tables(table_names, actor=None, include_extra=False):
    target_set = set(table_names)
    if target_set - ALLOWED_RESET_TABLES:
        raise ValueError("พบตารางที่ไม่ได้รับอนุญาตให้ลบ")
    conn = get_conn()
    try:
        conn.execute("PRAGMA foreign_keys = OFF")
        cur = conn.cursor()
        cur.execute("BEGIN IMMEDIATE")
        if include_extra:
            all_db = [
                r["name"]
                for r in cur.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                ).fetchall()
            ]
            ordered = all_db if "users" in target_set else [t for t in all_db if t != "users"]
        else:
            ordered = [t for t in (ALL_TX_TABLES + ["users"]) if t in target_set and table_exists(cur, t)]
        if not ordered:
            raise ValueError("กรุณาเลือกข้อมูลอย่างน้อย 1 รายการ")
        if "purchase_orders" in target_set and "approvals" not in target_set:
            cur.execute("DELETE FROM approvals WHERE doc_type='PO' AND document_id IS NOT NULL")
        if "expenses" in target_set and "approvals" not in target_set:
            cur.execute("DELETE FROM approvals WHERE doc_type='EXPENSE' AND document_id IS NOT NULL")
        has_seq = table_exists(cur, "sqlite_sequence")
        deleted = 0
        for t in ordered:
            cur.execute(f'DELETE FROM "{t}"')
            deleted += max(cur.rowcount, 0)
            if has_seq:
                cur.execute("DELETE FROM sqlite_sequence WHERE name=?", (t,))
        if actor and "audit_logs" not in target_set and "users" not in target_set:
            cur.execute(
                "INSERT INTO audit_logs (user_name, action) VALUES (?, ?)",
                (str(actor), f"ล้างข้อมูลตาราง: {', '.join(ordered)}"),
            )
        conn.commit()
        return deleted, ordered
    except Exception:
        safe_rollback(conn)
        raise
    finally:
        try:
            conn.execute("PRAGMA foreign_keys = ON")
        except sqlite3.Error:
            pass
        conn.close()


def delete_record(table: str, rec_id: int, actor: str, self_id: int = None):
    allowed = {
        "sales", "products", "crm_customers", "purchase_orders",
        "expenses", "employees", "journal_entries", "approvals", "users",
    }
    if table not in allowed:
        raise ValueError("ไม่สามารถลบข้อมูลจากตารางนี้ได้")
    conn = get_conn()
    try:
        conn.execute("PRAGMA foreign_keys = OFF")
        cur = conn.cursor()
        cur.execute("BEGIN IMMEDIATE")
        if table == "users":
            if self_id is not None and int(rec_id) == int(self_id):
                raise ValueError("ไม่สามารถลบบัญชีที่กำลังใช้งานอยู่ได้")
            t_user = cur.execute("SELECT role, status FROM users WHERE id=?", (rec_id,)).fetchone()
            if not t_user:
                raise ValueError("ไม่พบบัญชีที่ต้องการลบ")
            if t_user["role"] in ADMIN_ROLES and str(t_user["status"]).strip().casefold() == "active":
                cnt = cur.execute(
                    "SELECT COUNT(*) FROM users WHERE role IN ('Admin','Super Admin') AND LOWER(TRIM(status))='active'"
                ).fetchone()[0]
                if cnt <= 1:
                    raise ValueError("ไม่สามารถลบผู้ดูแลระบบที่ใช้งานอยู่คนสุดท้ายได้")
        elif table == "sales":
            cur.execute("DELETE FROM sales_payments WHERE sale_id=?", (rec_id,))
        elif table == "products":
            cur.execute("DELETE FROM inventory_movements WHERE product_id=?", (rec_id,))
        elif table == "employees":
            cur.execute("DELETE FROM payroll_items WHERE employee_id=?", (rec_id,))
        elif table == "purchase_orders":
            cur.execute("DELETE FROM approvals WHERE doc_type='PO' AND document_id=?", (rec_id,))
        elif table == "expenses":
            cur.execute("DELETE FROM approvals WHERE doc_type='EXPENSE' AND document_id=?", (rec_id,))
        cur.execute(f'DELETE FROM "{table}" WHERE id=?', (rec_id,))
        if cur.rowcount != 1:
            raise ValueError("ไม่พบรายการที่ต้องการลบ")
        cur.execute(
            "INSERT INTO audit_logs (user_name, action) VALUES (?, ?)",
            (str(actor), f"ลบรายการ ID #{rec_id} จากตาราง {table}"),
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


def record_payment(sale_id: int, amount: float, method: str, actor: str) -> float:
    amount = round(float(amount), 2)
    if not math.isfinite(amount) or amount <= 0:
        raise ValueError("ยอดรับชำระต้องมากกว่า 0")
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("BEGIN IMMEDIATE")
        sale = cur.execute("SELECT doc_no, total, status FROM sales WHERE id=?", (sale_id,)).fetchone()
        if not sale or sale["status"] == "ชำระแล้ว":
            raise ValueError("ไม่พบเอกสารหรือเอกสารนี้ชำระครบแล้ว")
        paid = float(cur.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM sales_payments WHERE sale_id=?", (sale_id,)
        ).fetchone()[0])
        due = round(float(sale["total"]) - paid, 2)
        if due <= 0:
            raise ValueError("เอกสารนี้ชำระครบแล้ว")
        if amount > due:
            raise ValueError(f"ยอดรับชำระเกินยอดคงค้าง ฿{due:,.2f}")
        cur.execute(
            "INSERT INTO sales_payments (sale_id, amount, payment_method, received_by) VALUES (?,?,?,?)",
            (sale_id, amount, method, actor),
        )
        dr = ("11200", "เงินรับผ่านบัตร") if method == "บัตรเครดิต" else ("11100", "เงินสด/เงินฝากธนาคาร")
        desc = f"รับชำระลูกหนี้ {sale['doc_no']}"
        cur.executemany(
            "INSERT INTO journal_entries (entry_date, account_code, account_name, debit, credit, description) VALUES (?,?,?,?,?,?)",
            [
                (date.today().isoformat(), dr[0], dr[1], amount, 0.0, desc),
                (date.today().isoformat(), "11300", "ลูกหนี้การค้า", 0.0, amount, desc),
            ],
        )
        if round(paid + amount, 2) >= round(float(sale["total"]), 2):
            cur.execute("UPDATE sales SET status='ชำระแล้ว' WHERE id=?", (sale_id,))
        conn.commit()
        return max(round(due - amount, 2), 0.0)
    except Exception:
        safe_rollback(conn)
        raise
    finally:
        conn.close()


def adjust_stock(product_id: int, mv_type: str, qty: int, ref: str, actor: str) -> int:
    if mv_type not in ("Receipt", "Issue"):
        raise ValueError("ประเภทการปรับสต็อกไม่ถูกต้อง")
    qty = int(qty)
    if qty < 1:
        raise ValueError("จำนวนสินค้าต้องมากกว่า 0")
    if not str(ref or "").strip():
        raise ValueError("กรุณาระบุเหตุผลหรือเลขอ้างอิง")
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("BEGIN IMMEDIATE")
        prod = cur.execute("SELECT stock FROM products WHERE id=?", (product_id,)).fetchone()
        if not prod:
            raise ValueError("ไม่พบสินค้าในระบบ")
        curr = int(prod["stock"] or 0)
        if mv_type == "Issue" and qty > curr:
            raise ValueError(f"สต็อกไม่เพียงพอ คงเหลือ {curr} ชิ้น")
        new_stock = curr + qty if mv_type == "Receipt" else curr - qty
        cur.execute("UPDATE products SET stock=? WHERE id=? AND stock=?", (new_stock, product_id, curr))
        if cur.rowcount != 1:
            raise ValueError("สต็อกเปลี่ยนแปลงแล้ว กรุณาลองใหม่")
        cur.execute(
            """INSERT INTO inventory_movements
               (product_id, movement_type, quantity, balance_after, reference, created_by)
               VALUES (?,?,?,?,?,?)""",
            (product_id, mv_type, qty, new_stock, ref.strip(), actor),
        )
        conn.commit()
        return new_stock
    except Exception:
        safe_rollback(conn)
        raise
    finally:
        conn.close()


def process_approval(app_id: int, status: str, actor: str):
    if status not in ("Approved", "Rejected"):
        raise ValueError("สถานะการอนุมัติไม่ถูกต้อง")
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("BEGIN IMMEDIATE")
        row = cur.execute(
            "SELECT doc_type, document_id FROM approvals WHERE id=? AND status='Pending Approval'",
            (app_id,),
        ).fetchone()
        if not row:
            raise ValueError("คำขอนี้ถูกดำเนินการแล้วหรือไม่พบในระบบ")
        cur.execute(
            "UPDATE approvals SET status=?, approved_by=? WHERE id=? AND status='Pending Approval'",
            (status, actor, app_id),
        )
        if row["doc_type"] == "PO" and row["document_id"] is not None:
            cur.execute(
                "UPDATE purchase_orders SET status=?, approved_by=? WHERE id=? AND status IN ('Pending Approval','Pending')",
                (status, actor, row["document_id"]),
            )
        elif row["doc_type"] == "EXPENSE" and row["document_id"] is not None:
            exp = cur.execute(
                "SELECT category, description, amount FROM expenses WHERE id=? AND status='Pending Approval'",
                (row["document_id"],),
            ).fetchone()
            if exp:
                cur.execute(
                    "UPDATE expenses SET status=?, approved_by=CASE WHEN ?='Approved' THEN ? ELSE NULL END WHERE id=?",
                    (status, status, actor, row["document_id"]),
                )
                if status == "Approved":
                    desc = f"รับรู้ค่าใช้จ่าย {exp['description']}"
                    cur.executemany(
                        "INSERT INTO journal_entries (entry_date, account_code, account_name, debit, credit, description) VALUES (?,?,?,?,?,?)",
                        [
                            (date.today().isoformat(), "61000", f"ค่าใช้จ่าย - {exp['category']}", float(exp["amount"]), 0.0, desc),
                            (date.today().isoformat(), "21100", "เจ้าหนี้ค่าใช้จ่าย", 0.0, float(exp["amount"]), desc),
                        ],
                    )
        conn.commit()
    except Exception:
        safe_rollback(conn)
        raise
    finally:
        conn.close()


def create_payroll(period: str, actor: str):
    cleaned = str(period or "").strip()
    try:
        parsed = datetime.strptime(cleaned, "%Y-%m")
        if parsed.strftime("%Y-%m") != cleaned:
            raise ValueError()
    except ValueError:
        raise ValueError("กรุณาระบุรอบเงินเดือนเป็นรูปแบบ YYYY-MM (เช่น 2026-11)") from None
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("BEGIN IMMEDIATE")
        cur.execute("INSERT INTO payroll_runs (period, created_by) VALUES (?,?)", (cleaned, actor))
        run_id = cur.lastrowid
        emps = cur.execute("SELECT id, salary FROM employees WHERE status='Active'").fetchall()
        if not emps:
            raise ValueError("ไม่มีพนักงานที่ใช้งานอยู่สำหรับรอบเงินเดือนนี้")
        cur.executemany(
            "INSERT INTO payroll_items (payroll_run_id, employee_id, gross_pay, deductions, net_pay) VALUES (?,?,?,0,?)",
            [(run_id, e["id"], round(float(e["salary"]), 2), round(float(e["salary"]), 2)) for e in emps],
        )
        conn.commit()
        return run_id, len(emps)
    except Exception:
        safe_rollback(conn)
        raise
    finally:
        conn.close()


def update_payroll_deduction(run_id: int, emp_id: int, deduction: float):
    ded = round(float(deduction), 2)
    if not math.isfinite(ded) or ded < 0:
        raise ValueError("ยอดหักต้องไม่ติดลบ")
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("BEGIN IMMEDIATE")
        run = cur.execute("SELECT status FROM payroll_runs WHERE id=?", (run_id,)).fetchone()
        item = cur.execute(
            "SELECT id, gross_pay FROM payroll_items WHERE payroll_run_id=? AND employee_id=?",
            (run_id, emp_id),
        ).fetchone()
        if not run or run["status"] != "Draft" or not item:
            raise ValueError("ไม่พบรายการเงินเดือนแบบร่างนี้")
        gross = float(item["gross_pay"])
        if ded > gross:
            raise ValueError(f"ยอดหักต้องไม่เกินเงินเดือนก่อนหัก ฿{gross:,.2f}")
        cur.execute(
            "UPDATE payroll_items SET deductions=?, net_pay=? WHERE id=?",
            (ded, round(gross - ded, 2), item["id"]),
        )
        conn.commit()
    except Exception:
        safe_rollback(conn)
        raise
    finally:
        conn.close()


def pay_payroll(run_id: int) -> float:
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("BEGIN IMMEDIATE")
        run = cur.execute("SELECT period, status FROM payroll_runs WHERE id=?", (run_id,)).fetchone()
        if not run or run["status"] != "Draft":
            raise ValueError("รอบเงินเดือนนี้ถูกจ่ายไปแล้วหรือไม่พบในระบบ")
        cnt, gross, ded, net = cur.execute(
            "SELECT COUNT(*), COALESCE(SUM(gross_pay),0), COALESCE(SUM(deductions),0), COALESCE(SUM(net_pay),0) FROM payroll_items WHERE payroll_run_id=?",
            (run_id,),
        ).fetchone()
        gross, ded, net = float(gross), float(ded), float(net)
        if cnt == 0:
            raise ValueError("ไม่มีรายการพนักงานในรอบเงินเดือนนี้")
        today_s = date.today().isoformat()
        entries = []
        if gross > 0:
            entries.append((today_s, "51000", "ค่าใช้จ่ายเงินเดือน", gross, 0.0, f"เงินเดือนรอบ {run['period']}"))
        if net > 0:
            entries.append((today_s, "11100", "เงินสด/เงินฝากธนาคาร", 0.0, net, f"จ่ายเงินเดือนรอบ {run['period']}"))
        if ded > 0:
            entries.append((today_s, "21400", "หนี้สินรายการหักเงินเดือน", 0.0, ded, f"ตั้งหนี้สินรายการหัก {run['period']}"))
        if entries:
            cur.executemany(
                "INSERT INTO journal_entries (entry_date, account_code, account_name, debit, credit, description) VALUES (?,?,?,?,?,?)",
                entries,
            )
        cur.execute(
            "UPDATE payroll_runs SET status='Paid', paid_at=CURRENT_TIMESTAMP WHERE id=? AND status='Draft'",
            (run_id,),
        )
        conn.commit()
        return net
    except Exception:
        safe_rollback(conn)
        raise
    finally:
        conn.close()


# Initialize database once per session
if not st.session_state.get("_db_ready") or not os.path.exists(DB_FILE):
    try:
        init_db()
        st.session_state["_db_ready"] = True
    except (sqlite3.Error, ValueError) as err:
        st.error(f"ไม่สามารถเตรียมฐานข้อมูลได้: {err}")
        st.stop()

# ------------------------------------------------------------------------------
# 5. AUTHENTICATION & LANDING PAGE
# ------------------------------------------------------------------------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user = None

if not st.session_state.authenticated or not st.session_state.user:
    st.session_state.authenticated = False
    st.session_state.user = None

    conn = get_conn()
    try:
        user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    finally:
        conn.close()

    if user_count == 0:
        show_flash()
        st.markdown("## 🛡️ ตั้งค่าผู้ดูแลระบบคนแรก (Initial Admin Setup)")
        st.info("สร้างบัญชี Admin คนแรกเพื่อเริ่มต้นใช้งาน TaxMate ERP v7.0")
        with st.form("init_admin_form"):
            u0 = st.text_input("ชื่อผู้ดูแลระบบ (Username)")
            fn0 = st.text_input("ชื่อ-นามสกุล")
            em0 = st.text_input("อีเมล")
            p0 = st.text_input("รหัสผ่าน (อย่างน้อย 4 ตัวอักษร)", type="password")
            p0c = st.text_input("ยืนยันรหัสผ่าน", type="password")
            sub0 = st.form_submit_button("สร้างบัญชีผู้ดูแลระบบ (Admin)", type="primary")
        if sub0:
            if not all(v.strip() for v in (u0, fn0, em0)):
                st.error("กรุณากรอกข้อมูลให้ครบทุกช่อง")
            elif len(p0) < 4:
                st.error("รหัสผ่านต้องมีอย่างน้อย 4 ตัวอักษร")
            elif p0 != p0c:
                st.error("รหัสผ่านและยืนยันรหัสผ่านไม่ตรงกัน")
            else:
                created = None
                conn = get_conn()
                try:
                    conn.execute("BEGIN IMMEDIATE")
                    if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]:
                        raise ValueError("มีบัญชีผู้ใช้แล้ว กรุณาเข้าสู่ระบบ")
                    conn.execute(
                        "INSERT INTO users (username, password_hash, full_name, role, department, email, status) VALUES (?,?,?,'Admin','บริหารและจัดการ',?,'Active')",
                        (u0.strip(), hash_password(p0), fn0.strip(), em0.strip()),
                    )
                    conn.commit()
                    created = dict(conn.execute("SELECT * FROM users WHERE username=?", (u0.strip(),)).fetchone())
                except (ValueError, sqlite3.Error) as err:
                    safe_rollback(conn)
                    st.error(f"สร้างบัญชีไม่สำเร็จ: {err}")
                finally:
                    conn.close()
                if created:
                    st.session_state.authenticated = True
                    st.session_state.user = created
                    log_audit(fn0.strip(), "สร้างบัญชีผู้ดูแลระบบเริ่มต้น")
                    set_flash("success", "สร้างบัญชีผู้ดูแลระบบเรียบร้อยแล้ว ยินดีต้อนรับ!")
                    st.rerun()
        st.stop()

    with st.sidebar:
        st.markdown("### 🏛️ TaxMate ERP v7.0")
        init_nav = st.radio("📍 เมนูระบบ:", ["🔑 เข้าสู่ระบบ / สมัครสมาชิก", "🏠 หน้าแรก (Overview)"])
        st.divider()
        st.caption("🟢 ฐานข้อมูล SQLite พร้อมใช้งาน")

    show_flash()

    if init_nav == "🏠 หน้าแรก (Overview)":
        st.markdown(
            """
        <div class="hero-box">
            <span class="hero-pill">🏛️ ALL-IN-ONE ENTERPRISE ERP v7.0</span>
            <div class="hero-title">TaxMate Enterprise ERP Suite</div>
            <div class="hero-sub">Admin Center • User Portal • e-Tax • Accounting • WMS • HR</div>
            <div class="hero-desc">ระบบบริหารจัดการองค์กรครบวงจร รองรับการแยกหน้าผู้ดูแลระบบ (Admin Center) และหน้าผู้ใช้งานทั่วไป (User Portal) พร้อมใบกำกับภาษี VAT 7% Dynamic PromptPay QR สต็อกสินค้า CRM จัดซื้อ ค่าใช้จ่าย เงินเดือน และลงบัญชีคู่ครบถ้วน</div>
        </div>
        """,
            unsafe_allow_html=True,
        )
        c1, c2, c3 = st.columns(3)
        c1.markdown('<div class="card-3d"><b>🛡️ Admin Center & User Portal</b>แยกหน้าผู้ดูแลระบบและหน้าผู้ใช้งานชัดเจน จัดการสิทธิ์ โปรไฟล์ รหัสผ่าน และประวัติการใช้งาน</div>', unsafe_allow_html=True)
        c2.markdown('<div class="card-3d"><b>🧾 e-Tax & Dynamic PromptPay QR</b>ออกใบกำกับภาษี VAT 7% ตัวอย่างใบเสร็จสด พร้อมระบบรับชำระหนี้และสร้าง QR Code ทันที</div>', unsafe_allow_html=True)
        c3.markdown('<div class="card-3d"><b>📊 GL, CRM, WMS & Payroll</b>ลงบัญชีคู่ งบทดลอง งบกำไรขาดทุน สต็อกสินค้าแจ้งเตือนของใกล้หมด และรอบเงินเดือนครบวงจร</div>', unsafe_allow_html=True)
    else:
        st.markdown("## 🔑 ศูนย์ยืนยันตัวตน (Admin & User Login)")
        t_in, t_up = st.tabs(["🔑 เข้าสู่ระบบ (Sign In)", "📝 ลงทะเบียนบัญชี Admin / User (Sign Up)"])

        with t_in:
            st.info("เข้าสู่ระบบได้ทั้งบัญชี **Admin** และ **User** ระบบจะเปิดหน้าให้ตรงกับสิทธิ์โดยอัตโนมัติ")
            with st.form("login_form"):
                u_in = st.text_input("ชื่อผู้ใช้งาน (Username)")
                p_in = st.text_input("รหัสผ่าน (Password)", type="password")
                if st.form_submit_button("เข้าสู่ระบบ", type="primary"):
                    conn = get_conn()
                    try:
                        found = conn.execute("SELECT * FROM users WHERE username=?", (u_in.strip(),)).fetchone()
                    finally:
                        conn.close()
                    if found and verify_password(p_in, found["password_hash"]):
                        if str(found["status"] or "").strip().casefold() != "active":
                            st.error(f"บัญชีนี้อยู่ในสถานะ '{found['status']}' กรุณาติดต่อผู้ดูแลระบบ")
                        else:
                            st.session_state.authenticated = True
                            st.session_state.user = dict(found)
                            log_audit(found["full_name"], "เข้าสู่ระบบสำเร็จ")
                            set_flash("success", f"ยินดีต้อนรับคุณ {found['full_name']} ({role_label(found['role'])})")
                            st.rerun()
                    else:
                        st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")

        with t_up:
            st.info("เลือกสร้างบัญชี **Admin (ผู้ดูแลระบบ)** หรือ **User (ผู้ใช้งานทั่วไป)** เพื่อเข้าใช้งานได้ทันที")
            with st.form("signup_form"):
                ru = st.text_input("Username:")
                rfn = st.text_input("ชื่อ-นามสกุล:")
                rem = st.text_input("อีเมล:")
                rdept = st.text_input("แผนก (Department):", value="ทั่วไป")
                rrole = st.selectbox("บทบาท (Role):", REGISTER_ROLES, index=1, format_func=role_label)
                rp1 = st.text_input("รหัสผ่าน (อย่างน้อย 4 ตัวอักษร):", type="password")
                rp2 = st.text_input("ยืนยันรหัสผ่าน (กรอกให้ตรงกับด้านบน):", type="password")
                if st.form_submit_button("สร้างบัญชีใหม่", type="primary"):
                    if not ru.strip() or not rfn.strip() or not rem.strip():
                        st.error("กรุณากรอก Username ชื่อ-นามสกุล และอีเมลให้ครบ")
                    elif len(rp1) < 4:
                        st.error("รหัสผ่านต้องมีอย่างน้อย 4 ตัวอักษร")
                    elif rp1 != rp2:
                        st.error("รหัสผ่านและการยืนยันรหัสผ่านไม่ตรงกัน กรุณากรอกให้เหมือนกันทั้ง 2 ช่อง")
                    else:
                        ok = False
                        conn = get_conn()
                        try:
                            conn.execute(
                                "INSERT INTO users (username, password_hash, full_name, role, department, email, status) VALUES (?,?,?,?,?,?,'Active')",
                                (ru.strip(), hash_password(rp1), rfn.strip(), rrole, rdept.strip() or "ทั่วไป", rem.strip()),
                            )
                            conn.commit()
                            ok = True
                        except sqlite3.IntegrityError:
                            safe_rollback(conn)
                            st.error("ชื่อผู้ใช้นี้มีอยู่แล้ว")
                        except sqlite3.Error as err:
                            safe_rollback(conn)
                            st.error(f"สร้างบัญชีไม่สำเร็จ: {err}")
                        finally:
                            conn.close()
                        if ok:
                            log_audit(rfn.strip(), f"สมัครบัญชีใหม่: {ru.strip()} ({rrole})")
                            st.success(f"สร้างบัญชี {ru.strip()} ({role_label(rrole)}) เรียบร้อยแล้ว! สลับไปแท็บ 'เข้าสู่ระบบ' เพื่อล็อกอินได้เลย")
    st.stop()

# ------------------------------------------------------------------------------
# 6. LOGGED-IN SESSION & ROLE NAVIGATION
# ------------------------------------------------------------------------------
conn = get_conn()
try:
    fetched = conn.execute("SELECT * FROM users WHERE id=?", (st.session_state.user.get("id"),)).fetchone()
finally:
    conn.close()

if not fetched or str(fetched["status"] or "").strip().casefold() != "active":
    st.session_state.clear()
    st.session_state.authenticated = False
    st.session_state.user = None
    set_flash("error", "บัญชีถูกปิดใช้งานหรือถูกลบ กรุณาเข้าสู่ระบบใหม่")
    st.rerun()

user = dict(fetched)
st.session_state.user = user
user_role = user.get("role", "User")
is_admin = user_role in ADMIN_ROLES

st.sidebar.title("🏛️ TaxMate ERP Suite")
st.sidebar.markdown(
    '<span class="badge-admin">🛡️ โหมดผู้ดูแลระบบ (Admin)</span>'
    if is_admin
    else '<span class="badge-user">👤 โหมดผู้ใช้งาน (User)</span>',
    unsafe_allow_html=True,
)
st.sidebar.markdown(f"👤 **{safe_text(user['full_name'])}**")
st.sidebar.caption(f"Role: `{safe_text(user_role)}` | Dept: `{safe_text(user['department'])}`")
st.sidebar.markdown("---")

if is_admin:
    menu_perms = {
        "🛡️ หน้าผู้ดูแลระบบ (Admin Center)": ADMIN_ROLES,
        "👤 หน้าผู้ใช้งาน (User Portal)": ALL_ROLES,
        "📊 Dashboard Overview": ALL_ROLES,
        "🧾 e-Tax Invoice & Dynamic QR": ALL_ROLES,
        "🤝 ระบบลูกค้าสัมพันธ์ (CRM & VIP)": ALL_ROLES,
        "📈 คาดการณ์ทางการเงิน (Forecast)": {"Admin", "Super Admin", "Executive", "Accounting"},
        "🛍️ จัดซื้อและคู่ค้า (Purchase Orders)": ALL_ROLES,
        "💸 คุมงบประมาณและค่าใช้จ่าย (Expenses)": ALL_ROLES,
        "📦 Smart Inventory WMS": ALL_ROLES,
        "👥 HR & Payroll": {"Admin", "Super Admin", "HR"},
        "📒 บันทึกบัญชีและงบการเงิน (GL)": {"Admin", "Super Admin", "Accounting"},
        "🛡️ ระบบขออนุมัติ (E-Approval)": ALL_ROLES,
        "🗑️ ล้างข้อมูลระบบ (Reset Data)": ADMIN_ROLES,
    }
else:
    menu_perms = {
        "👤 หน้าผู้ใช้งาน (User Portal)": ALL_ROLES,
        "📊 Dashboard Overview": ALL_ROLES,
        "🧾 e-Tax Invoice & Dynamic QR": {"User", "Executive", "Accounting", "POS"},
        "🤝 ระบบลูกค้าสัมพันธ์ (CRM & VIP)": {"User", "Executive", "Accounting", "POS"},
        "📈 คาดการณ์ทางการเงิน (Forecast)": {"Executive", "Accounting"},
        "🛍️ จัดซื้อและคู่ค้า (Purchase Orders)": {"User", "Executive", "Accounting"},
        "💸 คุมงบประมาณและค่าใช้จ่าย (Expenses)": {"User", "Executive", "Accounting"},
        "📦 Smart Inventory WMS": {"User", "Accounting", "POS"},
        "👥 HR & Payroll": {"HR"},
        "📒 บันทึกบัญชีและงบการเงิน (GL)": {"Accounting"},
        "🛡️ ระบบขออนุมัติ (E-Approval)": ALL_ROLES,
    }

avail_menus = [m for m, r in menu_perms.items() if user_role in r] or ["👤 หน้าผู้ใช้งาน (User Portal)"]
app_menu = st.sidebar.radio("ระบบงานหลัก", avail_menus)

st.sidebar.markdown("---")
if st.sidebar.button("🚪 ออกจากระบบ", use_container_width=True):
    log_audit(user["full_name"], "ออกจากระบบ")
    st.session_state.clear()
    st.session_state.authenticated = False
    st.session_state.user = None
    st.rerun()

st.title(app_menu)
show_flash()

# ------------------------------------------------------------------------------
# MODULE: USER PORTAL
# ------------------------------------------------------------------------------
if app_menu == "👤 หน้าผู้ใช้งาน (User Portal)":
    st.markdown(
        f"""<div class="portal-banner">
        <h3 style="margin:0 0 6px 0; color:#1E3A8A;">👋 ยินดีต้อนรับ, {safe_text(user['full_name'])}</h3>
        <p style="margin:0; color:#475569;">บัญชี: <b>{safe_text(user['username'])}</b> | บทบาท: <b>{safe_text(role_label(user['role']))}</b> | แผนก: <b>{safe_text(user['department'] or '-')}</b> | อีเมล: <b>{safe_text(user['email'] or '-')}</b></p>
        </div>""",
        unsafe_allow_html=True,
    )
    conn = get_conn()
    try:
        my_app = pd.read_sql_query(
            "SELECT id, doc_type AS 'ประเภท', title AS 'เรื่อง', amount AS 'งบประมาณ', status AS 'สถานะ', approved_by AS 'ผู้อนุมัติ', created_at AS 'วันที่ส่ง' FROM approvals WHERE requested_by=? ORDER BY id DESC LIMIT 200",
            conn, params=(user["full_name"],),
        )
        my_log = pd.read_sql_query(
            "SELECT timestamp AS 'เวลา', action AS 'กิจกรรม' FROM audit_logs WHERE user_name=? ORDER BY id DESC LIMIT 200",
            conn, params=(user["full_name"],),
        )
    finally:
        conn.close()

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("คำขอทั้งหมดของฉัน", f"{len(my_app)} รายการ")
    k2.metric("รออนุมัติ", f"{int((my_app['สถานะ']=='Pending Approval').sum()) if not my_app.empty else 0} รายการ")
    k3.metric("อนุมัติแล้ว", f"{int((my_app['สถานะ']=='Approved').sum()) if not my_app.empty else 0} รายการ")
    k4.metric("กิจกรรมล่าสุด", f"{len(my_log)} รายการ")

    ut1, ut2, ut3 = st.tabs(["👤 โปรไฟล์และเปลี่ยนรหัสผ่าน", "📝 คำขออนุมัติของฉัน", "📜 ประวัติของฉัน"])
    with ut1:
        c_p, c_pw = st.columns(2)
        with c_p:
            st.subheader("✏️ แก้ไขข้อมูลส่วนตัว")
            with st.form("u_prof_form"):
                efn = st.text_input("ชื่อ-นามสกุล", value=str(user["full_name"] or ""))
                eem = st.text_input("อีเมล", value=str(user["email"] or ""))
                edept = st.text_input("แผนก", value=str(user["department"] or ""))
                if st.form_submit_button("💾 บันทึกข้อมูลส่วนตัว", type="primary"):
                    if not efn.strip() or not eem.strip():
                        st.error("กรุณากรอกชื่อ-นามสกุลและอีเมลให้ครบ")
                    else:
                        old_n, new_n = str(user["full_name"] or ""), efn.strip()
                        ok = False
                        conn = get_conn()
                        try:
                            cur = conn.cursor()
                            cur.execute("BEGIN IMMEDIATE")
                            cur.execute("UPDATE users SET full_name=?, email=?, department=? WHERE id=?", (new_n, eem.strip(), edept.strip() or "ทั่วไป", int(user["id"])))
                            if old_n and old_n != new_n:
                                cur.execute("UPDATE approvals SET requested_by=? WHERE requested_by=?", (new_n, old_n))
                                cur.execute("UPDATE purchase_orders SET requested_by=? WHERE requested_by=?", (new_n, old_n))
                                cur.execute("UPDATE audit_logs SET user_name=? WHERE user_name=?", (new_n, old_n))
                            conn.commit()
                            ok = True
                        except sqlite3.Error as err:
                            safe_rollback(conn)
                            st.error(f"อัปเดตไม่สำเร็จ: {err}")
                        finally:
                            conn.close()
                        if ok:
                            log_audit(new_n, "อัปเดตข้อมูลโปรไฟล์ส่วนตัว")
                            set_flash("success", "บันทึกข้อมูลส่วนตัวเรียบร้อยแล้ว")
                            st.rerun()
        with c_pw:
            st.subheader("🔒 เปลี่ยนรหัสผ่าน")
            with st.form("u_pw_form"):
                cpw = st.text_input("รหัสผ่านปัจจุบัน", type="password")
                npw = st.text_input("รหัสผ่านใหม่ (อย่างน้อย 4 ตัวอักษร)", type="password")
                npwc = st.text_input("ยืนยันรหัสผ่านใหม่", type="password")
                if st.form_submit_button("🔑 เปลี่ยนรหัสผ่าน", type="primary"):
                    if not verify_password(cpw, user["password_hash"]):
                        st.error("รหัสผ่านปัจจุบันไม่ถูกต้อง")
                    elif len(npw) < 4:
                        st.error("รหัสผ่านใหม่ต้องมีอย่างน้อย 4 ตัวอักษร")
                    elif npw != npwc:
                        st.error("รหัสผ่านใหม่ไม่ตรงกัน")
                    else:
                        conn = get_conn()
                        try:
                            conn.execute("UPDATE users SET password_hash=? WHERE id=?", (hash_password(npw), int(user["id"])))
                            conn.commit()
                        finally:
                            conn.close()
                        log_audit(user["full_name"], "เปลี่ยนรหัสผ่านบัญชีตนเอง")
                        set_flash("success", "เปลี่ยนรหัสผ่านเรียบร้อยแล้ว")
                        st.rerun()

    with ut2:
        with st.form("u_qa_form"):
            q1, q2 = st.columns([1, 2])
            with q1:
                qt = st.selectbox("ประเภทคำขอ", ["LEAVE", "EXPENSE", "PO"])
                qa = st.number_input("จำนวนเงิน (บาท · ลางานใส่ 0)", min_value=0.0, value=0.0, step=100.0)
            with q2:
                qtitle = st.text_input("รายละเอียดคำขอ", placeholder="เช่น ขอลากิจ 1 วัน / ขอเบิกค่าเดินทาง")
            if st.form_submit_button("ส่งคำขออนุมัติ", type="primary"):
                if not qtitle.strip():
                    st.error("กรุณาระบุรายละเอียดคำขอ")
                else:
                    conn = get_conn()
                    try:
                        conn.execute(
                            "INSERT INTO approvals (doc_type, title, amount, requested_by, status) VALUES (?,?,?,?,'Pending Approval')",
                            (qt, qtitle.strip(), round(float(qa), 2), user["full_name"]),
                        )
                        conn.commit()
                    finally:
                        conn.close()
                    log_audit(user["full_name"], f"ส่งคำขอจาก User Portal: {qtitle.strip()}")
                    set_flash("success", "ส่งคำขออนุมัติเรียบร้อยแล้ว")
                    st.rerun()
        st.dataframe(my_app, use_container_width=True, hide_index=True)

    with ut3:
        st.dataframe(my_log, use_container_width=True, hide_index=True)

# ------------------------------------------------------------------------------
# MODULE: ADMIN CENTER
# ------------------------------------------------------------------------------
elif app_menu == "🛡️ หน้าผู้ดูแลระบบ (Admin Center)":
    conn = get_conn()
    try:
        df_u = pd.read_sql_query("SELECT id, username, full_name, role, department, email, status, created_at FROM users ORDER BY id", conn)
        u_rows = conn.execute("SELECT id, username, full_name, role, status FROM users ORDER BY username").fetchall()
        df_log = pd.read_sql_query("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 2000", conn)
        pend_cnt = conn.execute("SELECT COUNT(*) FROM approvals WHERE status='Pending Approval'").fetchone()[0]
    finally:
        conn.close()

    adm_cnt = int(df_u["role"].isin(["Admin", "Super Admin"]).sum()) if not df_u.empty else 0
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("บัญชีทั้งหมด", f"{len(df_u)} บัญชี")
    k2.metric("ผู้ดูแลระบบ (Admin)", f"{adm_cnt} บัญชี")
    k3.metric("ผู้ใช้งานทั่วไป", f"{len(df_u) - adm_cnt} บัญชี")
    k4.metric("คำขอรออนุมัติ", f"{pend_cnt} รายการ")

    a1, a2 = st.tabs(["👥 จัดการบัญชี Admin & User", "📜 Audit Logs"])
    with a1:
        with st.expander("➕ สร้างบัญชี Admin / User ใหม่"):
            with st.form("adm_new_user"):
                nu = st.text_input("Username")
                nfn = st.text_input("ชื่อ-นามสกุล")
                nem = st.text_input("อีเมล")
                ndept = st.text_input("แผนก", value="ทั่วไป")
                nrole = st.selectbox("บทบาท", REGISTER_ROLES, index=1, format_func=role_label)
                nstat = st.selectbox("สถานะ", ["Active", "Pending"], format_func=lambda v: "เปิดใช้งานทันที" if v == "Active" else "รออนุมัติ")
                np1 = st.text_input("รหัสผ่าน (อย่างน้อย 4 ตัวอักษร)", type="password")
                np2 = st.text_input("ยืนยันรหัสผ่าน", type="password")
                if st.form_submit_button("ลงทะเบียนผู้ใช้งาน", type="primary"):
                    if not all(v.strip() for v in (nu, nfn, nem, ndept)):
                        st.error("กรุณากรอกข้อมูลให้ครบ")
                    elif len(np1) < 4:
                        st.error("รหัสผ่านต้องมีอย่างน้อย 4 ตัวอักษร")
                    elif np1 != np2:
                        st.error("รหัสผ่านไม่ตรงกัน")
                    else:
                        ok = False
                        conn = get_conn()
                        try:
                            conn.execute(
                                "INSERT INTO users (username, password_hash, full_name, role, department, email, status) VALUES (?,?,?,?,?,?,?)",
                                (nu.strip(), hash_password(np1), nfn.strip(), nrole, ndept.strip(), nem.strip(), nstat),
                            )
                            conn.commit()
                            ok = True
                        except sqlite3.IntegrityError:
                            safe_rollback(conn)
                            st.error("ชื่อผู้ใช้นี้มีอยู่แล้ว")
                        except sqlite3.Error as err:
                            safe_rollback(conn)
                            st.error(f"ลงทะเบียนไม่สำเร็จ: {err}")
                        finally:
                            conn.close()
                        if ok:
                            log_audit(user["full_name"], f"สร้างบัญชี {nu.strip()} ({nrole}/{nstat})")
                            set_flash("success", f"ลงทะเบียน {nu.strip()} เรียบร้อยแล้ว")
                            st.rerun()

        st.dataframe(df_u, use_container_width=True, hide_index=True)
        if u_rows:
            u_opts = {f"{r['username']} · {r['full_name']} · {r['role']} · {r['status']}": r for r in u_rows}
            sel_u = u_opts[st.selectbox("เลือกบัญชีเพื่อแก้ไข", list(u_opts), key="adm_sel_u")]
            is_self = int(sel_u["id"]) == int(user["id"])
            st_opts = ["Active", "Pending", "Inactive"]
            with st.form("adm_edit_u"):
                erole = st.selectbox("บทบาท", ADMIN_EDIT_ROLES, index=ADMIN_EDIT_ROLES.index(sel_u["role"]) if sel_u["role"] in ADMIN_EDIT_ROLES else 2, format_func=role_label, disabled=is_self, key=f"er_{sel_u['id']}")
                estat = st.selectbox("สถานะ", st_opts, index=st_opts.index(sel_u["status"]) if sel_u["status"] in st_opts else 0, disabled=is_self, key=f"es_{sel_u['id']}")
                rpw = st.text_input("ตั้งรหัสผ่านใหม่ (เว้นว่างหากไม่เปลี่ยน)", type="password", key=f"ep_{sel_u['id']}")
                if st.form_submit_button("บันทึกบัญชีผู้ใช้", type="primary"):
                    if rpw and len(rpw) < 4:
                        st.error("รหัสผ่านใหม่ต้องมีอย่างน้อย 4 ตัวอักษร")
                    else:
                        ok = False
                        conn = get_conn()
                        try:
                            cur = conn.cursor()
                            cur.execute("BEGIN IMMEDIATE")
                            lat = cur.execute("SELECT role, status FROM users WHERE id=?", (sel_u["id"],)).fetchone()
                            if not lat:
                                raise ValueError("ไม่พบบัญชีนี้แล้ว")
                            f_role = lat["role"] if is_self else erole
                            f_stat = lat["status"] if is_self else estat
                            if lat["role"] in ADMIN_ROLES and str(lat["status"]).strip().casefold() == "active" and (f_role not in ADMIN_ROLES or f_stat != "Active"):
                                if cur.execute("SELECT COUNT(*) FROM users WHERE role IN ('Admin','Super Admin') AND LOWER(TRIM(status))='active'").fetchone()[0] <= 1:
                                    raise ValueError("ไม่สามารถลดสิทธิ์หรือปิดใช้งานผู้ดูแลระบบคนสุดท้ายได้")
                            if rpw:
                                cur.execute("UPDATE users SET role=?, status=?, password_hash=? WHERE id=?", (f_role, f_stat, hash_password(rpw), sel_u["id"]))
                            else:
                                cur.execute("UPDATE users SET role=?, status=? WHERE id=?", (f_role, f_stat, sel_u["id"]))
                            conn.commit()
                            ok = True
                        except (ValueError, sqlite3.Error) as err:
                            safe_rollback(conn)
                            st.error(str(err))
                        finally:
                            conn.close()
                        if ok:
                            log_audit(user["full_name"], f"แก้ไขบัญชี {sel_u['username']} -> {f_role}/{f_stat}")
                            set_flash("success", "บันทึกบัญชีผู้ใช้เรียบร้อยแล้ว")
                            st.rerun()

    with a2:
        st.dataframe(df_log, use_container_width=True, hide_index=True)
        if not df_log.empty:
            st.download_button("⬇️ ดาวน์โหลด Audit Logs (CSV)", df_log.to_csv(index=False).encode("utf-8-sig"), f"taxmate_audit_{date.today().isoformat()}.csv", "text/csv")

# ------------------------------------------------------------------------------
# MODULE: DASHBOARD OVERVIEW
# ------------------------------------------------------------------------------
elif app_menu == "📊 Dashboard Overview":
    conn = get_conn()
    try:
        df_s = pd.read_sql_query("SELECT * FROM sales", conn)
        df_p = pd.read_sql_query("SELECT * FROM products", conn)
        df_e = pd.read_sql_query("SELECT * FROM expenses WHERE status='Approved'", conn)
        pend = conn.execute("SELECT COUNT(*) FROM approvals WHERE status='Pending Approval'").fetchone()[0]
    finally:
        conn.close()

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("ยอดขายรวมสุทธิ", f"฿{float(df_s['total'].fillna(0).sum()) if not df_s.empty else 0:,.2f}")
    m2.metric("ภาษีขาย VAT 7%", f"฿{float(df_s['tax'].fillna(0).sum()) if not df_s.empty else 0:,.2f}")
    m3.metric("ค่าใช้จ่ายอนุมัติแล้ว", f"฿{float(df_e['amount'].fillna(0).sum()) if not df_e.empty else 0:,.2f}")
    m4.metric("สินค้าในสต็อก", f"{int(df_p['stock'].fillna(0).sum()) if not df_p.empty else 0:,} ชิ้น")
    m5.metric("รออนุมัติ", f"{pend} รายการ")

    if not df_p.empty:
        p_chk = df_p.copy()
        p_chk["stock"] = p_chk["stock"].fillna(0).astype(int)
        p_chk["min_stock"] = p_chk["min_stock"].fillna(10).astype(int)
        low = p_chk[p_chk["stock"] <= p_chk["min_stock"]]
        if not low.empty:
            st.warning(f"⚠️ สินค้าต่ำกว่าเกณฑ์ {len(low)} รายการ: " + ", ".join(f"{r.name} (เหลือ {int(r.stock)})" for r in low.itertuples()))

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📈 แนวโน้มรายได้ และภาษี VAT")
        if not df_s.empty:
            cs = df_s.copy()
            cs["amount"] = cs["amount"].fillna(0.0)
            cs["tax"] = cs["tax"].fillna(0.0)
            st.plotly_chart(px.bar(cs, x="doc_no", y=["amount", "tax"], barmode="stack", title="มูลค่าก่อน VAT และภาษีขาย"), use_container_width=True)
        else:
            st.info("ยังไม่มีข้อมูลการขาย")
    with c2:
        st.subheader("📊 สัดส่วนสถานะการชำระเงิน")
        if not df_s.empty:
            ss = df_s.assign(status=df_s["status"].fillna("ไม่ระบุ"), total=df_s["total"].fillna(0.0)).groupby("status", as_index=False)["total"].sum()
            ss = ss[ss["total"] > 0]
            if not ss.empty:
                st.plotly_chart(px.pie(ss, names="status", values="total", hole=0.4), use_container_width=True)
            else:
                st.info("ยังไม่มีข้อมูลยอดชำระเงิน")
        else:
            st.info("ยังไม่มีข้อมูลสถานะการชำระเงิน")

# ------------------------------------------------------------------------------
# MODULE: E-TAX INVOICE & DYNAMIC QR
# ------------------------------------------------------------------------------
elif app_menu == "🧾 e-Tax Invoice & Dynamic QR":
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📝 ออกใบกำกับภาษีใหม่")
        d_no = gen_input("เลขที่เอกสาร", "etax_doc_no", lambda: f"INV-{date.today():%Y%m%d}-{uuid.uuid4().hex[:8].upper()}")
        cust = st.text_input("ชื่อลูกค้า / นิติบุคคล", value="บริษัท สยามเทคโนโลยี จำกัด", key="etax_cust")
        tax_id = st.text_input("เลขประจำตัวผู้เสียภาษีลูกค้า (ไม่บังคับ)", placeholder="เช่น 0105551234567", key="etax_tid")
        amt = round(float(st.number_input("มูลค่าสินค้า/บริการ (บาท)", min_value=0.01, value=10000.0, step=500.0, key="etax_amt")), 2)
        pm = st.selectbox("ช่องทางชำระเงิน", ["โอนเงินผ่านธนาคาร", "PromptPay", "บัตรเครดิต", "เงินสด"], key="etax_pm")
        pp_id = st.text_input("PromptPay เบอร์มือถือ / เลขผู้เสียภาษี", placeholder="เช่น 0812345678", key="etax_pp") if pm == "PromptPay" else ""
        st_val = st.selectbox("สถานะ", ["ชำระแล้ว", "รอชำระ"], index=1, key="etax_st")
        vat, tot = round(amt * 0.07, 2), round(amt * 1.07, 2)

        if st.button("💾 บันทึกและออกใบกำกับภาษี", type="primary", use_container_width=True):
            valid = True
            if not d_no.strip() or not cust.strip():
                st.error("กรุณาระบุเลขที่เอกสารและชื่อลูกค้า")
                valid = False
            elif pm == "PromptPay":
                try:
                    promptpay_payload(pp_id, tot)
                except ValueError as err:
                    st.error(str(err))
                    valid = False
            if valid:
                ok = False
                conn = get_conn()
                try:
                    cur = conn.cursor()
                    cur.execute("BEGIN IMMEDIATE")
                    cur.execute(
                        "INSERT INTO sales (doc_no, customer, customer_tax_id, amount, tax, total, status, payment_method) VALUES (?,?,?,?,?,?,?,?)",
                        (d_no.strip(), cust.strip(), tax_id.strip() or None, amt, vat, tot, st_val, pm),
                    )
                    sid = cur.lastrowid
                    if st_val != "ชำระแล้ว":
                        dr = ("11300", "ลูกหนี้การค้า")
                    elif pm == "บัตรเครดิต":
                        dr = ("11200", "เงินรับผ่านบัตร")
                    else:
                        dr = ("11100", "เงินสด/เงินฝากธนาคาร")
                    if st_val == "ชำระแล้ว":
                        cur.execute("INSERT INTO sales_payments (sale_id, amount, payment_method, received_by) VALUES (?,?,?,?)", (sid, tot, pm, user["full_name"]))
                    cur.executemany(
                        "INSERT INTO journal_entries (entry_date, account_code, account_name, debit, credit, description) VALUES (?,?,?,?,?,?)",
                        [
                            (date.today().isoformat(), dr[0], dr[1], tot, 0.0, f"รับรู้ยอดขาย {d_no.strip()}"),
                            (date.today().isoformat(), "41100", "รายได้จากการขาย", 0.0, amt, f"รับรู้ยอดขาย {d_no.strip()}"),
                            (date.today().isoformat(), "21300", "ภาษีขาย", 0.0, vat, f"ภาษีขาย 7% {d_no.strip()}"),
                        ],
                    )
                    conn.commit()
                    ok = True
                except sqlite3.IntegrityError:
                    safe_rollback(conn)
                    st.error("เลขที่เอกสารนี้มีอยู่แล้ว")
                except sqlite3.Error as err:
                    safe_rollback(conn)
                    st.error(f"บันทึกไม่สำเร็จ: {err}")
                finally:
                    conn.close()
                if ok:
                    log_audit(user["full_name"], f"ออกใบกำกับภาษี {d_no.strip()}")
                    queue_input("etax_doc_no", f"INV-{date.today():%Y%m%d}-{uuid.uuid4().hex[:8].upper()}")
                    set_flash("success", f"บันทึกเอกสาร {d_no.strip()} เรียบร้อยแล้ว!")
                    st.rerun()

    with c2:
        st.subheader("🧾 ตัวอย่างเอกสาร (Live Preview)")
        st.markdown(
            f"""<div class="receipt-paper">
            <h3 style="text-align:center; margin-bottom:4px;">ใบกำกับภาษี / ใบเสร็จรับเงิน</h3>
            <p style="text-align:center; font-size:12px; color:#64748B;">TAX INVOICE / RECEIPT</p><hr>
            <p><b>เลขที่:</b> {safe_text(d_no)}</p>
            <p><b>ลูกค้า:</b> {safe_text(cust)}</p>
            <p><b>เลขผู้เสียภาษี:</b> {safe_text(tax_id.strip() or '-')}</p>
            <p><b>ช่องทางชำระ:</b> {safe_text(pm)}</p><hr>
            <p><b>มูลค่าก่อน VAT:</b> ฿{amt:,.2f}</p>
            <p><b>ภาษี VAT 7%:</b> ฿{vat:,.2f}</p>
            <h4 style="color:#2563EB;">ยอดรวมสุทธิ: ฿{tot:,.2f}</h4>
            </div>""",
            unsafe_allow_html=True,
        )
        if pm == "PromptPay" and pp_id.strip():
            try:
                st.subheader("💳 Dynamic PromptPay QR Code")
                st.image(qr_png_bytes(promptpay_payload(pp_id, tot)), caption=f"สแกนชำระเงิน ฿{tot:,.2f}", width=250)
            except (ValueError, RuntimeError) as err:
                st.error(str(err))
        elif pm == "PromptPay":
            st.info("กรอกเบอร์มือถือหรือเลขผู้เสียภาษีด้านซ้ายเพื่อสร้าง PromptPay QR Code ทันที")

    st.markdown("---")
    conn = get_conn()
    try:
        df_sales = pd.read_sql_query("SELECT doc_no, customer, customer_tax_id, amount, tax, total, status, payment_method, created_at FROM sales ORDER BY id DESC", conn)
        open_rows = conn.execute(
            """SELECT s.id, s.doc_no, s.customer, s.total, COALESCE(p.paid,0) AS paid
               FROM sales s LEFT JOIN (SELECT sale_id, SUM(amount) AS paid FROM sales_payments GROUP BY sale_id) p ON p.sale_id=s.id
               WHERE s.status != 'ชำระแล้ว' AND ROUND(s.total - COALESCE(p.paid,0), 2) >= 0.01 ORDER BY s.id DESC"""
        ).fetchall()
    finally:
        conn.close()

    st.subheader("📋 รายการใบกำกับภาษีในระบบ")
    st.dataframe(df_sales, use_container_width=True, hide_index=True)
    if not df_sales.empty:
        st.download_button("⬇️ ดาวน์โหลดรายงานขาย (CSV)", df_sales.to_csv(index=False).encode("utf-8-sig"), f"taxmate_sales_{date.today().isoformat()}.csv", "text/csv")

    if open_rows:
        st.subheader("💳 รับชำระใบแจ้งหนี้ค้างรับ")
        s_opts = {f"{r['doc_no']} · {r['customer']} · ค้าง ฿{round(float(r['total'])-float(r['paid']),2):,.2f}": r for r in open_rows}
        sel_s = s_opts[st.selectbox("เลือกเอกสารค้างชำระ", list(s_opts), key="ar_sel")]
        due = round(float(sel_s["total"]) - float(sel_s["paid"]), 2)
        with st.form("ar_pay_form"):
            rm = st.selectbox("ช่องทางรับชำระ", ["เงินสด", "โอนเงินผ่านธนาคาร", "บัตรเครดิต", "PromptPay"])
            ra = st.number_input(f"ยอดรับชำระ (ยอดคงค้าง ฿{due:,.2f})", min_value=0.01, value=due, key=f"ar_{sel_s['id']}_{due:.2f}")
            if st.form_submit_button("บันทึกรับชำระ", type="primary"):
                try:
                    rem_due = record_payment(sel_s["id"], ra, rm, user["full_name"])
                except (ValueError, sqlite3.Error) as err:
                    st.error(str(err))
                else:
                    log_audit(user["full_name"], f"รับชำระ {sel_s['doc_no']} ฿{ra:,.2f}")
                    set_flash("success", f"รับชำระเรียบร้อย · ยอดคงค้าง ฿{rem_due:,.2f}")
                    st.rerun()

# ------------------------------------------------------------------------------
# MODULE: CRM & VIP
# ------------------------------------------------------------------------------
elif app_menu == "🤝 ระบบลูกค้าสัมพันธ์ (CRM & VIP)":
    c1, c2 = st.columns([1.2, 1])
    with c1:
        with st.expander("➕ ลงทะเบียนลูกค้าใหม่", expanded=True):
            with st.form("crm_form"):
                cc = gen_input("รหัสลูกค้า", "crm_code", lambda: f"CUST-{uuid.uuid4().hex[:8].upper()}")
                cn = st.text_input("ชื่อบริษัท / คุณลูกค้า")
                cp = st.text_input("เบอร์โทรศัพท์")
                ce = st.text_input("อีเมล")
                ct = st.selectbox("ระดับสิทธิประโยชน์ (Tier)", ["Silver", "Gold", "Platinum", "Diamond"])
                cpt = st.number_input("คะแนนสะสมเริ่มต้น", min_value=0, value=100, step=50)
                if st.form_submit_button("บันทึกข้อมูลลูกค้า", type="primary"):
                    if not cc.strip() or not cn.strip():
                        st.error("กรุณาระบุรหัสและชื่อลูกค้า")
                    else:
                        ok = False
                        conn = get_conn()
                        try:
                            conn.execute("INSERT INTO crm_customers (cust_code, name, phone, email, tier, points) VALUES (?,?,?,?,?,?)", (cc.strip(), cn.strip(), cp.strip(), ce.strip(), ct, int(cpt)))
                            conn.commit()
                            ok = True
                        except sqlite3.IntegrityError:
                            safe_rollback(conn)
                            st.error("รหัสลูกค้านี้มีอยู่แล้ว")
                        finally:
                            conn.close()
                        if ok:
                            log_audit(user["full_name"], f"เพิ่มลูกค้า {cn.strip()}")
                            queue_input("crm_code", f"CUST-{uuid.uuid4().hex[:8].upper()}")
                            set_flash("success", "บันทึกข้อมูลลูกค้าเรียบร้อยแล้ว!")
                            st.rerun()
    conn = get_conn()
    try:
        df_crm = pd.read_sql_query("SELECT * FROM crm_customers ORDER BY id DESC", conn)
    finally:
        conn.close()
    with c2:
        if not df_crm.empty:
            tc = df_crm["tier"].fillna("Silver").value_counts().reset_index()
            tc.columns = ["tier", "count"]
            st.plotly_chart(px.pie(tc, names="tier", values="count", title="สัดส่วนระดับสมาชิกลูกค้า", hole=0.35), use_container_width=True)
        else:
            st.info("ยังไม่มีข้อมูลลูกค้า")
    st.dataframe(df_crm, use_container_width=True, hide_index=True)

# ------------------------------------------------------------------------------
# MODULE: FINANCIAL FORECAST
# ------------------------------------------------------------------------------
elif app_menu == "📈 คาดการณ์ทางการเงิน (Forecast)":
    conn = get_conn()
    try:
        df_fc = pd.read_sql_query(
            "SELECT COALESCE(strftime('%Y-%m', created_at), strftime('%Y-%m','now')) AS period, SUM(total) AS total FROM sales GROUP BY 1 ORDER BY 1",
            conn,
        )
    finally:
        conn.close()
    rev_sum = float(df_fc["total"].fillna(0).sum()) if not df_fc.empty else 0.0
    base = float(df_fc["total"].fillna(0).tail(3).mean()) if not df_fc.empty else 0.0
    f1, f2, f3 = st.columns(3)
    f1.metric("รายได้สะสม", f"฿{rev_sum:,.2f}")
    f2.metric("ฐานเฉลี่ยเดือนล่าสุด (สูงสุด 3 เดือน)", f"฿{base:,.2f}")
    f3.metric("จำนวนเดือนที่มีข้อมูล", f"{len(df_fc)} เดือน")

    if df_fc.empty:
        st.info("ยังไม่มีข้อมูลยอดขายสำหรับคำนวณประมาณการ")
    else:
        g = st.slider("สมมติฐานอัตราเติบโตต่อเดือน (%)", -20, 30, 0, 1)
        today = date.today()
        months, vals = [], []
        for i in range(1, 7):
            mi = today.month - 1 + i
            months.append(f"{today.year + mi // 12:04d}-{mi % 12 + 1:02d}")
            vals.append(round(base * ((1 + g / 100.0) ** i), 2))
        fig = go.Figure(go.Scatter(x=months, y=vals, mode="lines+markers", line=dict(color="#2563EB", width=4)))
        fig.update_layout(title=f"ประมาณการยอดขาย 6 เดือน (เติบโต {g:+d}%/เดือน)", xaxis_title="เดือน", yaxis_title="บาท")
        st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------------------------
# MODULE: PURCHASE ORDERS
# ------------------------------------------------------------------------------
elif app_menu == "🛍️ จัดซื้อและคู่ค้า (Purchase Orders)":
    with st.expander("➕ สร้างใบสั่งซื้อ (PO) ใหม่", expanded=True):
        with st.form("po_form"):
            po_no = gen_input("เลขที่ PO", "po_no", lambda: f"PO-{date.today():%Y%m%d}-{uuid.uuid4().hex[:8].upper()}")
            vn = st.text_input("ชื่อซัพพลายเออร์ / คู่ค้า", "บริษัท ซัพพลายฮับ จำกัด")
            iname = st.text_input("รายการสินค้า / บริการ")
            qty = st.number_input("จำนวน", min_value=1, value=1, step=1)
            tp = st.number_input("ราคารวม (บาท)", min_value=0.01, value=10000.0, step=1000.0)
            if st.form_submit_button("ส่งใบสั่งซื้อขออนุมัติ (PO)", type="primary"):
                if not all(v.strip() for v in (po_no, vn, iname)):
                    st.error("กรุณากรอกข้อมูลให้ครบ")
                else:
                    ok = False
                    conn = get_conn()
                    try:
                        cur = conn.cursor()
                        cur.execute("BEGIN IMMEDIATE")
                        cur.execute(
                            "INSERT INTO purchase_orders (po_no, vendor_name, item_name, qty, total_amount, status, requested_by) VALUES (?,?,?,?,?,'Pending Approval',?)",
                            (po_no.strip(), vn.strip(), iname.strip(), int(qty), round(float(tp), 2), user["full_name"]),
                        )
                        cur.execute(
                            "INSERT INTO approvals (doc_type, title, amount, requested_by, status, document_id) VALUES ('PO',?,?,?,'Pending Approval',?)",
                            (f"{po_no.strip()} · {vn.strip()} · {iname.strip()}", round(float(tp), 2), user["full_name"], cur.lastrowid),
                        )
                        conn.commit()
                        ok = True
                    except sqlite3.IntegrityError:
                        safe_rollback(conn)
                        st.error("เลขที่ PO นี้มีอยู่แล้ว")
                    finally:
                        conn.close()
                    if ok:
                        log_audit(user["full_name"], f"สร้าง PO {po_no.strip()}")
                        queue_input("po_no", f"PO-{date.today():%Y%m%d}-{uuid.uuid4().hex[:8].upper()}")
                        set_flash("success", f"บันทึก PO {po_no.strip()} และส่งขออนุมัติแล้ว!")
                        st.rerun()
    conn = get_conn()
    try:
        df_po = pd.read_sql_query("SELECT * FROM purchase_orders ORDER BY id DESC", conn)
    finally:
        conn.close()
    st.dataframe(df_po, use_container_width=True, hide_index=True)

# ------------------------------------------------------------------------------
# MODULE: EXPENSES
# ------------------------------------------------------------------------------
elif app_menu == "💸 คุมงบประมาณและค่าใช้จ่าย (Expenses)":
    c1, c2 = st.columns(2)
    with c1:
        with st.form("exp_form"):
            eno = gen_input("เลขที่ใบสำคัญจ่าย", "exp_no", lambda: f"EXP-{date.today():%Y%m%d}-{uuid.uuid4().hex[:8].upper()}")
            ecat = st.selectbox("หมวดหมู่", ["ค่าสาธารณูปโภค", "ค่าการตลาด", "ค่าเช่าสถานที่", "อุปกรณ์สำนักงาน", "อื่นๆ"])
            edesc = st.text_input("รายละเอียดค่าใช้จ่าย")
            eamt = st.number_input("จำนวนเงิน (บาท)", min_value=0.01, value=1000.0, step=100.0)
            if st.form_submit_button("บันทึกและส่งขออนุมัติค่าใช้จ่าย", type="primary"):
                if not eno.strip() or not edesc.strip():
                    st.error("กรุณาระบุเลขที่และรายละเอียด")
                else:
                    ok = False
                    conn = get_conn()
                    try:
                        cur = conn.cursor()
                        cur.execute("BEGIN IMMEDIATE")
                        cur.execute(
                            "INSERT INTO expenses (exp_no, category, description, amount, approved_by, status) VALUES (?,?,?,?,NULL,'Pending Approval')",
                            (eno.strip(), ecat, edesc.strip(), round(float(eamt), 2)),
                        )
                        cur.execute(
                            "INSERT INTO approvals (doc_type, title, amount, requested_by, status, document_id) VALUES ('EXPENSE',?,?,?,'Pending Approval',?)",
                            (f"{eno.strip()} · {ecat} · {edesc.strip()}", round(float(eamt), 2), user["full_name"], cur.lastrowid),
                        )
                        conn.commit()
                        ok = True
                    except sqlite3.IntegrityError:
                        safe_rollback(conn)
                        st.error("เลขที่ใบสำคัญจ่ายนี้มีอยู่แล้ว")
                    finally:
                        conn.close()
                    if ok:
                        log_audit(user["full_name"], f"บันทึกค่าใช้จ่าย {eno.strip()}")
                        queue_input("exp_no", f"EXP-{date.today():%Y%m%d}-{uuid.uuid4().hex[:8].upper()}")
                        set_flash("success", f"บันทึกค่าใช้จ่าย {eno.strip()} และส่งขออนุมัติแล้ว!")
                        st.rerun()
    conn = get_conn()
    try:
        df_exp = pd.read_sql_query("SELECT * FROM expenses ORDER BY id DESC", conn)
    finally:
        conn.close()
    with c2:
        if not df_exp.empty:
            es = df_exp.assign(category=df_exp["category"].fillna("อื่นๆ"), amount=df_exp["amount"].fillna(0.0)).groupby("category", as_index=False)["amount"].sum()
            es = es[es["amount"] > 0]
            if not es.empty:
                st.plotly_chart(px.pie(es, names="category", values="amount", title="สัดส่วนค่าใช้จ่ายตามหมวดหมู่", hole=0.35), use_container_width=True)
        else:
            st.info("ยังไม่มีข้อมูลค่าใช้จ่าย")
    st.dataframe(df_exp, use_container_width=True, hide_index=True)

# ------------------------------------------------------------------------------
# MODULE: SMART INVENTORY WMS
# ------------------------------------------------------------------------------
elif app_menu == "📦 Smart Inventory WMS":
    with st.expander("➕ เพิ่มรายการสินค้าใหม่"):
        with st.form("prod_form"):
            psku = gen_input("รหัสสินค้า (SKU)", "prod_sku", lambda: f"SKU-{uuid.uuid4().hex[:8].upper()}")
            pname = st.text_input("ชื่อสินค้า")
            pprice = st.number_input("ราคาขาย (บาท)", min_value=0.0, value=1000.0)
            pstock = st.number_input("สต็อกเริ่มต้น", min_value=0, value=10, step=1)
            pmin = st.number_input("จุดแจ้งเตือนสต็อกต่ำ", min_value=0, value=5, step=1)
            pcat = st.selectbox("หมวดหมู่", ["Software", "Hardware", "Service", "General"])
            if st.form_submit_button("บันทึกสินค้าใหม่", type="primary"):
                if not psku.strip() or not pname.strip():
                    st.error("กรุณาระบุรหัสและชื่อสินค้า")
                else:
                    ok = False
                    conn = get_conn()
                    try:
                        cur = conn.cursor()
                        cur.execute("BEGIN IMMEDIATE")
                        cur.execute("INSERT INTO products (sku, name, price, stock, category, min_stock) VALUES (?,?,?,?,?,?)", (psku.strip(), pname.strip(), round(float(pprice), 2), int(pstock), pcat, int(pmin)))
                        if int(pstock) > 0:
                            cur.execute(
                                "INSERT INTO inventory_movements (product_id, movement_type, quantity, balance_after, reference, created_by) VALUES (?,'Receipt',?,?,'ยอดตั้งต้น',?)",
                                (cur.lastrowid, int(pstock), int(pstock), user["full_name"]),
                            )
                        conn.commit()
                        ok = True
                    except sqlite3.IntegrityError:
                        safe_rollback(conn)
                        st.error("รหัสสินค้านี้มีอยู่แล้ว")
                    finally:
                        conn.close()
                    if ok:
                        log_audit(user["full_name"], f"เพิ่มสินค้า {psku.strip()}")
                        queue_input("prod_sku", f"SKU-{uuid.uuid4().hex[:8].upper()}")
                        set_flash("success", "เพิ่มสินค้าเรียบร้อยแล้ว!")
                        st.rerun()

    conn = get_conn()
    try:
        df_p = pd.read_sql_query("SELECT * FROM products ORDER BY name", conn)
        df_mv = pd.read_sql_query(
            "SELECT m.created_at AS 'เวลา', p.sku AS 'SKU', p.name AS 'สินค้า', m.movement_type AS 'ประเภท', m.quantity AS 'จำนวน', m.balance_after AS 'คงเหลือ', m.reference AS 'อ้างอิง', m.created_by AS 'ผู้บันทึก' FROM inventory_movements m JOIN products p ON p.id=m.product_id ORDER BY m.id DESC LIMIT 500",
            conn,
        )
    finally:
        conn.close()

    if not df_p.empty:
        df_p["stock"] = df_p["stock"].fillna(0).astype(int)
        df_p["min_stock"] = df_p["min_stock"].fillna(10).astype(int)
        if len(df_p[df_p["stock"] <= df_p["min_stock"]]) > 0:
            st.warning("⚠️ มีสินค้าต่ำกว่าจุดแจ้งเตือน กรุณาตรวจสอบสต็อก")
    st.dataframe(df_p, use_container_width=True, hide_index=True)

    if not df_p.empty:
        p_opts = {f"{r.sku} · {r.name} · คงเหลือ {int(r.stock)} ชิ้น": int(r.id) for r in df_p.itertuples()}
        st.subheader("🔄 ปรับยอดรับเข้า / เบิกออกสินค้า")
        with st.form("adj_stock_form"):
            sp = st.selectbox("เลือกสินค้า", list(p_opts))
            mt = st.selectbox("ประเภท", ["Receipt", "Issue"], format_func=lambda v: "รับเข้า" if v == "Receipt" else "เบิกออก")
            mq = st.number_input("จำนวน", min_value=1, value=1, step=1)
            mref = st.text_input("เหตุผล / เลขอ้างอิง")
            if st.form_submit_button("บันทึกการเคลื่อนไหวสต็อก", type="primary"):
                try:
                    ns = adjust_stock(p_opts[sp], mt, mq, mref, user["full_name"])
                except (ValueError, sqlite3.Error) as err:
                    st.error(str(err))
                else:
                    log_audit(user["full_name"], f"ปรับสต็อก {sp} -> {ns}")
                    set_flash("success", f"บันทึกแล้ว · คงเหลือ {ns} ชิ้น")
                    st.rerun()
    st.subheader("📋 ประวัติการเคลื่อนไหวสต็อก")
    st.dataframe(df_mv, use_container_width=True, hide_index=True)

# ------------------------------------------------------------------------------
# MODULE: HR & PAYROLL
# ------------------------------------------------------------------------------
elif app_menu == "👥 HR & Payroll":
    with st.expander("➕ เพิ่มพนักงานใหม่"):
        with st.form("emp_form"):
            ec = gen_input("รหัสพนักงาน", "emp_code", lambda: f"EMP-{uuid.uuid4().hex[:8].upper()}")
            en = st.text_input("ชื่อ-นามสกุล")
            ep = st.text_input("ตำแหน่ง")
            esal = st.number_input("เงินเดือน (บาท)", min_value=0.0, value=30000.0, step=1000.0)
            edept = st.selectbox("แผนก", ["บริหาร", "บัญชีและการเงิน", "การขาย", "ทรัพยากรบุคคล", "ไอที"])
            if st.form_submit_button("บันทึกพนักงานใหม่", type="primary"):
                if not all(v.strip() for v in (ec, en, ep)):
                    st.error("กรุณากรอกข้อมูลพนักงานให้ครบ")
                else:
                    ok = False
                    conn = get_conn()
                    try:
                        conn.execute("INSERT INTO employees (emp_code, name, position, salary, department) VALUES (?,?,?,?,?)", (ec.strip(), en.strip(), ep.strip(), round(float(esal), 2), edept))
                        conn.commit()
                        ok = True
                    except sqlite3.IntegrityError:
                        safe_rollback(conn)
                        st.error("รหัสพนักงานนี้มีอยู่แล้ว")
                    finally:
                        conn.close()
                    if ok:
                        log_audit(user["full_name"], f"เพิ่มพนักงาน {ec.strip()}")
                        queue_input("emp_code", f"EMP-{uuid.uuid4().hex[:8].upper()}")
                        set_flash("success", "เพิ่มพนักงานเรียบร้อยแล้ว!")
                        st.rerun()

    conn = get_conn()
    try:
        df_emp = pd.read_sql_query("SELECT * FROM employees ORDER BY emp_code", conn)
        runs = conn.execute("SELECT id, period, status FROM payroll_runs ORDER BY period DESC").fetchall()
    finally:
        conn.close()
    st.dataframe(df_emp, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("💸 รอบจ่ายเงินเดือน")
    with st.form("pr_create"):
        per = st.text_input("รอบเงินเดือน (YYYY-MM)", value=date.today().strftime("%Y-%m"))
        if st.form_submit_button("สร้างรอบเงินเดือนแบบร่าง"):
            try:
                _, ecnt = create_payroll(per, user["full_name"])
            except sqlite3.IntegrityError:
                st.error("มีรอบเงินเดือนนี้อยู่แล้ว")
            except (ValueError, sqlite3.Error) as err:
                st.error(str(err))
            else:
                log_audit(user["full_name"], f"สร้างรอบเงินเดือน {per.strip()}")
                set_flash("success", f"สร้างรอบเงินเดือนสำเร็จ ({ecnt} คน)")
                st.rerun()

    if runs:
        r_opts = {f"{r['period']} · {r['status']}": r for r in runs}
        sel_r = r_opts[st.selectbox("เลือกรอบเงินเดือน", list(r_opts), key="sel_pr")]
        conn = get_conn()
        try:
            items = conn.execute(
                "SELECT pi.employee_id, e.emp_code, e.name, pi.gross_pay, pi.deductions, pi.net_pay FROM payroll_items pi JOIN employees e ON e.id=pi.employee_id WHERE pi.payroll_run_id=? ORDER BY e.emp_code",
                (sel_r["id"],),
            ).fetchall()
        finally:
            conn.close()
        if items:
            st.dataframe(pd.DataFrame([{"รหัส": i["emp_code"], "ชื่อ": i["name"], "เงินเดือน": i["gross_pay"], "หัก": i["deductions"], "สุทธิ": i["net_pay"]} for i in items]), use_container_width=True, hide_index=True)
        if sel_r["status"] == "Draft" and items:
            e_opts = {f"{i['emp_code']} · {i['name']}": i for i in items}
            sel_e = e_opts[st.selectbox("เลือกพนักงานเพื่อปรับยอดหัก", list(e_opts), key=f"pe_{sel_r['id']}")]
            gross_v = float(sel_e["gross_pay"])
            cur_d = min(float(sel_e["deductions"]), gross_v)
            if gross_v > 0:
                with st.form("pr_ded_form"):
                    dv = st.number_input(f"ยอดหัก (สูงสุด ฿{gross_v:,.2f})", min_value=0.0, value=cur_d, step=100.0, key=f"pd_{sel_r['id']}_{sel_e['employee_id']}_{cur_d:.2f}")
                    if st.form_submit_button("บันทึกยอดหัก"):
                        try:
                            update_payroll_deduction(sel_r["id"], sel_e["employee_id"], dv)
                        except (ValueError, sqlite3.Error) as err:
                            st.error(str(err))
                        else:
                            set_flash("success", "บันทึกยอดหักเรียบร้อยแล้ว")
                            st.rerun()
            if st.button("ยืนยันจ่ายเงินเดือนและบันทึกบัญชีอัตโนมัติ", type="primary"):
                try:
                    net_p = pay_payroll(sel_r["id"])
                except (ValueError, sqlite3.Error) as err:
                    st.error(str(err))
                else:
                    log_audit(user["full_name"], f"จ่ายเงินเดือนรอบ {sel_r['period']} ฿{net_p:,.2f}")
                    set_flash("success", "จ่ายเงินเดือนและบันทึกบัญชีเรียบร้อยแล้ว")
                    st.rerun()

# ------------------------------------------------------------------------------
# MODULE: JOURNAL ENTRIES & FINANCIAL STATEMENTS (GL)
# ------------------------------------------------------------------------------
elif app_menu == "📒 บันทึกบัญชีและงบการเงิน (GL)":
    tj, ttb, tpl = st.tabs(["📒 สมุดรายวัน (Journal)", "⚖️ งบทดลอง (Trial Balance)", "📊 งบกำไรขาดทุน (P&L)"])
    conn = get_conn()
    try:
        df_j = pd.read_sql_query("SELECT * FROM journal_entries ORDER BY id DESC", conn)
    finally:
        conn.close()

    with tj:
        with st.form("gl_form"):
            g1, g2 = st.columns(2)
            with g1:
                jd = st.date_input("วันที่", date.today())
                jdc = st.text_input("รหัสบัญชีเดบิต", "11100")
                jdn = st.text_input("ชื่อบัญชีเดบิต", "เงินสด/เงินฝากธนาคาร")
            with g2:
                ja = st.number_input("จำนวนเงิน (บาท)", min_value=0.01, value=1000.0)
                jcc = st.text_input("รหัสบัญชีเครดิต", "41100")
                jcn = st.text_input("ชื่อบัญชีเครดิต", "รายได้จากการขาย")
            jdesc = st.text_input("คำอธิบายรายการ")
            if st.form_submit_button("บันทึกรายการบัญชีคู่", type="primary"):
                if not all(v.strip() for v in (jdc, jdn, jcc, jcn, jdesc)):
                    st.error("กรุณากรอกข้อมูลให้ครบ")
                elif jdc.strip() == jcc.strip():
                    st.error("บัญชีเดบิตและเครดิตต้องเป็นคนละบัญชี")
                else:
                    amt_v = round(float(ja), 2)
                    conn = get_conn()
                    try:
                        conn.executemany(
                            "INSERT INTO journal_entries (entry_date, account_code, account_name, debit, credit, description) VALUES (?,?,?,?,?,?)",
                            [
                                (str(jd), jdc.strip(), jdn.strip(), amt_v, 0.0, jdesc.strip()),
                                (str(jd), jcc.strip(), jcn.strip(), 0.0, amt_v, jdesc.strip()),
                            ],
                        )
                        conn.commit()
                    finally:
                        conn.close()
                    log_audit(user["full_name"], f"บันทึกสมุดรายวัน ฿{amt_v:,.2f}")
                    set_flash("success", "บันทึกรายการเดบิตและเครดิตเรียบร้อยแล้ว")
                    st.rerun()
        st.dataframe(df_j, use_container_width=True, hide_index=True)
        if not df_j.empty:
            st.download_button("⬇️ ดาวน์โหลดสมุดรายวัน (CSV)", df_j.to_csv(index=False).encode("utf-8-sig"), f"taxmate_gl_{date.today().isoformat()}.csv", "text/csv")

    with ttb:
        if df_j.empty:
            st.info("ยังไม่มีรายการบัญชี")
        else:
            jc = df_j.assign(debit=df_j["debit"].fillna(0.0), credit=df_j["credit"].fillna(0.0))
            tb = jc.groupby(["account_code", "account_name"], as_index=False)[["debit", "credit"]].sum().sort_values("account_code")
            tb["net_balance"] = tb["debit"] - tb["credit"]
            dr_s, cr_s = float(tb["debit"].sum()), float(tb["credit"].sum())
            c1, c2, c3 = st.columns(3)
            c1.metric("รวมเดบิต", f"฿{dr_s:,.2f}")
            c2.metric("รวมเครดิต", f"฿{cr_s:,.2f}")
            c3.metric("สถานะ", "สมดุล" if math.isclose(dr_s, cr_s, abs_tol=0.01) else "ไม่สมดุล")
            st.dataframe(tb, use_container_width=True, hide_index=True)

    with tpl:
        if df_j.empty:
            st.info("ยังไม่มีรายการบัญชี")
        else:
            codes = df_j["account_code"].fillna("").astype(str).str.strip()
            rev_df, exp_df = df_j[codes.str.startswith("4")], df_j[codes.str.startswith(("5", "6"))]
            t_rev = float(rev_df["credit"].fillna(0).sum() - rev_df["debit"].fillna(0).sum())
            t_exp = float(exp_df["debit"].fillna(0).sum() - exp_df["credit"].fillna(0).sum())
            net_p = t_rev - t_exp
            p1, p2, p3 = st.columns(3)
            p1.metric("รายได้รวม (หมวด 4)", f"฿{t_rev:,.2f}")
            p2.metric("ค่าใช้จ่ายรวม (หมวด 5-6)", f"฿{t_exp:,.2f}")
            p3.metric("กำไร (ขาดทุน) สุทธิ", f"฿{net_p:,.2f}")
            st.plotly_chart(px.bar(pd.DataFrame({"รายการ": ["รายได้รวม", "ค่าใช้จ่ายรวม", "กำไรสุทธิ"], "จำนวนเงิน": [t_rev, t_exp, net_p]}), x="รายการ", y="จำนวนเงิน", title="สรุปงบกำไรขาดทุนเบื้องต้น"), use_container_width=True)

# ------------------------------------------------------------------------------
# MODULE: E-APPROVAL
# ------------------------------------------------------------------------------
elif app_menu == "🛡️ ระบบขออนุมัติ (E-Approval)":
    with st.form("app_form"):
        at = st.selectbox("ประเภทเอกสาร", ["PO", "EXPENSE", "LEAVE"])
        atitle = st.text_input("เรื่องที่ขออนุมัติ")
        aamt = st.number_input("จำนวนเงิน (บาท · ลางานใส่ 0 ได้)", min_value=0.0, value=0.0, step=500.0)
        if st.form_submit_button("ส่งคำขออนุมัติ", type="primary"):
            if not atitle.strip():
                st.error("กรุณาระบุเรื่องที่ขออนุมัติ")
            else:
                conn = get_conn()
                try:
                    conn.execute(
                        "INSERT INTO approvals (doc_type, title, amount, requested_by, status) VALUES (?,?,?,?,'Pending Approval')",
                        (at, atitle.strip(), round(float(aamt), 2), user["full_name"]),
                    )
                    conn.commit()
                finally:
                    conn.close()
                log_audit(user["full_name"], f"ส่งคำขออนุมัติ: {atitle.strip()}")
                set_flash("success", "ส่งคำขออนุมัติเรียบร้อยแล้ว!")
                st.rerun()

    conn = get_conn()
    try:
        pend_rows = conn.execute("SELECT id, doc_type, title, amount, requested_by FROM approvals WHERE status='Pending Approval' ORDER BY id").fetchall()
        df_app = pd.read_sql_query("SELECT * FROM approvals ORDER BY id DESC LIMIT 1000", conn)
    finally:
        conn.close()

    if user_role in APPROVER_ROLES:
        if pend_rows:
            a_opts = {f"#{r['id']} · {r['doc_type']} · {r['title']} · ฿{float(r['amount']):,.2f} · {r['requested_by']}": r["id"] for r in pend_rows}
            st.subheader("⚖️ พิจารณาคำขอที่รออนุมัติ")
            with st.form("rev_app_form"):
                sel_a = st.selectbox("เลือกคำขอ", list(a_opts))
                dec = st.radio("ผลการพิจารณา", ["อนุมัติ", "ปฏิเสธ"], horizontal=True)
                if st.form_submit_button("บันทึกผลการพิจารณา", type="primary"):
                    try:
                        process_approval(a_opts[sel_a], "Approved" if dec == "อนุมัติ" else "Rejected", user["full_name"])
                    except (ValueError, sqlite3.Error) as err:
                        st.error(str(err))
                    else:
                        log_audit(user["full_name"], f"{dec}คำขอ {sel_a}")
                        set_flash("success", "บันทึกผลการพิจารณาเรียบร้อยแล้ว")
                        st.rerun()
        else:
            st.info("ไม่มีคำขอที่รอพิจารณา")
    else:
        st.info("คุณสามารถส่งและติดตามคำขอได้ (สิทธิ์อนุมัติสงวนไว้สำหรับ Admin / ผู้บริหาร)")
    st.dataframe(df_app, use_container_width=True, hide_index=True)

# ------------------------------------------------------------------------------
# MODULE: RESET DATA (ADMIN ONLY)
# ------------------------------------------------------------------------------
elif app_menu == "🗑️ ล้างข้อมูลระบบ (Reset Data)":
    st.warning("⚠️ การลบข้อมูลจะลบออกจากฐานข้อมูล SQLite ทันทีและไม่สามารถกู้คืนได้")
    cnts = get_row_counts()
    tx_total = sum(cnts[t] for t in ALL_TX_TABLES)
    s1, s2, s3 = st.columns(3)
    s1.metric("ข้อมูลธุรกรรม", f"{tx_total:,} รายการ")
    s2.metric("บัญชีผู้ใช้", f"{cnts['users']:,} บัญชี")
    s3.metric("รวมทั้งหมด", f"{tx_total + cnts['users']:,} รายการ")

    t_all, t_part, t_one = st.tabs(["🔥 ลบทั้งหมด", "🧹 ลบเฉพาะหมวดหมู่", "🎯 ลบทีละรายการ"])
    with t_all:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 1. ล้างข้อมูลธุรกรรมทั้งหมด (เก็บบัญชีผู้ใช้ไว้)")
            with st.form("rst_tx"):
                chk1 = st.checkbox("ยืนยันล้างข้อมูลธุรกรรมทั้งหมด")
                if st.form_submit_button("🧹 ล้างข้อมูลธุรกรรมทั้งหมด", type="primary"):
                    if not chk1:
                        st.error("กรุณาติ๊กยืนยันก่อนลบ")
                    else:
                        d_cnt, _ = reset_tables(ALL_TX_TABLES, include_extra=True)
                        set_flash("success", f"ล้างข้อมูลธุรกรรมเรียบร้อยแล้ว ({d_cnt:,} รายการ)")
                        st.rerun()
        with col2:
            st.markdown("#### 2. Factory Reset (ลบทุกอย่างรวมบัญชีผู้ใช้)")
            with st.form("rst_all"):
                chk2 = st.checkbox("ยืนยันลบข้อมูลและบัญชีผู้ใช้ทั้งหมดอย่างถาวร")
                if st.form_submit_button("🔥 ล้างข้อมูลทั้งหมด (Factory Reset)", type="primary"):
                    if not chk2:
                        st.error("กรุณาติ๊กยืนยันก่อนลบ")
                    else:
                        reset_tables(ALL_TX_TABLES + ["users"], include_extra=True)
                        st.session_state.clear()
                        st.session_state.authenticated = False
                        st.session_state.user = None
                        set_flash("success", "ล้างข้อมูลทั้งหมดเรียบร้อยแล้ว")
                        st.rerun()

    with t_part:
        with st.form("rst_part"):
            grps = st.multiselect("เลือกหมวดข้อมูลที่ต้องการลบ", list(RESET_GROUPS))
            chk3 = st.checkbox("ยืนยันลบข้อมูลในหมวดที่เลือก")
            if st.form_submit_button("🗑️ ลบข้อมูลเฉพาะหมวดที่เลือก", type="primary"):
                if not grps or not chk3:
                    st.error("กรุณาเลือกหมวดข้อมูลและติ๊กยืนยัน")
                else:
                    tbls = [t for g in grps for t in RESET_GROUPS[g]]
                    d_cnt, cleared = reset_tables(tbls, actor=user["full_name"])
                    set_flash("success", f"ลบแล้ว {d_cnt:,} รายการ จาก {len(cleared)} ตาราง")
                    st.rerun()

    with t_one:
        cfg = {
            "🧾 ใบกำกับภาษี (Sales)": ("sales", "SELECT id, doc_no || ' · ' || customer || ' · ฿' || printf('%.2f', total) AS label FROM sales ORDER BY id DESC", ()),
            "📦 สินค้า (Products)": ("products", "SELECT id, sku || ' · ' || name || ' · คงเหลือ ' || stock AS label FROM products ORDER BY id DESC", ()),
            "🤝 ลูกค้า (CRM)": ("crm_customers", "SELECT id, cust_code || ' · ' || name || ' · ' || tier AS label FROM crm_customers ORDER BY id DESC", ()),
            "🛍️ ใบสั่งซื้อ (PO)": ("purchase_orders", "SELECT id, po_no || ' · ' || vendor_name || ' · ' || item_name AS label FROM purchase_orders ORDER BY id DESC", ()),
            "💸 ค่าใช้จ่าย (Expenses)": ("expenses", "SELECT id, exp_no || ' · ' || category || ' · ' || description AS label FROM expenses ORDER BY id DESC", ()),
            "👥 พนักงาน (Employees)": ("employees", "SELECT id, emp_code || ' · ' || name || ' · ' || position AS label FROM employees ORDER BY id DESC", ()),
            "📒 สมุดรายวัน (GL)": ("journal_entries", "SELECT id, entry_date || ' · ' || account_code || ' ' || account_name AS label FROM journal_entries ORDER BY id DESC", ()),
            "🛡️ คำขออนุมัติ (Approvals)": ("approvals", "SELECT id, doc_type || ' · ' || title || ' · ' || status AS label FROM approvals ORDER BY id DESC", ()),
            "👤 บัญชีผู้ใช้งานอื่น (Users)": ("users", "SELECT id, username || ' · ' || full_name || ' · ' || role AS label FROM users WHERE id != ? ORDER BY id DESC", (int(user["id"]),)),
        }
        cat = st.selectbox("เลือกหมวดหมู่", list(cfg), key="sdel_cat")
        t_key, q_sql, q_params = cfg[cat]
        conn = get_conn()
        try:
            i_rows = conn.execute(q_sql, q_params).fetchall()
        finally:
            conn.close()
        if not i_rows:
            st.info("ไม่มีรายการให้ลบในหมวดนี้")
        else:
            imap = {f"#{r['id']} · {r['label']}": int(r["id"]) for r in i_rows}
            sel_i = st.selectbox("เลือกรายการที่ต้องการลบ", list(imap), key=f"sdel_i_{t_key}")
            if st.button("🗑️ ลบรายการนี้ถาวร", type="primary"):
                try:
                    delete_record(t_key, imap[sel_i], user["full_name"], self_id=int(user["id"]))
                except (ValueError, sqlite3.Error) as err:
                    st.error(str(err))
                else:
                    set_flash("success", f"ลบรายการ {sel_i} เรียบร้อยแล้ว")
                    st.rerun()