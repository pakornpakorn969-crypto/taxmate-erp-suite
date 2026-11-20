# ==============================================================================
# 🏛️ TaxMate Enterprise ERP Suite v8.1 (Supabase PostgreSQL + SQLite Hybrid)
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
import zipfile
from datetime import date, datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    psycopg2 = None
    RealDictCursor = None

try:
    import qrcode
    from PIL import Image  # noqa: F401
except ImportError:
    qrcode = None

# ------------------------------------------------------------------------------
# 1. PAGE CONFIG & ENTERPRISE LIGHT 3D THEME
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="TaxMate Enterprise ERP Suite v8.1",
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
    .hero-desc { font-size: 15px; color: #475569; max-width: 880px; margin: 0 auto; line-height: 1.7; }
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
        font-family: 'Sarabun', sans-serif; color: #0F172A; font-size: 14px;
    }
    .receipt-paper table { width: 100%; border-collapse: collapse; margin: 10px 0; }
    .receipt-paper th, .receipt-paper td { border-bottom: 1px solid #E2E8F0; padding: 5px 4px; text-align: left; }
    .receipt-paper .num { text-align: right; }
    [data-testid="stMetricValue"] { font-size: 24px !important; font-weight: 800 !important; color: #1E3A8A !important; }
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
# 2. DATABASE ENGINE DETECTION (SUPABASE POSTGRESQL OR LOCAL SQLITE)
# ------------------------------------------------------------------------------
APP_DIR = os.path.dirname(os.path.abspath(__file__))


def resolve_database_url() -> str:
    url = ""
    try:
        if "DATABASE_URL" in st.secrets:
            url = str(st.secrets["DATABASE_URL"]).strip()
        elif "supabase" in st.secrets and "database_url" in st.secrets["supabase"]:
            url = str(st.secrets["supabase"]["database_url"]).strip()
    except Exception:
        pass
    if not url:
        url = str(os.environ.get("DATABASE_URL") or "").strip()
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://") and "sslmode=" not in url.lower():
        if "localhost" not in url.lower() and "127.0.0.1" not in url.lower():
            url += ("&" if "?" in url else "?") + "sslmode=require"
    return url


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


DATABASE_URL = resolve_database_url()
DB_ENGINE = "postgres" if DATABASE_URL.startswith("postgresql://") else "sqlite"
DB_FILE = resolve_db_path()

DB_INTEGRITY_ERRORS = (sqlite3.IntegrityError, psycopg2.IntegrityError) if psycopg2 else (sqlite3.IntegrityError,)
DB_ERRORS = (sqlite3.Error, psycopg2.Error) if psycopg2 else (sqlite3.Error,)

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

THAI_COA = [
    ("11100", "เงินสด/เงินฝากธนาคาร"),
    ("11200", "เงินรับผ่านบัตรเครดิต"),
    ("11300", "ลูกหนี้การค้า"),
    ("11400", "ภาษีเงินได้หัก ณ ที่จ่ายถูกหัก"),
    ("11500", "ภาษีซื้อ (Input VAT)"),
    ("12100", "อุปกรณ์สำนักงานและสินทรัพย์ถาวร"),
    ("21100", "เจ้าหนี้การค้า/เจ้าหนี้ค่าใช้จ่าย"),
    ("21300", "ภาษีขาย (Output VAT)"),
    ("21400", "หนี้สินรายการหักเงินเดือน/ประกันสังคมค้างจ่าย"),
    ("21500", "ภาษีหัก ณ ที่จ่ายรอนำส่ง (ภ.ง.ด.)"),
    ("31000", "ทุนจดทะเบียน"),
    ("32000", "กำไรสะสม"),
    ("41100", "รายได้จากการขายและบริการ"),
    ("42100", "รายได้อื่น"),
    ("51000", "ค่าใช้จ่ายเงินเดือนและสวัสดิการ"),
    ("52000", "ต้นทุนขายและบริการ"),
    ("61000", "ค่าใช้จ่ายในการดำเนินงาน"),
    ("62000", "ค่าเสื่อมราคาและค่าใช้จ่ายอื่น"),
]

RESET_GROUPS = {
    "🧾 ยอดขายและใบกำกับภาษี (Sales & Payments)": ["sales_payments", "sale_items", "sales"],
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
    "sales_payments", "sale_items", "sales",
    "inventory_movements", "products", "crm_customers",
    "purchase_orders", "expenses",
    "payroll_items", "payroll_runs", "employees",
    "journal_entries", "approvals", "audit_logs",
]
ALLOWED_RESET_TABLES = set(ALL_TX_TABLES) | {"users", "company_settings"}


# ------------------------------------------------------------------------------
# 3. DUAL-ENGINE DATABASE WRAPPER & UTILITIES
# ------------------------------------------------------------------------------
def _adapt_sql(sql: str) -> str:
    if DB_ENGINE != "postgres":
        return sql
    out = []
    in_quote = False
    i = 0
    n = len(sql)
    while i < n:
        ch = sql[i]
        if ch == "'":
            out.append(ch)
            if in_quote and i + 1 < n and sql[i + 1] == "'":
                out.append("'")
                i += 1
            else:
                in_quote = not in_quote
        elif ch == "?" and not in_quote:
            out.append("%s")
        elif ch == "%":
            out.append("%%")
        else:
            out.append(ch)
        i += 1
    return "".join(out)


class DBCursor:
    def __init__(self, raw_cur):
        self._cur = raw_cur

    def execute(self, sql: str, params=None):
        if DB_ENGINE == "postgres" and sql.strip().upper().startswith("BEGIN"):
            return self
        q = _adapt_sql(sql)
        if params is None:
            self._cur.execute(q)
        else:
            self._cur.execute(q, params)
        return self

    def executemany(self, sql: str, seq_params):
        q = _adapt_sql(sql)
        self._cur.executemany(q, seq_params)
        return self

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()

    @property
    def rowcount(self):
        return self._cur.rowcount

    @property
    def lastrowid(self):
        return getattr(self._cur, "lastrowid", None)

    @property
    def description(self):
        return self._cur.description


class DBConnection:
    def __init__(self, raw_conn):
        self._conn = raw_conn

    def cursor(self) -> DBCursor:
        if DB_ENGINE == "postgres":
            return DBCursor(self._conn.cursor(cursor_factory=RealDictCursor))
        return DBCursor(self._conn.cursor())

    def execute(self, sql: str, params=None) -> DBCursor:
        cur = self.cursor()
        cur.execute(sql, params)
        return cur

    def executemany(self, sql: str, seq_params) -> DBCursor:
        cur = self.cursor()
        cur.executemany(sql, seq_params)
        return cur

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()


def get_conn() -> DBConnection:
    if DB_ENGINE == "postgres":
        if psycopg2 is None:
            raise RuntimeError("ยังไม่ได้ติดตั้ง psycopg2-binary กรุณาเพิ่ม psycopg2-binary ใน requirements.txt")
        raw = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        return DBConnection(raw)
    raw = sqlite3.connect(DB_FILE, timeout=20, check_same_thread=False)
    raw.row_factory = sqlite3.Row
    raw.execute("PRAGMA busy_timeout = 20000")
    raw.execute("PRAGMA foreign_keys = ON")
    return DBConnection(raw)


def safe_rollback(conn):
    if conn is not None:
        try:
            conn.rollback()
        except Exception:
            pass


def first_val(row, default=0):
    if row is None:
        return default
    if isinstance(row, dict):
        val = next(iter(row.values()), default)
        return default if val is None else val
    return default if row[0] is None else row[0]


def read_df(conn: DBConnection, sql: str, params=None) -> pd.DataFrame:
    cur = conn.execute(sql, params)
    rows = cur.fetchall()
    cols = [d[0] for d in (cur.description or [])]
    if not rows:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame([dict(r) for r in rows], columns=cols)


def insert_returning_id(cur: DBCursor, sql: str, params) -> int:
    if DB_ENGINE == "postgres":
        cur.execute(sql.rstrip().rstrip(";") + " RETURNING id", params)
        return int(first_val(cur.fetchone(), 0))
    cur.execute(sql, params)
    return int(cur.lastrowid)


def table_exists(cur: DBCursor, name: str) -> bool:
    if DB_ENGINE == "postgres":
        return cur.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name=?",
            (name,),
        ).fetchone() is not None
    return cur.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def table_columns(cur: DBCursor, table: str) -> set:
    if DB_ENGINE == "postgres":
        rows = cur.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name=?",
            (table,),
        ).fetchall()
        return {r["column_name"] for r in rows}
    return {r["name"] for r in cur.execute(f'PRAGMA table_info("{table}")').fetchall()}


def ensure_col(cur: DBCursor, table: str, col: str, decl: str):
    if col not in table_columns(cur, table):
        pg_decl = decl.replace("REAL", "DOUBLE PRECISION") if DB_ENGINE == "postgres" else decl
        cur.execute(f'ALTER TABLE "{table}" ADD COLUMN "{col}" {pg_decl}')


def archive_if_incompatible(cur: DBCursor, table: str, required_cols: set):
    if DB_ENGINE == "postgres" or not table_exists(cur, table):
        return None
    if required_cols.issubset(table_columns(cur, table)):
        return None
    suffix = 1
    while True:
        archive_name = f"{table}_legacy_v{suffix}"
        if not table_exists(cur, archive_name):
            break
        suffix += 1
    cur.execute(f'ALTER TABLE "{table}" RENAME TO "{archive_name}"')
    return archive_name


def ui_dataframe(df, **kwargs):
    try:
        return st.dataframe(df, width="stretch", **kwargs)
    except TypeError:
        return st.dataframe(df, use_container_width=True, **kwargs)


def ui_plotly(fig, **kwargs):
    try:
        return st.plotly_chart(fig, width="stretch", **kwargs)
    except TypeError:
        return st.plotly_chart(fig, use_container_width=True, **kwargs)


def ui_button(label, container=None, **kwargs):
    target = container if container is not None else st
    try:
        return target.button(label, width="stretch", **kwargs)
    except TypeError:
        return target.button(label, use_container_width=True, **kwargs)


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


def username_exists(cur: DBCursor, username: str) -> bool:
    return cur.execute(
        "SELECT 1 FROM users WHERE LOWER(username) = LOWER(?)", (username.strip(),)
    ).fetchone() is not None


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


def compute_invoice_totals(subtotal: float, discount: float, vat_mode: str, vat_rate: float, wht_rate: float) -> dict:
    sub = round(max(float(subtotal), 0.0), 2)
    disc = round(min(max(float(discount), 0.0), sub), 2)
    after_disc = round(sub - disc, 2)
    vr, wr = max(float(vat_rate), 0.0), max(float(wht_rate), 0.0)
    if vat_mode == "ยกเว้น VAT (0%)":
        amount, vat, total = after_disc, 0.0, after_disc
    elif vat_mode == "รวมใน (Include VAT)":
        total = after_disc
        amount = round(total / (1.0 + vr / 100.0), 2) if vr > 0 else total
        vat = round(total - amount, 2)
    else:
        amount = after_disc
        vat = round(amount * (vr / 100.0), 2)
        total = round(amount + vat, 2)
    wht_amount = round(amount * (wr / 100.0), 2)
    return {
        "subtotal": sub, "discount": disc, "amount": amount,
        "vat": vat, "total": total, "wht_amount": wht_amount,
        "net_receivable": round(max(total - wht_amount, 0.0), 2),
    }


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


def build_invoice_html(company: dict, sale: dict, items: list) -> str:
    if items:
        rows_html = "".join(
            f"<tr><td>{i}</td><td>{safe_text(it['item_name'])}</td>"
            f"<td class='num'>{int(it['qty']):,}</td>"
            f"<td class='num'>฿{float(it['unit_price']):,.2f}</td>"
            f"<td class='num'>฿{float(it['line_total']):,.2f}</td></tr>"
            for i, it in enumerate(items, 1)
        )
    else:
        rows_html = (
            f"<tr><td>1</td><td>ค่าสินค้า / บริการตามเอกสาร {safe_text(sale['doc_no'])}</td>"
            f"<td class='num'>1</td><td class='num'>฿{float(sale['amount']):,.2f}</td>"
            f"<td class='num'>฿{float(sale['amount']):,.2f}</td></tr>"
        )
    return f"""<!DOCTYPE html><html lang="th"><head><meta charset="utf-8">
    <title>{safe_text(sale['doc_no'])}</title>
    <style>
        body {{ font-family:'Sarabun',sans-serif; color:#0F172A; max-width:820px; margin:24px auto; padding:28px; border:1px solid #CBD5E1; }}
        .header {{ display:flex; justify-content:space-between; border-bottom:2px solid #1E3A8A; padding-bottom:14px; margin-bottom:16px; }}
        .title {{ color:#1E3A8A; font-size:21px; font-weight:800; }}
        table {{ width:100%; border-collapse:collapse; margin:16px 0; }}
        th, td {{ border:1px solid #CBD5E1; padding:8px 10px; font-size:14px; }}
        th {{ background:#EFF6FF; color:#1E3A8A; }}
        .num {{ text-align:right; }}
        .totals {{ width:340px; margin-left:auto; }}
        .sign {{ display:flex; justify-content:space-between; margin-top:44px; text-align:center; }}
        .sign div {{ width:42%; border-top:1px solid #64748B; padding-top:8px; font-size:13px; }}
        @media print {{ body {{ border:none; margin:0; }} }}
    </style></head><body>
    <div class="header">
        <div>
            <div class="title">{safe_text(company['company_name'])}</div>
            <div>{safe_text(company['address'])}</div>
            <div>เลขผู้เสียภาษี: {safe_text(company['tax_id'])} ({safe_text(company['branch_name'])})</div>
            <div>โทร: {safe_text(company['phone'])} | อีเมล: {safe_text(company['email'])}</div>
        </div>
        <div style="text-align:right;">
            <div class="title">ใบกำกับภาษี / ใบเสร็จรับเงิน</div>
            <div><b>เลขที่:</b> {safe_text(sale['doc_no'])}</div>
            <div><b>วันที่:</b> {safe_text(str(sale.get('created_at') or date.today().isoformat())[:10])}</div>
            <div><b>ครบกำหนด:</b> {safe_text(sale.get('due_date') or '-')}</div>
        </div>
    </div>
    <div><b>ลูกค้า:</b> {safe_text(sale['customer'])} | <b>เลขผู้เสียภาษี:</b> {safe_text(sale.get('customer_tax_id') or '-')} | <b>สถานะ:</b> {safe_text(sale.get('status') or '-')}</div>
    <table>
        <thead><tr><th style="width:45px;">#</th><th>รายการสินค้า / บริการ</th><th class="num" style="width:80px;">จำนวน</th><th class="num" style="width:120px;">ราคา/หน่วย</th><th class="num" style="width:130px;">จำนวนเงิน</th></tr></thead>
        <tbody>{rows_html}</tbody>
    </table>
    <table class="totals">
        <tr><td>ส่วนลด</td><td class="num">-฿{float(sale.get('discount') or 0):,.2f}</td></tr>
        <tr><td>มูลค่าก่อน VAT</td><td class="num">฿{float(sale['amount']):,.2f}</td></tr>
        <tr><td>ภาษีมูลค่าเพิ่ม (VAT)</td><td class="num">฿{float(sale['tax']):,.2f}</td></tr>
        <tr><td><b>รวมเป็นเงินทั้งสิ้น</b></td><td class="num"><b>฿{float(sale['total']):,.2f}</b></td></tr>
        <tr><td>หัก ณ ที่จ่าย ({float(sale.get('wht_rate') or 0):.1f}%)</td><td class="num">-฿{float(sale.get('wht_amount') or 0):,.2f}</td></tr>
        <tr style="background:#EFF6FF;"><td><b>ยอดสุทธิที่ต้องชำระ</b></td><td class="num"><b>฿{float(sale.get('net_receivable') or sale['total']):,.2f}</b></td></tr>
    </table>
    <div style="font-size:13px; color:#475569;">หมายเหตุ: {safe_text(sale.get('notes') or '-')}</div>
    <div class="sign">
        <div>ผู้รับสินค้า / ผู้ชำระเงิน<br>วันที่ ____/____/________</div>
        <div>ผู้มีอำนาจลงนาม / ผู้รับเงิน<br>วันที่ ____/____/________</div>
    </div></body></html>"""


def build_payslip_html(company: dict, period: str, item: dict) -> str:
    return f"""<!DOCTYPE html><html lang="th"><head><meta charset="utf-8">
    <title>Payslip {safe_text(period)} - {safe_text(item['emp_code'])}</title>
    <style>
        body {{ font-family:'Sarabun',sans-serif; color:#0F172A; max-width:720px; margin:24px auto; padding:24px; border:1px solid #CBD5E1; }}
        h2 {{ color:#1E3A8A; margin:0 0 4px 0; }}
        table {{ width:100%; border-collapse:collapse; margin:16px 0; }}
        th, td {{ border:1px solid #CBD5E1; padding:8px 10px; font-size:14px; }}
        th {{ background:#EFF6FF; text-align:left; }}
        .num {{ text-align:right; }}
    </style></head><body>
    <h2>{safe_text(company['company_name'])}</h2>
    <div>ใบแจ้งเงินเดือน (PAYSLIP) ประจำงวด <b>{safe_text(period)}</b></div><hr>
    <p><b>รหัสพนักงาน:</b> {safe_text(item['emp_code'])} | <b>ชื่อ-นามสกุล:</b> {safe_text(item['name'])}<br>
    <b>ตำแหน่ง:</b> {safe_text(item['position'])} | <b>แผนก:</b> {safe_text(item['department'])} |
    <b>เลขบัญชี:</b> {safe_text(item.get('bank_account') or '-')}</p>
    <table>
        <thead><tr><th>รายได้</th><th class="num">จำนวน (บาท)</th><th>รายการหัก</th><th class="num">จำนวน (บาท)</th></tr></thead>
        <tbody>
            <tr><td>เงินเดือนประจำ</td><td class="num">฿{float(item['gross_pay']):,.2f}</td><td>ประกันสังคม (SSO)</td><td class="num">฿{float(item['sso_deduction']):,.2f}</td></tr>
            <tr><td>OT / โบนัส / ค่าตำแหน่ง</td><td class="num">฿{float(item['bonus']):,.2f}</td><td>ภาษี ภ.ง.ด.1</td><td class="num">฿{float(item['tax_deduction']):,.2f}</td></tr>
            <tr><td></td><td></td><td>รายการหักอื่น ๆ</td><td class="num">฿{float(item['other_deduction']):,.2f}</td></tr>
            <tr style="background:#F8FAFC;"><td><b>รวมรายได้</b></td><td class="num"><b>฿{float(item['gross_pay']) + float(item['bonus']):,.2f}</b></td><td><b>รวมรายการหัก</b></td><td class="num"><b>฿{float(item['deductions']):,.2f}</b></td></tr>
        </tbody>
    </table>
    <div style="background:#EFF6FF; padding:14px; border-radius:8px; font-size:18px; text-align:right;">
        <b>เงินได้สุทธิโอนเข้าบัญชี (Net Pay): ฿{float(item['net_pay']):,.2f}</b>
    </div></body></html>"""


def build_zip_backup() -> bytes:
    buf = io.BytesIO()
    conn = get_conn()
    try:
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for t in ["company_settings", "users"] + ALL_TX_TABLES:
                df = read_df(conn, f'SELECT * FROM "{t}"')
                zf.writestr(f"{t}.csv", df.to_csv(index=False).encode("utf-8-sig"))
    finally:
        conn.close()
    return buf.getvalue()


# ------------------------------------------------------------------------------
# 4. DATABASE INITIALIZATION, AUTO-MIGRATION & DOMAIN TRANSACTIONS
# ------------------------------------------------------------------------------
def init_db():
    pk = "SERIAL PRIMARY KEY" if DB_ENGINE == "postgres" else "INTEGER PRIMARY KEY AUTOINCREMENT"
    num = "DOUBLE PRECISION" if DB_ENGINE == "postgres" else "REAL"

    conn = get_conn()
    try:
        if DB_ENGINE == "sqlite":
            try:
                conn.execute("PRAGMA journal_mode = WAL")
            except Exception:
                pass
        cur = conn.cursor()

        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS company_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                company_name TEXT NOT NULL DEFAULT 'บริษัท แท็กซ์เมท เอ็นเตอร์ไพรส์ จำกัด',
                tax_id TEXT DEFAULT '0105560000000',
                branch_name TEXT DEFAULT 'สำนักงานใหญ่',
                address TEXT DEFAULT 'กรุงเทพมหานคร ประเทศไทย',
                phone TEXT DEFAULT '02-000-0000',
                email TEXT DEFAULT 'contact@taxmate-erp.local',
                default_promptpay TEXT DEFAULT '',
                default_vat_rate {num} DEFAULT 7.0,
                default_wht_rate {num} DEFAULT 3.0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
        cur.execute("INSERT INTO company_settings (id) VALUES (1) ON CONFLICT (id) DO NOTHING")

        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS users (
                id {pk},
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
        for col, decl in [("department", "TEXT NOT NULL DEFAULT 'ทั่วไป'"), ("email", "TEXT"), ("status", "TEXT NOT NULL DEFAULT 'Active'"), ("allowed_modules", "TEXT NOT NULL DEFAULT 'all'"), ("created_at", "TIMESTAMP")]:
            ensure_col(cur, "users", col, decl)
        cur.execute("UPDATE users SET status = 'Active' WHERE status IS NULL OR TRIM(status) = ''")

        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS sales (
                id {pk},
                doc_no TEXT UNIQUE NOT NULL,
                customer TEXT NOT NULL,
                customer_tax_id TEXT,
                amount {num} NOT NULL,
                tax {num} NOT NULL,
                total {num} NOT NULL,
                status TEXT NOT NULL,
                branch TEXT DEFAULT 'สำนักงานใหญ่',
                payment_method TEXT DEFAULT 'โอนเงินผ่านธนาคาร',
                discount {num} DEFAULT 0.0,
                vat_mode TEXT DEFAULT 'แยกนอก (Exclude VAT)',
                wht_rate {num} DEFAULT 0.0,
                wht_amount {num} DEFAULT 0.0,
                net_receivable {num} DEFAULT 0.0,
                due_date TEXT,
                notes TEXT,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
        for col, decl in [
            ("customer_tax_id", "TEXT"), ("branch", "TEXT DEFAULT 'สำนักงานใหญ่'"),
            ("payment_method", "TEXT DEFAULT 'โอนเงินผ่านธนาคาร'"), ("discount", "REAL DEFAULT 0.0"),
            ("vat_mode", "TEXT DEFAULT 'แยกนอก (Exclude VAT)'"), ("wht_rate", "REAL DEFAULT 0.0"),
            ("wht_amount", "REAL DEFAULT 0.0"), ("net_receivable", "REAL DEFAULT 0.0"),
            ("due_date", "TEXT"), ("notes", "TEXT"), ("created_by", "TEXT"), ("created_at", "TIMESTAMP"),
        ]:
            ensure_col(cur, "sales", col, decl)
        cur.execute("UPDATE sales SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
        cur.execute("UPDATE sales SET net_receivable = total - COALESCE(wht_amount, 0) WHERE net_receivable IS NULL OR (net_receivable = 0 AND total > 0)")

        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS sale_items (
                id {pk},
                sale_id INTEGER NOT NULL REFERENCES sales(id) ON DELETE CASCADE,
                product_id INTEGER,
                item_name TEXT NOT NULL,
                qty INTEGER NOT NULL CHECK (qty > 0),
                unit_price {num} NOT NULL CHECK (unit_price >= 0),
                line_total {num} NOT NULL CHECK (line_total >= 0)
            )""")

        archive_if_incompatible(cur, "sales_payments", {"sale_id", "amount", "payment_method", "received_by"})
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS sales_payments (
                id {pk},
                sale_id INTEGER NOT NULL REFERENCES sales(id) ON DELETE CASCADE,
                amount {num} NOT NULL CHECK (amount > 0),
                payment_method TEXT NOT NULL,
                received_by TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
        ensure_col(cur, "sales_payments", "created_at", "TIMESTAMP")

        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS products (
                id {pk},
                sku TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                price {num} NOT NULL,
                stock INTEGER NOT NULL,
                category TEXT NOT NULL,
                branch TEXT DEFAULT 'สำนักงานใหญ่',
                min_stock INTEGER DEFAULT 10,
                cost_price {num} DEFAULT 0.0,
                unit TEXT DEFAULT 'ชิ้น',
                location TEXT DEFAULT 'คลังหลัก'
            )""")
        for col, decl in [("branch", "TEXT DEFAULT 'สำนักงานใหญ่'"), ("min_stock", "INTEGER DEFAULT 10"), ("cost_price", "REAL DEFAULT 0.0"), ("unit", "TEXT DEFAULT 'ชิ้น'"), ("location", "TEXT DEFAULT 'คลังหลัก'")]:
            ensure_col(cur, "products", col, decl)
        cur.execute("UPDATE products SET min_stock = 10 WHERE min_stock IS NULL")

        legacy_inv = archive_if_incompatible(cur, "inventory_movements", {"product_id", "movement_type", "quantity", "balance_after", "reference", "created_by"})
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS inventory_movements (
                id {pk},
                product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
                movement_type TEXT NOT NULL CHECK (movement_type IN ('Receipt', 'Issue')),
                quantity INTEGER NOT NULL CHECK (quantity > 0),
                balance_after INTEGER NOT NULL CHECK (balance_after >= 0),
                reference TEXT NOT NULL,
                created_by TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
        ensure_col(cur, "inventory_movements", "created_at", "TIMESTAMP")
        if legacy_inv:
            valid_pids = {r["id"] for r in cur.execute("SELECT id FROM products").fetchall()}
            for r in cur.execute(f'SELECT * FROM "{legacy_inv}"').fetchall():
                d = dict(r)
                pid, raw_qty = d.get("product_id"), (d.get("quantity") if d.get("quantity") is not None else d.get("qty"))
                if pid not in valid_pids or raw_qty is None or abs(int(raw_qty)) <= 0:
                    continue
                raw_t = str(d.get("movement_type") or d.get("type") or "").strip().lower()
                mv_t = "Issue" if raw_t in ("issue", "out", "withdraw", "เบิกออก") else "Receipt"
                cur.execute(
                    "INSERT INTO inventory_movements (product_id, movement_type, quantity, balance_after, reference, created_by, created_at) VALUES (?,?,?,?,?,?,?)",
                    (pid, mv_t, abs(int(raw_qty)), max(int(d.get("balance_after") or 0), 0), str(d.get("reference") or "ข้อมูลเดิม"), str(d.get("created_by") or "System"), d.get("created_at")),
                )

        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS crm_customers (
                id {pk},
                cust_code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                phone TEXT,
                email TEXT,
                tier TEXT DEFAULT 'Silver',
                points INTEGER DEFAULT 0,
                tax_id TEXT,
                address TEXT,
                credit_limit {num} DEFAULT 0.0,
                notes TEXT
            )""")
        for col, decl in [("phone", "TEXT"), ("email", "TEXT"), ("tier", "TEXT DEFAULT 'Silver'"), ("points", "INTEGER DEFAULT 0"), ("tax_id", "TEXT"), ("address", "TEXT"), ("credit_limit", "REAL DEFAULT 0.0"), ("notes", "TEXT")]:
            ensure_col(cur, "crm_customers", col, decl)

        legacy_po = archive_if_incompatible(cur, "purchase_orders", {"po_no", "vendor_name", "item_name", "qty", "total_amount", "status"})
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS purchase_orders (
                id {pk},
                po_no TEXT UNIQUE NOT NULL,
                vendor_name TEXT NOT NULL,
                item_name TEXT NOT NULL,
                qty INTEGER NOT NULL,
                total_amount {num} NOT NULL,
                status TEXT DEFAULT 'Pending Approval',
                branch TEXT DEFAULT 'สำนักงานใหญ่',
                requested_by TEXT,
                approved_by TEXT,
                unit_price {num} DEFAULT 0.0,
                vat_amount {num} DEFAULT 0.0,
                expected_date TEXT,
                received_status TEXT DEFAULT 'รอรับสินค้า',
                product_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
        for col, decl in [("branch", "TEXT DEFAULT 'สำนักงานใหญ่'"), ("requested_by", "TEXT"), ("approved_by", "TEXT"), ("unit_price", "REAL DEFAULT 0.0"), ("vat_amount", "REAL DEFAULT 0.0"), ("expected_date", "TEXT"), ("received_status", "TEXT DEFAULT 'รอรับสินค้า'"), ("product_id", "INTEGER"), ("created_at", "TIMESTAMP")]:
            ensure_col(cur, "purchase_orders", col, decl)
        if legacy_po:
            for r in cur.execute(f'SELECT * FROM "{legacy_po}"').fetchall():
                d = dict(r)
                cur.execute(
                    "INSERT INTO purchase_orders (po_no, vendor_name, item_name, qty, total_amount, status, branch, requested_by, approved_by, created_at) VALUES (?,?,?,?,?,?,?,?,?,?) ON CONFLICT (po_no) DO NOTHING",
                    (d.get("po_no") or f"PO-LEGACY-{d.get('id')}", d.get("vendor_name") or "ไม่ระบุ", d.get("item_name") or "รายการเดิม", max(int(d.get("qty") or 1), 1), float(d.get("total_amount") or 0), d.get("status") or "Pending Approval", d.get("branch") or "สำนักงานใหญ่", d.get("requested_by"), d.get("approved_by"), d.get("created_at")),
                )

        legacy_exp = archive_if_incompatible(cur, "expenses", {"exp_no", "category", "description", "amount", "approved_by"})
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS expenses (
                id {pk},
                exp_no TEXT UNIQUE NOT NULL,
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                amount {num} NOT NULL,
                approved_by TEXT,
                status TEXT NOT NULL DEFAULT 'Pending Approval',
                vendor_name TEXT,
                tax_inv_no TEXT,
                vat_amount {num} DEFAULT 0.0,
                wht_rate {num} DEFAULT 0.0,
                wht_amount {num} DEFAULT 0.0,
                payment_status TEXT DEFAULT 'รอจ่าย',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
        for col, decl in [("approved_by", "TEXT"), ("status", "TEXT NOT NULL DEFAULT 'Pending Approval'"), ("vendor_name", "TEXT"), ("tax_inv_no", "TEXT"), ("vat_amount", "REAL DEFAULT 0.0"), ("wht_rate", "REAL DEFAULT 0.0"), ("wht_amount", "REAL DEFAULT 0.0"), ("payment_status", "TEXT DEFAULT 'รอจ่าย'"), ("created_at", "TIMESTAMP")]:
            ensure_col(cur, "expenses", col, decl)
        if legacy_exp:
            for r in cur.execute(f'SELECT * FROM "{legacy_exp}"').fetchall():
                d = dict(r)
                cur.execute(
                    "INSERT INTO expenses (exp_no, category, description, amount, approved_by, created_at) VALUES (?,?,?,?,?,?) ON CONFLICT (exp_no) DO NOTHING",
                    (d.get("exp_no") or f"EXP-LEGACY-{d.get('id')}", d.get("category") or "อื่นๆ", d.get("description") or "รายการเดิม", float(d.get("amount") or 0), d.get("approved_by"), d.get("created_at")),
                )
        cur.execute("UPDATE expenses SET status = 'Approved' WHERE status = 'Pending Approval' AND approved_by IS NOT NULL")

        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS employees (
                id {pk},
                emp_code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                position TEXT NOT NULL,
                salary {num} NOT NULL,
                department TEXT NOT NULL,
                status TEXT DEFAULT 'Active',
                phone TEXT,
                email TEXT,
                bank_account TEXT,
                sso_enabled INTEGER DEFAULT 1
            )""")
        for col, decl in [("status", "TEXT DEFAULT 'Active'"), ("phone", "TEXT"), ("email", "TEXT"), ("bank_account", "TEXT"), ("sso_enabled", "INTEGER DEFAULT 1")]:
            ensure_col(cur, "employees", col, decl)

        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS payroll_runs (
                id {pk},
                period TEXT UNIQUE NOT NULL,
                status TEXT NOT NULL DEFAULT 'Draft',
                created_by TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                paid_at TIMESTAMP
            )""")

        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS payroll_items (
                id {pk},
                payroll_run_id INTEGER NOT NULL REFERENCES payroll_runs(id) ON DELETE CASCADE,
                employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
                gross_pay {num} NOT NULL CHECK (gross_pay >= 0),
                bonus {num} NOT NULL DEFAULT 0,
                sso_deduction {num} NOT NULL DEFAULT 0,
                tax_deduction {num} NOT NULL DEFAULT 0,
                other_deduction {num} NOT NULL DEFAULT 0,
                deductions {num} NOT NULL DEFAULT 0 CHECK (deductions >= 0),
                net_pay {num} NOT NULL CHECK (net_pay >= 0),
                UNIQUE(payroll_run_id, employee_id)
            )""")
        for col, decl in [("bonus", "REAL NOT NULL DEFAULT 0"), ("sso_deduction", "REAL NOT NULL DEFAULT 0"), ("tax_deduction", "REAL NOT NULL DEFAULT 0"), ("other_deduction", "REAL NOT NULL DEFAULT 0")]:
            ensure_col(cur, "payroll_items", col, decl)

        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS journal_entries (
                id {pk},
                entry_date TEXT NOT NULL,
                account_code TEXT NOT NULL,
                account_name TEXT NOT NULL,
                debit {num} DEFAULT 0.0,
                credit {num} DEFAULT 0.0,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
        ensure_col(cur, "journal_entries", "created_at", "TIMESTAMP")

        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS approvals (
                id {pk},
                doc_type TEXT NOT NULL,
                title TEXT NOT NULL,
                amount {num} NOT NULL,
                requested_by TEXT NOT NULL,
                status TEXT DEFAULT 'Pending Approval',
                approved_by TEXT,
                document_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
        for col, decl in [("approved_by", "TEXT"), ("document_id", "INTEGER"), ("created_at", "TIMESTAMP")]:
            ensure_col(cur, "approvals", col, decl)

        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id {pk},
                user_name TEXT NOT NULL,
                action TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")

        conn.commit()
    finally:
        conn.close()


def get_company_settings() -> dict:
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM company_settings WHERE id = 1").fetchone()
        return dict(row) if row else {
            "company_name": "บริษัท แท็กซ์เมท เอ็นเตอร์ไพรส์ จำกัด",
            "tax_id": "0105560000000", "branch_name": "สำนักงานใหญ่",
            "address": "กรุงเทพมหานคร ประเทศไทย", "phone": "02-000-0000",
            "email": "contact@taxmate-erp.local", "default_promptpay": "",
            "default_vat_rate": 7.0, "default_wht_rate": 3.0,
        }
    finally:
        conn.close()


def log_audit(user_name: str, action: str):
    conn = get_conn()
    try:
        conn.execute("INSERT INTO audit_logs (user_name, action) VALUES (?, ?)", (str(user_name or "System"), str(action)))
        conn.commit()
    except DB_ERRORS:
        safe_rollback(conn)
    finally:
        conn.close()


def reset_sequence_if_exists(cur: DBCursor, table: str):
    if DB_ENGINE == "postgres":
        seq = first_val(cur.execute("SELECT pg_get_serial_sequence(?, 'id') AS seq", (table,)).fetchone(), None)
        if seq:
            cur.execute("SELECT setval(?, 1, false)", (seq,))
    elif table_exists(cur, "sqlite_sequence"):
        cur.execute("DELETE FROM sqlite_sequence WHERE name=?", (table,))


def delete_audit_logs(log_ids=None) -> int:
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("BEGIN IMMEDIATE")
        if log_ids is None:
            cur.execute("DELETE FROM audit_logs")
            deleted = max(cur.rowcount, 0)
            reset_sequence_if_exists(cur, "audit_logs")
        else:
            clean_ids = [int(i) for i in log_ids]
            if not clean_ids:
                raise ValueError("กรุณาเลือกรายการ Audit Log อย่างน้อย 1 รายการ")
            cur.execute(f"DELETE FROM audit_logs WHERE id IN ({','.join('?' for _ in clean_ids)})", clean_ids)
            deleted = max(cur.rowcount, 0)
        conn.commit()
        return deleted
    except Exception:
        safe_rollback(conn)
        raise
    finally:
        conn.close()


def get_row_counts() -> dict:
    conn = get_conn()
    try:
        return {t: int(first_val(conn.execute(f'SELECT COUNT(*) AS cnt FROM "{t}"').fetchone(), 0)) for t in ALL_TX_TABLES + ["users"]}
    finally:
        conn.close()


def reset_tables(table_names, actor=None, include_extra=False):
    target_set = set(table_names)
    if target_set - ALLOWED_RESET_TABLES:
        raise ValueError("พบตารางที่ไม่ได้รับอนุญาตให้ลบ")
    conn = get_conn()
    try:
        if DB_ENGINE == "sqlite":
            conn.execute("PRAGMA foreign_keys = OFF")
        cur = conn.cursor()
        cur.execute("BEGIN IMMEDIATE")
        if include_extra and DB_ENGINE == "sqlite":
            all_db = [r["name"] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()]
            keep = {t for t in ("users", "company_settings") if t not in target_set}
            ordered = [t for t in all_db if t not in keep]
        else:
            ordered = [t for t in (ALL_TX_TABLES + ["users", "company_settings"]) if t in target_set and table_exists(cur, t)]
        if not ordered:
            raise ValueError("กรุณาเลือกข้อมูลอย่างน้อย 1 รายการ")
        if "purchase_orders" in target_set and "approvals" not in target_set:
            cur.execute("DELETE FROM approvals WHERE doc_type='PO' AND document_id IS NOT NULL")
        if "expenses" in target_set and "approvals" not in target_set:
            cur.execute("DELETE FROM approvals WHERE doc_type='EXPENSE' AND document_id IS NOT NULL")
        deleted = 0
        for t in ordered:
            cur.execute(f'DELETE FROM "{t}"')
            deleted += max(cur.rowcount, 0)
            if t != "company_settings":
                reset_sequence_if_exists(cur, t)
        if "company_settings" in ordered:
            cur.execute("INSERT INTO company_settings (id) VALUES (1) ON CONFLICT (id) DO NOTHING")
        if actor and "audit_logs" not in target_set and "users" not in target_set:
            cur.execute("INSERT INTO audit_logs (user_name, action) VALUES (?, ?)", (str(actor), f"ล้างข้อมูลตาราง: {', '.join(ordered)}"))
        conn.commit()
        return deleted, ordered
    except Exception:
        safe_rollback(conn)
        raise
    finally:
        if DB_ENGINE == "sqlite":
            try:
                conn.execute("PRAGMA foreign_keys = ON")
            except Exception:
                pass
        conn.close()


def delete_record(table: str, rec_id: int, actor: str, self_id: int = None):
    allowed = {"sales", "products", "crm_customers", "purchase_orders", "expenses", "employees", "journal_entries", "approvals", "audit_logs", "users"}
    if table not in allowed:
        raise ValueError("ไม่สามารถลบข้อมูลจากตารางนี้ได้")
    conn = get_conn()
    try:
        if DB_ENGINE == "sqlite":
            conn.execute("PRAGMA foreign_keys = OFF")
        cur = conn.cursor()
        cur.execute("BEGIN IMMEDIATE")
        if table == "users":
            if self_id is not None and int(rec_id) == int(self_id):
                raise ValueError("ไม่สามารถลบบัญชีที่กำลังใช้งานอยู่ได้")
            tu = cur.execute("SELECT role, status FROM users WHERE id=?", (rec_id,)).fetchone()
            if not tu:
                raise ValueError("ไม่พบบัญชีที่ต้องการลบ")
            if tu["role"] in ADMIN_ROLES and str(tu["status"]).strip().casefold() == "active":
                cnt = int(first_val(cur.execute("SELECT COUNT(*) AS cnt FROM users WHERE role IN ('Admin','Super Admin') AND LOWER(TRIM(status))='active'").fetchone(), 0))
                if cnt <= 1:
                    raise ValueError("ไม่สามารถลบผู้ดูแลระบบที่ใช้งานอยู่คนสุดท้ายได้")
        elif table == "sales":
            cur.execute("DELETE FROM sales_payments WHERE sale_id=?", (rec_id,))
            cur.execute("DELETE FROM sale_items WHERE sale_id=?", (rec_id,))
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
            raise ValueError("ไม่พบรายการที่ต้องการลบ หรือรายการนี้ถูกลบไปแล้ว")
        if table != "audit_logs":
            cur.execute("INSERT INTO audit_logs (user_name, action) VALUES (?, ?)", (str(actor), f"ลบรายการ ID #{rec_id} จากตาราง {table}"))
        conn.commit()
    except Exception:
        safe_rollback(conn)
        raise
    finally:
        if DB_ENGINE == "sqlite":
            try:
                conn.execute("PRAGMA foreign_keys = ON")
            except Exception:
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
        sale = cur.execute("SELECT doc_no, total, net_receivable, status FROM sales WHERE id=?", (sale_id,)).fetchone()
        if not sale or sale["status"] == "ชำระแล้ว":
            raise ValueError("ไม่พบเอกสารหรือเอกสารนี้ชำระครบแล้ว")
        paid = float(first_val(cur.execute("SELECT COALESCE(SUM(amount), 0) AS paid FROM sales_payments WHERE sale_id=?", (sale_id,)).fetchone(), 0.0))
        nr = float(sale["net_receivable"] or 0.0)
        collectible = round(nr if nr > 0 else float(sale["total"]), 2)
        due = round(collectible - paid, 2)
        if due <= 0:
            raise ValueError("เอกสารนี้ชำระครบแล้ว")
        if amount > due:
            raise ValueError(f"ยอดรับชำระเกินยอดคงค้าง ฿{due:,.2f}")
        cur.execute("INSERT INTO sales_payments (sale_id, amount, payment_method, received_by) VALUES (?,?,?,?)", (sale_id, amount, method, actor))
        dr = ("11200", "เงินรับผ่านบัตรเครดิต") if method == "บัตรเครดิต" else ("11100", "เงินสด/เงินฝากธนาคาร")
        desc = f"รับชำระลูกหนี้ {sale['doc_no']}"
        cur.executemany(
            "INSERT INTO journal_entries (entry_date, account_code, account_name, debit, credit, description) VALUES (?,?,?,?,?,?)",
            [(date.today().isoformat(), dr[0], dr[1], amount, 0.0, desc), (date.today().isoformat(), "11300", "ลูกหนี้การค้า", 0.0, amount, desc)],
        )
        if round(paid + amount, 2) >= collectible:
            cur.execute("UPDATE sales SET status='ชำระแล้ว' WHERE id=?", (sale_id,))
        conn.commit()
        return max(round(due - amount, 2), 0.0)
    except Exception:
        safe_rollback(conn)
        raise
    finally:
        conn.close()


def adjust_stock(product_id: int, mv_type: str, qty: int, ref: str, actor: str) -> int:
    if mv_type not in ("Receipt", "Issue") or int(qty) < 1 or not str(ref or "").strip():
        raise ValueError("กรุณาระบุประเภท จำนวน (>0) และเหตุผลให้ครบถ้วน")
    qty = int(qty)
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
            "INSERT INTO inventory_movements (product_id, movement_type, quantity, balance_after, reference, created_by) VALUES (?,?,?,?,?,?)",
            (product_id, mv_type, qty, new_stock, ref.strip(), actor),
        )
        conn.commit()
        return new_stock
    except Exception:
        safe_rollback(conn)
        raise
    finally:
        conn.close()


def receive_po_to_stock(po_id: int, product_id: int, actor: str) -> int:
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("BEGIN IMMEDIATE")
        po = cur.execute("SELECT po_no, qty, status, received_status FROM purchase_orders WHERE id=?", (po_id,)).fetchone()
        if not po or po["status"] != "Approved":
            raise ValueError("รับสินค้าเข้าคลังได้เฉพาะใบสั่งซื้อที่อนุมัติแล้วเท่านั้น")
        if po["received_status"] == "รับสินค้าแล้ว":
            raise ValueError("ใบสั่งซื้อนี้รับสินค้าเข้าคลังไปแล้ว")
        prod = cur.execute("SELECT stock FROM products WHERE id=?", (product_id,)).fetchone()
        if not prod:
            raise ValueError("ไม่พบสินค้าปลายทางในคลัง")
        qty = max(int(po["qty"]), 1)
        new_stock = int(prod["stock"] or 0) + qty
        cur.execute("UPDATE products SET stock=? WHERE id=?", (new_stock, product_id))
        cur.execute(
            "INSERT INTO inventory_movements (product_id, movement_type, quantity, balance_after, reference, created_by) VALUES (?,'Receipt',?,?,?,?)",
            (product_id, qty, new_stock, f"รับสินค้าตาม {po['po_no']}", actor),
        )
        cur.execute("UPDATE purchase_orders SET received_status='รับสินค้าแล้ว', product_id=? WHERE id=?", (product_id, po_id))
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
        row = cur.execute("SELECT doc_type, document_id FROM approvals WHERE id=? AND status='Pending Approval'", (app_id,)).fetchone()
        if not row:
            raise ValueError("คำขอนี้ถูกดำเนินการแล้วหรือไม่พบในระบบ")
        cur.execute("UPDATE approvals SET status=?, approved_by=? WHERE id=? AND status='Pending Approval'", (status, actor, app_id))
        if cur.rowcount != 1:
            raise ValueError("สถานะคำขอเปลี่ยนแปลงแล้ว กรุณาโหลดหน้าใหม่")
        if row["doc_type"] == "PO" and row["document_id"] is not None:
            cur.execute("UPDATE purchase_orders SET status=?, approved_by=? WHERE id=? AND status IN ('Pending Approval','Pending')", (status, actor, row["document_id"]))
        elif row["doc_type"] == "EXPENSE" and row["document_id"] is not None:
            exp = cur.execute("SELECT exp_no, category, description, amount, COALESCE(vat_amount,0) AS vat_amount, COALESCE(wht_amount,0) AS wht_amount FROM expenses WHERE id=? AND status='Pending Approval'", (row["document_id"],)).fetchone()
            if exp:
                cur.execute("UPDATE expenses SET status=?, approved_by=CASE WHEN ?='Approved' THEN ? ELSE NULL END WHERE id=? AND status='Pending Approval'", (status, status, actor, row["document_id"]))
                if status == "Approved":
                    base_amt, vat_amt, wht_amt = round(float(exp["amount"]), 2), round(float(exp["vat_amount"]), 2), round(float(exp["wht_amount"]), 2)
                    ap_amt = round(base_amt + vat_amt - wht_amt, 2)
                    desc = f"รับรู้ค่าใช้จ่าย {exp['exp_no']} · {exp['description']}"
                    td = date.today().isoformat()
                    entries = [(td, "61000", f"ค่าใช้จ่าย - {exp['category']}", base_amt, 0.0, desc)]
                    if vat_amt > 0:
                        entries.append((td, "11500", "ภาษีซื้อ (Input VAT)", vat_amt, 0.0, desc))
                    if ap_amt > 0:
                        entries.append((td, "21100", "เจ้าหนี้การค้า/เจ้าหนี้ค่าใช้จ่าย", 0.0, ap_amt, desc))
                    if wht_amt > 0:
                        entries.append((td, "21500", "ภาษีหัก ณ ที่จ่ายรอนำส่ง (ภ.ง.ด.)", 0.0, wht_amt, desc))
                    cur.executemany("INSERT INTO journal_entries (entry_date, account_code, account_name, debit, credit, description) VALUES (?,?,?,?,?,?)", entries)
        conn.commit()
    except Exception:
        safe_rollback(conn)
        raise
    finally:
        conn.close()


def create_payroll(period: str, actor: str):
    cleaned = str(period or "").strip()
    try:
        if datetime.strptime(cleaned, "%Y-%m").strftime("%Y-%m") != cleaned:
            raise ValueError()
    except ValueError:
        raise ValueError("กรุณาระบุรอบเงินเดือนเป็นรูปแบบ YYYY-MM (เช่น 2026-11)") from None
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("BEGIN IMMEDIATE")
        run_id = insert_returning_id(cur, "INSERT INTO payroll_runs (period, created_by) VALUES (?,?)", (cleaned, actor))
        emps = cur.execute("SELECT id, salary, COALESCE(sso_enabled, 1) AS sso_enabled FROM employees WHERE status='Active'").fetchall()
        if not emps:
            raise ValueError("ไม่มีพนักงานที่ใช้งานอยู่สำหรับรอบเงินเดือนนี้")
        rows = []
        for e in emps:
            gross = round(float(e["salary"]), 2)
            sso = round(min(gross * 0.05, 750.0), 2) if int(e["sso_enabled"]) == 1 and gross > 0 else 0.0
            rows.append((run_id, e["id"], gross, 0.0, sso, 0.0, 0.0, sso, round(max(gross - sso, 0.0), 2)))
        cur.executemany(
            "INSERT INTO payroll_items (payroll_run_id, employee_id, gross_pay, bonus, sso_deduction, tax_deduction, other_deduction, deductions, net_pay) VALUES (?,?,?,?,?,?,?,?,?)",
            rows,
        )
        conn.commit()
        return run_id, len(emps)
    except Exception:
        safe_rollback(conn)
        raise
    finally:
        conn.close()


def update_payroll_item(run_id: int, emp_id: int, bonus: float, sso: float, tax: float, other: float):
    bonus, sso, tax, other = (round(max(float(v), 0.0), 2) for v in (bonus, sso, tax, other))
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("BEGIN IMMEDIATE")
        run = cur.execute("SELECT status FROM payroll_runs WHERE id=?", (run_id,)).fetchone()
        item = cur.execute("SELECT id, gross_pay FROM payroll_items WHERE payroll_run_id=? AND employee_id=?", (run_id, emp_id)).fetchone()
        if not run or run["status"] != "Draft" or not item:
            raise ValueError("ไม่พบรายการเงินเดือนแบบร่างนี้")
        gross_total = round(float(item["gross_pay"]) + bonus, 2)
        total_ded = round(sso + tax + other, 2)
        if total_ded > gross_total:
            raise ValueError(f"ยอดหักรวม (฿{total_ded:,.2f}) เกินรายได้รวม (฿{gross_total:,.2f})")
        cur.execute(
            "UPDATE payroll_items SET bonus=?, sso_deduction=?, tax_deduction=?, other_deduction=?, deductions=?, net_pay=? WHERE id=?",
            (bonus, sso, tax, other, total_ded, round(gross_total - total_ded, 2), item["id"]),
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
        tot = cur.execute(
            "SELECT COUNT(*) AS cnt, COALESCE(SUM(gross_pay),0) AS gross, COALESCE(SUM(bonus),0) AS bonus, COALESCE(SUM(deductions),0) AS ded, COALESCE(SUM(net_pay),0) AS net FROM payroll_items WHERE payroll_run_id=?",
            (run_id,),
        ).fetchone()
        cnt = int(tot["cnt"] or 0)
        total_earn = round(float(tot["gross"] or 0) + float(tot["bonus"] or 0), 2)
        ded, net = round(float(tot["ded"] or 0), 2), round(float(tot["net"] or 0), 2)
        if cnt == 0 or not math.isclose(total_earn, ded + net, abs_tol=0.01):
            raise ValueError("ไม่มีรายการหรือยอดรายได้กับรายการหักไม่สมดุล")
        td = date.today().isoformat()
        entries = []
        if total_earn > 0:
            entries.append((td, "51000", "ค่าใช้จ่ายเงินเดือนและสวัสดิการ", total_earn, 0.0, f"เงินเดือนรอบ {run['period']}"))
        if net > 0:
            entries.append((td, "11100", "เงินสด/เงินฝากธนาคาร", 0.0, net, f"จ่ายเงินเดือนรอบ {run['period']}"))
        if ded > 0:
            entries.append((td, "21400", "หนี้สินรายการหักเงินเดือน/ประกันสังคมค้างจ่าย", 0.0, ded, f"ตั้งหนี้สินรายการหัก {run['period']}"))
        if entries:
            cur.executemany("INSERT INTO journal_entries (entry_date, account_code, account_name, debit, credit, description) VALUES (?,?,?,?,?,?)", entries)
        cur.execute("UPDATE payroll_runs SET status='Paid', paid_at=CURRENT_TIMESTAMP WHERE id=? AND status='Draft'", (run_id,))
        if cur.rowcount != 1:
            raise ValueError("สถานะรอบเงินเดือนเปลี่ยนแปลงแล้ว กรุณาโหลดหน้าใหม่")
        conn.commit()
        return net
    except Exception:
        safe_rollback(conn)
        raise
    finally:
        conn.close()


if not st.session_state.get("_db_ready_v81") or (DB_ENGINE == "sqlite" and not os.path.exists(DB_FILE)):
    try:
        init_db()
        st.session_state["_db_ready_v81"] = True
    except Exception as err:
        st.error(f"ไม่สามารถเชื่อมต่อหรือเตรียมฐานข้อมูลได้ ({DB_ENGINE}): {err}")
        st.info("หากใช้ Supabase กรุณาตรวจสอบว่าใน Streamlit Secrets ใส่ DATABASE_URL แบบ Session/Transaction Pooler (IPv4) และรหัสผ่านถูกต้อง")
        st.stop()

DB_STATUS_LABEL = "🟢 Supabase PostgreSQL (ถาวร)" if DB_ENGINE == "postgres" else "🟡 Local SQLite (ในเครื่อง)"

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
        user_count = int(first_val(conn.execute("SELECT COUNT(*) AS cnt FROM users").fetchone(), 0))
    except Exception as err:
        st.error(f"ไม่สามารถอ่านข้อมูลผู้ใช้ได้: {err}")
        st.stop()
    finally:
        conn.close()

    if user_count == 0:
        show_flash()
        st.markdown("## 🛡️ ตั้งค่าผู้ดูแลระบบคนแรก (Initial Admin Setup)")
        st.info(f"สร้างบัญชี Admin คนแรกเพื่อเริ่มต้นใช้งาน TaxMate ERP v8.1 | ฐานข้อมูล: **{DB_STATUS_LABEL}**")
        with st.form("init_admin_form"):
            u0 = st.text_input("ชื่อผู้ดูแลระบบ (Username)")
            fn0 = st.text_input("ชื่อ-นามสกุล")
            em0 = st.text_input("อีเมล")
            p0 = st.text_input("รหัสผ่าน (อย่างน้อย 4 ตัวอักษร)", type="password")
            p0c = st.text_input("ยืนยันรหัสผ่าน", type="password")
            if st.form_submit_button("สร้างบัญชีผู้ดูแลระบบ (Admin)", type="primary"):
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
                        cur = conn.cursor()
                        cur.execute("BEGIN IMMEDIATE")
                        if int(first_val(cur.execute("SELECT COUNT(*) AS cnt FROM users").fetchone(), 0)) > 0:
                            raise ValueError("มีบัญชีผู้ใช้แล้ว กรุณาเข้าสู่ระบบ")
                        cur.execute(
                            "INSERT INTO users (username, password_hash, full_name, role, department, email, status) VALUES (?,?,?,'Admin','บริหารและจัดการ',?,'Active')",
                            (u0.strip(), hash_password(p0), fn0.strip(), em0.strip()),
                        )
                        conn.commit()
                        created = dict(cur.execute("SELECT * FROM users WHERE username=?", (u0.strip(),)).fetchone())
                    except (ValueError, *DB_ERRORS) as err:
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
        st.markdown("### 🏛️ TaxMate ERP v8.1")
        init_nav = st.radio("📍 เมนูระบบ:", ["🔑 เข้าสู่ระบบ / สมัครสมาชิก", "🏠 หน้าแรก (Overview)"])
        st.divider()
        st.caption(DB_STATUS_LABEL)

    show_flash()

    if init_nav == "🏠 หน้าแรก (Overview)":
        cp = get_company_settings()
        st.markdown(
            f"""<div class="hero-box">
            <span class="hero-pill">🏛️ CLOUD ENTERPRISE MASTER ERP v8.1</span>
            <div class="hero-title">{safe_text(cp['company_name'])}</div>
            <div class="hero-sub">Admin Center • User Portal • Multi-Item e-Tax • ภ.พ.30 • WMS • Payroll • GL</div>
            <div class="hero-desc">ระบบบริหารจัดการองค์กรและบัญชีภาษีไทยครบวงจร รองรับการเชื่อมต่อฐานข้อมูลถาวร Supabase PostgreSQL ฟรี 100% แยกหน้าผู้ดูแลระบบและผู้ใช้งานชัดเจน ออกบิลหลายรายการ ตัดสต็อกอัตโนมัติ คำนวณ VAT/หัก ณ ที่จ่าย สรุป ภ.พ.30 สต็อกเชื่อม PO เงินเดือนประกันสังคมพร้อมสลิป และงบการเงินครบชุด</div>
            </div>""",
            unsafe_allow_html=True,
        )
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown('<div class="card-3d"><b>🛡️ Admin & User Portal</b>แยกหน้าผู้ดูแลระบบ ตั้งค่าบริษัท สำรองข้อมูล ลบ Audit Logs และพอร์ทัลส่วนตัว</div>', unsafe_allow_html=True)
        c2.markdown('<div class="card-3d"><b>🧾 Multi-Item e-Tax & QR</b>บิลหลายรายการ ส่วนลด VAT แยกนอก/รวมใน หัก ณ ที่จ่าย PromptPay QR และใบเสร็จ HTML</div>', unsafe_allow_html=True)
        c3.markdown('<div class="card-3d"><b>🏛️ ศูนย์ภาษีไทย (ภ.พ.30)</b>สรุปภาษีขาย ภาษีซื้อ ยอด ภ.พ.30 และ ภ.ง.ด. รายเดือนพร้อมส่งออก CSV</div>', unsafe_allow_html=True)
        c4.markdown('<div class="card-3d"><b>☁️ Supabase Cloud DB</b>เก็บข้อมูลถาวรบนคลาวด์ PostgreSQL ไม่หายแม้รีบูตแอปบน Streamlit Cloud</div>', unsafe_allow_html=True)
    else:
        st.markdown("## 🔑 ศูนย์ยืนยันตัวตน (Admin & User Login)")
        t_in, t_up = st.tabs(["🔑 เข้าสู่ระบบ (Sign In)", "📝 ลงทะเบียนบัญชี Admin / User (Sign Up)"])
        with t_in:
            st.info("เข้าสู่ระบบได้ทั้งบัญชี **Admin** และ **User** ระบบจะเปิดหน้าให้ตรงกับสิทธิ์โดยอัตโนมัติ")
            with st.form("login_form"):
                u_in = st.text_input("ชื่อผู้ใช้งาน (Username)")
                p_in = st.text_input("รหัสผ่าน (Password)", type="password")
                if st.form_submit_button("เข้าสู่ระบบ", type="primary"):
                    found, db_err = None, False
                    conn = get_conn()
                    try:
                        found = conn.execute("SELECT * FROM users WHERE LOWER(username)=LOWER(?)", (u_in.strip(),)).fetchone()
                    except DB_ERRORS as err:
                        st.error(f"ฐานข้อมูลขัดข้อง: {err}")
                        db_err = True
                    finally:
                        conn.close()
                    if not db_err:
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
                        st.error("รหัสผ่านและการยืนยันรหัสผ่านไม่ตรงกัน")
                    else:
                        ok = False
                        conn = get_conn()
                        try:
                            cur = conn.cursor()
                            cur.execute("BEGIN IMMEDIATE")
                            if username_exists(cur, ru):
                                raise ValueError("ชื่อผู้ใช้นี้มีอยู่แล้ว กรุณาใช้ชื่ออื่น")
                            cur.execute(
                                "INSERT INTO users (username, password_hash, full_name, role, department, email, status) VALUES (?,?,?,?,?,?,'Active')",
                                (ru.strip(), hash_password(rp1), rfn.strip(), rrole, rdept.strip() or "ทั่วไป", rem.strip()),
                            )
                            conn.commit()
                            ok = True
                        except (ValueError, *DB_ERRORS) as err:
                            safe_rollback(conn)
                            st.error(str(err))
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
except DB_ERRORS as err:
    st.error(f"ไม่สามารถตรวจสอบสถานะบัญชีได้: {err}")
    st.stop()
finally:
    conn.close()

if not fetched or str(fetched["status"] or "").strip().casefold() != "active":
    st.session_state.clear()
    st.session_state.authenticated = False
    st.session_state.user = None
    set_flash("error", "บัญชีถูกปิดใช้งานหรือถูกลบ กรุณาเข้าสู่ระบบใหม่")
    st.rerun()

user = dict(fetched)
company = get_company_settings()
st.session_state.user = user
user_role = user.get("role", "User")
is_admin = user_role in ADMIN_ROLES

st.sidebar.title("🏛️ TaxMate ERP v8.1")
st.sidebar.caption(f"🏢 {safe_text(company['company_name'])}")
st.sidebar.caption(DB_STATUS_LABEL)
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
        "📊 Dashboard ผู้บริหาร (BI)": ALL_ROLES,
        "🧾 e-Tax Invoice & POS ขั้นสูง": ALL_ROLES,
        "🏛️ ศูนย์สรุปภาษีไทย (ภ.พ.30 & ภ.ง.ด.)": {"Admin", "Super Admin", "Executive", "Accounting"},
        "🤝 ระบบลูกค้าสัมพันธ์ (CRM & VIP)": ALL_ROLES,
        "📈 คาดการณ์ทางการเงิน (Forecast)": {"Admin", "Super Admin", "Executive", "Accounting"},
        "🛍️ จัดซื้อและรับสินค้า (PO)": ALL_ROLES,
        "💸 คุมงบประมาณและค่าใช้จ่าย (Expenses)": ALL_ROLES,
        "📦 Smart Inventory WMS": ALL_ROLES,
        "👥 HR & Payroll (ปกส./สลิป)": {"Admin", "Super Admin", "HR"},
        "📒 บันทึกบัญชีและงบการเงิน (GL)": {"Admin", "Super Admin", "Accounting"},
        "🛡️ ระบบขออนุมัติ (E-Approval)": ALL_ROLES,
        "🗑️ ล้างข้อมูลระบบ (Reset Data)": ADMIN_ROLES,
    }
else:
    menu_perms = {
        "👤 หน้าผู้ใช้งาน (User Portal)": ALL_ROLES,
        "📊 Dashboard ผู้บริหาร (BI)": ALL_ROLES,
        "🧾 e-Tax Invoice & POS ขั้นสูง": {"User", "Executive", "Accounting", "POS"},
        "🏛️ ศูนย์สรุปภาษีไทย (ภ.พ.30 & ภ.ง.ด.)": {"Executive", "Accounting"},
        "🤝 ระบบลูกค้าสัมพันธ์ (CRM & VIP)": {"User", "Executive", "Accounting", "POS"},
        "📈 คาดการณ์ทางการเงิน (Forecast)": {"Executive", "Accounting"},
        "🛍️ จัดซื้อและรับสินค้า (PO)": {"User", "Executive", "Accounting"},
        "💸 คุมงบประมาณและค่าใช้จ่าย (Expenses)": {"User", "Executive", "Accounting"},
        "📦 Smart Inventory WMS": {"User", "Accounting", "POS"},
        "👥 HR & Payroll (ปกส./สลิป)": {"HR"},
        "📒 บันทึกบัญชีและงบการเงิน (GL)": {"Accounting"},
        "🛡️ ระบบขออนุมัติ (E-Approval)": ALL_ROLES,
    }

avail_menus = [m for m, r in menu_perms.items() if user_role in r] or ["👤 หน้าผู้ใช้งาน (User Portal)"]
app_menu = st.sidebar.radio("ระบบงานหลัก", avail_menus)

st.sidebar.markdown("---")
if ui_button("🚪 ออกจากระบบ", container=st.sidebar, key="btn_logout"):
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
        my_app = read_df(conn, "SELECT id, doc_type AS \"ประเภท\", title AS \"เรื่อง\", amount AS \"งบประมาณ\", status AS \"สถานะ\", approved_by AS \"ผู้อนุมัติ\", created_at AS \"วันที่ส่ง\" FROM approvals WHERE requested_by=? ORDER BY id DESC LIMIT 200", (user["full_name"],))
        my_log = read_df(conn, "SELECT timestamp AS \"เวลา\", action AS \"กิจกรรม\" FROM audit_logs WHERE user_name=? ORDER BY id DESC LIMIT 200", (user["full_name"],))
        my_ps = conn.execute(
            """SELECT pr.period, pr.status, e.emp_code, e.name, e.position, e.department, e.bank_account,
                      pi.gross_pay, pi.bonus, pi.sso_deduction, pi.tax_deduction, pi.other_deduction, pi.deductions, pi.net_pay
               FROM payroll_items pi JOIN payroll_runs pr ON pr.id=pi.payroll_run_id JOIN employees e ON e.id=pi.employee_id
               WHERE LOWER(TRIM(e.name))=LOWER(TRIM(?)) OR (e.email IS NOT NULL AND LOWER(TRIM(e.email))=LOWER(TRIM(?)))
               ORDER BY pr.period DESC""",
            (user["full_name"], user.get("email") or ""),
        ).fetchall()
    finally:
        conn.close()

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("คำขอทั้งหมดของฉัน", f"{len(my_app)} รายการ")
    k2.metric("รออนุมัติ", f"{int((my_app['สถานะ']=='Pending Approval').sum()) if not my_app.empty else 0} รายการ")
    k3.metric("อนุมัติแล้ว", f"{int((my_app['สถานะ']=='Approved').sum()) if not my_app.empty else 0} รายการ")
    k4.metric("สลิปเงินเดือนของฉัน", f"{len(my_ps)} งวด")

    ut1, ut2, ut3, ut4 = st.tabs(["👤 โปรไฟล์และรหัสผ่าน", "📝 คำขออนุมัติของฉัน", "💵 สลิปเงินเดือนของฉัน", "📜 ประวัติของฉัน"])
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
                        old_n, new_n, ok = str(user["full_name"] or ""), efn.strip(), False
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
                        except DB_ERRORS as err:
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
                        conn.execute("INSERT INTO approvals (doc_type, title, amount, requested_by, status) VALUES (?,?,?,?,'Pending Approval')", (qt, qtitle.strip(), round(float(qa), 2), user["full_name"]))
                        conn.commit()
                    finally:
                        conn.close()
                    log_audit(user["full_name"], f"ส่งคำขอจาก User Portal: {qtitle.strip()}")
                    set_flash("success", "ส่งคำขออนุมัติเรียบร้อยแล้ว")
                    st.rerun()
        ui_dataframe(my_app, hide_index=True)
    with ut3:
        if not my_ps:
            st.info("ยังไม่มีสลิปเงินเดือนที่ตรงกับชื่อหรืออีเมลของบัญชีนี้")
        else:
            p_opts = {f"งวด {r['period']} · {r['status']} · สุทธิ ฿{float(r['net_pay']):,.2f}": dict(r) for r in my_ps}
            sel_ps = p_opts[st.selectbox("เลือกงวดเงินเดือน", list(p_opts), key="u_ps_sel")]
            st.download_button("⬇️ ดาวน์โหลดสลิปเงินเดือน (HTML / พิมพ์ PDF)", build_payslip_html(company, sel_ps["period"], sel_ps).encode("utf-8"), f"payslip_{sel_ps['period']}_{sel_ps['emp_code']}.html", "text/html")
    with ut4:
        ui_dataframe(my_log, hide_index=True)

# ------------------------------------------------------------------------------
# MODULE: ADMIN CENTER
# ------------------------------------------------------------------------------
elif app_menu == "🛡️ หน้าผู้ดูแลระบบ (Admin Center)":
    conn = get_conn()
    try:
        df_u = read_df(conn, "SELECT id, username, full_name, role, department, email, status, created_at FROM users ORDER BY id")
        u_rows = conn.execute("SELECT id, username, full_name, role, status FROM users ORDER BY username").fetchall()
        df_log = read_df(conn, "SELECT * FROM audit_logs ORDER BY id DESC LIMIT 2000")
        pend_cnt = int(first_val(conn.execute("SELECT COUNT(*) AS cnt FROM approvals WHERE status='Pending Approval'").fetchone(), 0))
    finally:
        conn.close()

    adm_cnt = int(df_u["role"].isin(["Admin", "Super Admin"]).sum()) if not df_u.empty else 0
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("บัญชีทั้งหมด", f"{len(df_u)} บัญชี")
    k2.metric("ผู้ดูแลระบบ (Admin)", f"{adm_cnt} บัญชี")
    k3.metric("ผู้ใช้งานทั่วไป", f"{len(df_u) - adm_cnt} บัญชี")
    k4.metric("คำขอรออนุมัติ", f"{pend_cnt} รายการ")

    a1, a2, a3, a4 = st.tabs(["👥 จัดการบัญชี Admin & User", "🏢 ตั้งค่าบริษัทและภาษี", "📜 Audit Logs (ลบได้)", "💾 สำรองฐานข้อมูล"])
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
                    elif len(np1) < 4 or np1 != np2:
                        st.error("รหัสผ่านต้องมีอย่างน้อย 4 ตัวอักษรและตรงกันทั้ง 2 ช่อง")
                    else:
                        ok = False
                        conn = get_conn()
                        try:
                            cur = conn.cursor()
                            cur.execute("BEGIN IMMEDIATE")
                            if username_exists(cur, nu):
                                raise ValueError("ชื่อผู้ใช้นี้มีอยู่แล้ว")
                            cur.execute("INSERT INTO users (username, password_hash, full_name, role, department, email, status) VALUES (?,?,?,?,?,?,?)", (nu.strip(), hash_password(np1), nfn.strip(), nrole, ndept.strip(), nem.strip(), nstat))
                            conn.commit()
                            ok = True
                        except (ValueError, *DB_ERRORS) as err:
                            safe_rollback(conn)
                            st.error(str(err))
                        finally:
                            conn.close()
                        if ok:
                            log_audit(user["full_name"], f"สร้างบัญชี {nu.strip()} ({nrole}/{nstat})")
                            set_flash("success", f"ลงทะเบียน {nu.strip()} เรียบร้อยแล้ว")
                            st.rerun()

        ui_dataframe(df_u, hide_index=True)
        if u_rows:
            u_opts = {f"{r['username']} · {r['full_name']} · {r['role']} · {r['status']}": r for r in u_rows}
            sel_u = u_opts[st.selectbox("เลือกบัญชีเพื่อแก้ไขหรือลบ", list(u_opts), key="adm_sel_u")]
            is_self = int(sel_u["id"]) == int(user["id"])
            st_opts = ["Active", "Pending", "Inactive"]
            with st.form("adm_edit_u"):
                erole = st.selectbox("บทบาท", ADMIN_EDIT_ROLES, index=ADMIN_EDIT_ROLES.index(sel_u["role"]) if sel_u["role"] in ADMIN_EDIT_ROLES else 2, format_func=role_label, disabled=is_self, key=f"er_{sel_u['id']}")
                estat = st.selectbox("สถานะ", st_opts, index=st_opts.index(sel_u["status"]) if sel_u["status"] in st_opts else 0, disabled=is_self, key=f"es_{sel_u['id']}")
                rpw = st.text_input("ตั้งรหัสผ่านใหม่ (เว้นว่างหากไม่เปลี่ยน)", type="password", key=f"ep_{sel_u['id']}")
                if st.form_submit_button("💾 บันทึกบัญชีผู้ใช้", type="primary"):
                    if rpw and len(rpw) < 4:
                        st.error("รหัสผ่านใหม่ต้องมีอย่างน้อย 4 ตัวอักษร")
                    else:
                        ok, f_role, f_stat = False, sel_u["role"], sel_u["status"]
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
                                cnt = int(first_val(cur.execute("SELECT COUNT(*) AS cnt FROM users WHERE role IN ('Admin','Super Admin') AND LOWER(TRIM(status))='active'").fetchone(), 0))
                                if cnt <= 1:
                                    raise ValueError("ไม่สามารถลดสิทธิ์หรือปิดใช้งานผู้ดูแลระบบคนสุดท้ายได้")
                            if rpw:
                                cur.execute("UPDATE users SET role=?, status=?, password_hash=? WHERE id=?", (f_role, f_stat, hash_password(rpw), sel_u["id"]))
                            else:
                                cur.execute("UPDATE users SET role=?, status=? WHERE id=?", (f_role, f_stat, sel_u["id"]))
                            conn.commit()
                            ok = True
                        except (ValueError, *DB_ERRORS) as err:
                            safe_rollback(conn)
                            st.error(str(err))
                        finally:
                            conn.close()
                        if ok:
                            log_audit(user["full_name"], f"แก้ไขบัญชี {sel_u['username']} -> {f_role}/{f_stat}")
                            set_flash("success", "บันทึกบัญชีผู้ใช้เรียบร้อยแล้ว")
                            st.rerun()
            if not is_self:
                with st.expander(f"🗑️ ลบบัญชีผู้ใช้ '{sel_u['username']}'"):
                    with st.form(f"adm_del_u_{sel_u['id']}"):
                        chk_du = st.checkbox(f"ยืนยันลบบัญชี {sel_u['username']} ({sel_u['full_name']}) อย่างถาวร")
                        if st.form_submit_button("🗑️ ลบบัญชีผู้ใช้นี้", type="primary"):
                            if not chk_du:
                                st.error("กรุณาติ๊กยืนยันก่อนลบบัญชี")
                            else:
                                try:
                                    delete_record("users", int(sel_u["id"]), user["full_name"], self_id=int(user["id"]))
                                except (ValueError, *DB_ERRORS) as err:
                                    st.error(str(err))
                                else:
                                    set_flash("success", f"ลบบัญชี {sel_u['username']} เรียบร้อยแล้ว")
                                    st.rerun()

    with a2:
        st.subheader("🏢 ข้อมูลองค์กรสำหรับหัวเอกสาร e-Tax และสลิปเงินเดือน")
        with st.form("company_settings_form"):
            cs1, cs2 = st.columns(2)
            with cs1:
                c_name = st.text_input("ชื่อบริษัท / กิจการ", value=str(company.get("company_name") or ""))
                c_tax = st.text_input("เลขประจำตัวผู้เสียภาษี 13 หลัก", value=str(company.get("tax_id") or ""))
                c_branch = st.text_input("สาขา", value=str(company.get("branch_name") or "สำนักงานใหญ่"))
                c_phone = st.text_input("เบอร์โทรศัพท์", value=str(company.get("phone") or ""))
            with cs2:
                c_email = st.text_input("อีเมลองค์กร", value=str(company.get("email") or ""))
                c_pp = st.text_input("PromptPay เริ่มต้นของบริษัท (10/13/15 หลัก)", value=str(company.get("default_promptpay") or ""))
                c_vat = st.number_input("อัตรา VAT เริ่มต้น (%)", min_value=0.0, max_value=20.0, value=float(company.get("default_vat_rate") or 7.0), step=0.5)
                c_wht = st.number_input("อัตราหัก ณ ที่จ่ายเริ่มต้น (%)", min_value=0.0, max_value=15.0, value=float(company.get("default_wht_rate") or 3.0), step=0.5)
            c_addr = st.text_area("ที่อยู่บริษัท (แสดงบนใบกำกับภาษี)", value=str(company.get("address") or ""))
            if st.form_submit_button("💾 บันทึกข้อมูลบริษัท", type="primary"):
                if not c_name.strip():
                    st.error("กรุณาระบุชื่อบริษัท")
                else:
                    conn = get_conn()
                    try:
                        conn.execute(
                            "UPDATE company_settings SET company_name=?, tax_id=?, branch_name=?, address=?, phone=?, email=?, default_promptpay=?, default_vat_rate=?, default_wht_rate=?, updated_at=CURRENT_TIMESTAMP WHERE id=1",
                            (c_name.strip(), c_tax.strip(), c_branch.strip(), c_addr.strip(), c_phone.strip(), c_email.strip(), c_pp.strip(), float(c_vat), float(c_wht)),
                        )
                        conn.commit()
                    finally:
                        conn.close()
                    log_audit(user["full_name"], "อัปเดตข้อมูลบริษัทและการตั้งค่าภาษี")
                    set_flash("success", "บันทึกข้อมูลบริษัทเรียบร้อยแล้ว")
                    st.rerun()

    with a3:
        log_q = st.text_input("🔍 ค้นหา Audit Logs (ชื่อผู้ใช้ / กิจกรรม)", key="log_search")
        df_lv = df_log.copy()
        if log_q.strip() and not df_lv.empty:
            df_lv = df_lv[df_lv["user_name"].fillna("").astype(str).str.contains(log_q.strip(), case=False, na=False) | df_lv["action"].fillna("").astype(str).str.contains(log_q.strip(), case=False, na=False)]
        ui_dataframe(df_lv, hide_index=True)
        if not df_log.empty:
            st.download_button("⬇️ ดาวน์โหลด Audit Logs (CSV)", df_lv.to_csv(index=False).encode("utf-8-sig"), f"taxmate_audit_{date.today().isoformat()}.csv", "text/csv")
            st.markdown("---")
            st.subheader("🗑️ ลบประวัติ Audit Logs")
            cd1, cd2 = st.columns(2)
            with cd1:
                lmap = {f"#{int(r['id'])} · {r['user_name']} · {r['action']} · {r['timestamp']}": int(r["id"]) for _, r in df_lv.iterrows()}
                with st.form("del_sel_logs"):
                    picked = st.multiselect("เลือกรายการที่ต้องการลบ (เลือกได้หลายรายการ)", list(lmap.keys()))
                    if st.form_submit_button("🗑️ ลบรายการที่เลือก", type="primary"):
                        if not picked:
                            st.error("กรุณาเลือกรายการอย่างน้อย 1 รายการ")
                        else:
                            removed = delete_audit_logs([lmap[k] for k in picked])
                            set_flash("success", f"ลบ Audit Logs เรียบร้อยแล้ว ({removed:,} รายการ)")
                            st.rerun()
            with cd2:
                with st.form("clr_all_logs"):
                    st.caption(f"ล้างประวัติการใช้งานทั้งหมด {len(df_log):,} รายการให้เหลือ 0")
                    chk_cl = st.checkbox("ยืนยันลบ Audit Logs ทั้งหมดอย่างถาวร")
                    if st.form_submit_button("🔥 ล้าง Audit Logs ทั้งหมด", type="primary"):
                        if not chk_cl:
                            st.error("กรุณาติ๊กยืนยันก่อนล้างประวัติทั้งหมด")
                        else:
                            removed = delete_audit_logs(None)
                            set_flash("success", f"ล้างประวัติ Audit Logs ทั้งหมดเรียบร้อยแล้ว ({removed:,} รายการ)")
                            st.rerun()
        else:
            st.info("ไม่มีรายการ Audit Logs ในระบบ")

    with a4:
        st.subheader("💾 สำรองข้อมูลทั้งหมด")
        st.info(f"โหมดฐานข้อมูลปัจจุบัน: **{DB_STATUS_LABEL}**")
        if DB_ENGINE == "sqlite" and os.path.exists(DB_FILE):
            with open(DB_FILE, "rb") as f:
                db_bytes = f.read()
            st.metric("ขนาดไฟล์ฐานข้อมูล SQLite", f"{len(db_bytes) / 1024:,.1f} KB")
            st.download_button("⬇️ ดาวน์โหลดไฟล์ฐานข้อมูล (.db)", db_bytes, f"taxmate_backup_{date.today().isoformat()}.db", "application/octet-stream")
        st.download_button(
            "📦 ดาวน์โหลดข้อมูลทั้งหมดทุกตาราง (.zip รวม CSV)",
            build_zip_backup(),
            file_name=f"taxmate_full_backup_{date.today().isoformat()}.zip",
            mime="application/zip",
        )

# ------------------------------------------------------------------------------
# MODULE: EXECUTIVE BI DASHBOARD
# ------------------------------------------------------------------------------
elif app_menu == "📊 Dashboard ผู้บริหาร (BI)":
    pf = st.radio("📅 ช่วงเวลาวิเคราะห์:", ["ทั้งหมด", "เดือนนี้", "ปีนี้"], horizontal=True)
    m_pref, y_pref = date.today().strftime("%Y-%m"), date.today().strftime("%Y")
    conn = get_conn()
    try:
        df_s = read_df(conn, "SELECT * FROM sales")
        df_p = read_df(conn, "SELECT * FROM products")
        df_e = read_df(conn, "SELECT * FROM expenses WHERE status='Approved'")
        df_pay = read_df(conn, "SELECT sale_id, SUM(amount) AS paid FROM sales_payments GROUP BY sale_id")
        df_pr = read_df(conn, "SELECT pr.period, SUM(pi.gross_pay + pi.bonus) AS cost FROM payroll_runs pr JOIN payroll_items pi ON pi.payroll_run_id=pr.id WHERE pr.status='Paid' GROUP BY pr.period")
        pend = int(first_val(conn.execute("SELECT COUNT(*) AS cnt FROM approvals WHERE status='Pending Approval'").fetchone(), 0))
    finally:
        conn.close()

    def fdate(df, col="created_at"):
        if df.empty or col not in df.columns:
            return df
        s = df[col].fillna("").astype(str)
        return df[s.str.startswith(m_pref)] if pf == "เดือนนี้" else (df[s.str.startswith(y_pref)] if pf == "ปีนี้" else df)

    df_sf, df_ef = fdate(df_s), fdate(df_e)
    tot_rev = float(df_sf["amount"].fillna(0).sum()) if not df_sf.empty else 0.0
    tot_gross = float(df_sf["total"].fillna(0).sum()) if not df_sf.empty else 0.0
    tot_vat = float(df_sf["tax"].fillna(0).sum()) if not df_sf.empty else 0.0
    tot_exp = float(df_ef["amount"].fillna(0).sum()) if not df_ef.empty else 0.0
    pr_cost = float((df_pr[df_pr["period"] == m_pref] if pf == "เดือนนี้" else (df_pr[df_pr["period"].astype(str).str.startswith(y_pref)] if pf == "ปีนี้" else df_pr))["cost"].sum()) if not df_pr.empty else 0.0
    stk_val = float((df_p["price"].fillna(0) * df_p["stock"].fillna(0)).sum()) if not df_p.empty else 0.0

    ar_due = 0.0
    if not df_s.empty:
        sar = df_s.copy()
        sar["coll"] = sar["net_receivable"].fillna(0.0)
        sar.loc[sar["coll"] <= 0, "coll"] = sar["total"].fillna(0.0)
        if not df_pay.empty:
            sar = sar.merge(df_pay, left_on="id", right_on="sale_id", how="left")
            sar["paid"] = sar["paid"].fillna(0.0)
        else:
            sar["paid"] = 0.0
        sar["due"] = (sar["coll"] - sar["paid"]).clip(lower=0.0)
        ar_due = float(sar[sar["status"] != "ชำระแล้ว"]["due"].sum())

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("ยอดขายรวม VAT", f"฿{tot_gross:,.2f}")
    m2.metric("กำไรเบื้องต้น", f"฿{tot_rev - tot_exp - pr_cost:,.2f}")
    m3.metric("ภาษีขาย VAT", f"฿{tot_vat:,.2f}")
    m4.metric("ลูกหนี้ค้างรับ (AR)", f"฿{ar_due:,.2f}")
    m5.metric("มูลค่าสต็อกรวม", f"฿{stk_val:,.2f}")
    m6.metric("รออนุมัติ", f"{pend} รายการ")

    if not df_p.empty:
        low = df_p[df_p["stock"].fillna(0).astype(int) <= df_p["min_stock"].fillna(10).astype(int)]
        if not low.empty:
            st.warning(f"⚠️ สินค้าต่ำกว่าเกณฑ์ {len(low)} รายการ: " + ", ".join(f"{r.name} (เหลือ {int(r.stock)})" for r in low.itertuples()))

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📈 รายได้ vs ค่าใช้จ่ายรายเดือน")
        rm = df_sf.assign(period=df_sf["created_at"].fillna("").astype(str).str[:7]).groupby("period", as_index=False)["amount"].sum().rename(columns={"amount": "รายได้"}) if not df_sf.empty else pd.DataFrame(columns=["period", "รายได้"])
        em = df_ef.assign(period=df_ef["created_at"].fillna("").astype(str).str[:7]).groupby("period", as_index=False)["amount"].sum().rename(columns={"amount": "ค่าใช้จ่าย"}) if not df_ef.empty else pd.DataFrame(columns=["period", "ค่าใช้จ่าย"])
        mg = pd.merge(rm, em, on="period", how="outer").fillna(0.0).sort_values("period")
        if not mg.empty:
            ui_plotly(px.bar(mg, x="period", y=["รายได้", "ค่าใช้จ่าย"], barmode="group", title="เปรียบเทียบรายได้และค่าใช้จ่ายรายเดือน"))
        else:
            st.info("ยังไม่มีข้อมูลสำหรับเปรียบเทียบรายเดือน")
    with c2:
        st.subheader("📊 สัดส่วนสถานะการชำระเงิน")
        if not df_sf.empty:
            ss = df_sf.assign(status=df_sf["status"].fillna("ไม่ระบุ"), total=df_sf["total"].fillna(0.0)).groupby("status", as_index=False)["total"].sum()
            ss = ss[ss["total"] > 0]
            if not ss.empty:
                ui_plotly(px.pie(ss, names="status", values="total", hole=0.4))
            else:
                st.info("ยังไม่มีข้อมูลยอดชำระเงิน")
        else:
            st.info("ยังไม่มีข้อมูลการขาย")

    c3, c4 = st.columns(2)
    with c3:
        st.subheader("🏆 ลูกค้ายอดซื้อสูงสุด (Top 5)")
        if not df_sf.empty:
            ui_plotly(px.bar(df_sf.groupby("customer", as_index=False)["total"].sum().sort_values("total", ascending=False).head(5), x="total", y="customer", orientation="h"))
        else:
            st.info("ยังไม่มีข้อมูลยอดขายลูกค้า")
    with c4:
        st.subheader("📦 มูลค่าสินค้าคงคลังตามหมวดหมู่")
        if not df_p.empty:
            pv = df_p.assign(val=df_p["price"].fillna(0) * df_p["stock"].fillna(0)).groupby("category", as_index=False)["val"].sum()
            pv = pv[pv["val"] > 0]
            if not pv.empty:
                ui_plotly(px.pie(pv, names="category", values="val", hole=0.38))
            else:
                st.info("ยังไม่มีมูลค่าสินค้าคงคลัง")
        else:
            st.info("ยังไม่มีข้อมูลสินค้า")

# ------------------------------------------------------------------------------
# MODULE: E-TAX INVOICE & POS ขั้นสูง
# ------------------------------------------------------------------------------
elif app_menu == "🧾 e-Tax Invoice & POS ขั้นสูง":
    if "etax_cart" not in st.session_state:
        st.session_state.etax_cart = []
    conn = get_conn()
    try:
        crm_rows = conn.execute("SELECT id, cust_code, name, tax_id FROM crm_customers ORDER BY name").fetchall()
        prod_rows = conn.execute("SELECT id, sku, name, price, stock, unit FROM products ORDER BY name").fetchall()
    finally:
        conn.close()

    c1, c2 = st.columns([1.15, 1])
    with c1:
        st.subheader("📝 สร้างใบกำกับภาษี / ใบเสร็จ (รองรับหลายรายการ)")
        d_no = gen_input("เลขที่เอกสาร", "etax_doc_no", lambda: f"INV-{date.today():%Y%m%d}-{uuid.uuid4().hex[:8].upper()}")
        c_list = ["-- กรอกชื่อลูกค้าเอง --"] + [f"{r['cust_code']} · {r['name']}" for r in crm_rows]
        picked_c = st.selectbox("ดึงข้อมูลลูกค้าจาก CRM (ไม่บังคับ)", c_list, key="etax_crm_pick")
        mc = next((r for r in crm_rows if f"{r['cust_code']} · {r['name']}" == picked_c), None)
        cust = st.text_input("ชื่อลูกค้า / นิติบุคคล", value=mc["name"] if mc else "บริษัท สยามเทคโนโลยี จำกัด", key=f"etax_cust_{picked_c}")
        tax_id = st.text_input("เลขประจำตัวผู้เสียภาษีลูกค้า (13 หลัก)", value=(mc["tax_id"] or "") if mc else "", key=f"etax_tid_{picked_c}")

        with st.container(border=True):
            st.markdown("##### 🛒 รายการสินค้า / บริการในบิล")
            p_opts = ["-- พิมพ์รายการเอง --"] + [f"{r['sku']} · {r['name']} (฿{float(r['price']):,.2f} | เหลือ {int(r['stock'])})" for r in prod_rows]
            sel_pl = st.selectbox("เลือกสินค้าจากสต็อก หรือพิมพ์รายการเอง", p_opts, key="cart_prod_pick")
            mp = next((r for r in prod_rows if f"{r['sku']} · {r['name']} (฿{float(r['price']):,.2f} | เหลือ {int(r['stock'])})" == sel_pl), None)
            ic1, ic2, ic3 = st.columns([2, 1, 1])
            with ic1:
                ilbl = st.text_input("ชื่อรายการ", value=mp["name"] if mp else "", key=f"ci_n_{sel_pl}")
            with ic2:
                iqty = st.number_input("จำนวน", min_value=1, value=1, step=1, key="ci_q")
            with ic3:
                iprc = st.number_input("ราคา/หน่วย", min_value=0.0, value=float(mp["price"]) if mp else 1000.0, step=100.0, key=f"ci_p_{sel_pl}")
            b1, b2 = st.columns(2)
            with b1:
                if ui_button("➕ เพิ่มรายการลงบิล", key="btn_add_cart"):
                    if not ilbl.strip():
                        st.error("กรุณาระบุชื่อรายการ")
                    else:
                        st.session_state.etax_cart.append({"product_id": int(mp["id"]) if mp else None, "item_name": ilbl.strip(), "qty": int(iqty), "unit_price": round(float(iprc), 2), "line_total": round(int(iqty) * float(iprc), 2)})
                        st.rerun()
            with b2:
                if ui_button("🧹 ล้างตะกร้า", key="btn_clr_cart") and st.session_state.etax_cart:
                    st.session_state.etax_cart = []
                    st.rerun()

        if st.session_state.etax_cart:
            ui_dataframe(pd.DataFrame([{"รายการ": x["item_name"], "จำนวน": x["qty"], "ราคา/หน่วย": x["unit_price"], "รวม": x["line_total"]} for x in st.session_state.etax_cart]), hide_index=True)
            sub_val = round(sum(x["line_total"] for x in st.session_state.etax_cart), 2)
            deduct_stk = st.checkbox("ตัดสต็อกสินค้าอัตโนมัติสำหรับรายการที่เลือกจากคลัง", value=True, key="etax_ded_stk")
        else:
            sub_val = round(float(st.number_input("มูลค่ารวมก่อนส่วนลด (กรณีไม่ออกแยกรายการ)", min_value=0.01, value=10000.0, step=500.0, key="etax_man_amt")), 2)
            deduct_stk = False

        tx1, tx2, tx3 = st.columns(3)
        with tx1:
            disc_v = st.number_input("ส่วนลด (บาท)", min_value=0.0, max_value=max(sub_val, 0.01), value=0.0, step=100.0, key="etax_disc")
        with tx2:
            v_mode = st.selectbox("โหมดภาษี VAT", ["แยกนอก (Exclude VAT)", "รวมใน (Include VAT)", "ยกเว้น VAT (0%)"], key="etax_vm")
        with tx3:
            w_rate = st.selectbox("หัก ณ ที่จ่าย (WHT %)", [0.0, 1.0, 2.0, 3.0, 5.0], key="etax_wr")

        pm1, pm2, pm3 = st.columns(3)
        with pm1:
            pm = st.selectbox("ช่องทางชำระเงิน", ["โอนเงินผ่านธนาคาร", "PromptPay", "บัตรเครดิต", "เงินสด"], key="etax_pm")
        with pm2:
            st_val = st.selectbox("สถานะ", ["ชำระแล้ว", "รอชำระ"], index=1, key="etax_st")
        with pm3:
            due_dt = st.date_input("วันครบกำหนด", value=date.today() + timedelta(days=30), key="etax_due")

        pp_id = st.text_input("PromptPay (10/13/15 หลัก)", value=str(company.get("default_promptpay") or ""), key="etax_pp") if pm == "PromptPay" else ""
        notes = st.text_input("หมายเหตุท้ายบิล (ไม่บังคับ)", key="etax_notes")
        calc = compute_invoice_totals(sub_val, disc_v, v_mode, float(company.get("default_vat_rate") or 7.0), float(w_rate))

        if ui_button("💾 บันทึกและออกใบกำกับภาษี", type="primary", key="btn_save_etax"):
            valid = True
            if not d_no.strip() or not cust.strip() or calc["total"] <= 0:
                st.error("กรุณาระบุเลขที่เอกสาร ชื่อลูกค้า และยอดรวมให้ถูกต้อง")
                valid = False
            elif pm == "PromptPay":
                try:
                    promptpay_payload(pp_id, calc["net_receivable"] or calc["total"])
                except ValueError as err:
                    st.error(str(err))
                    valid = False
            if valid:
                ok = False
                conn = get_conn()
                try:
                    cur = conn.cursor()
                    cur.execute("BEGIN IMMEDIATE")
                    sid = insert_returning_id(
                        cur,
                        """INSERT INTO sales (doc_no, customer, customer_tax_id, amount, tax, total, status, payment_method,
                           discount, vat_mode, wht_rate, wht_amount, net_receivable, due_date, notes, created_by)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (d_no.strip(), cust.strip(), tax_id.strip() or None, calc["amount"], calc["vat"], calc["total"], st_val, pm, calc["discount"], v_mode, float(w_rate), calc["wht_amount"], calc["net_receivable"], str(due_dt), notes.strip() or None, user["full_name"]),
                    )
                    for ci in st.session_state.etax_cart:
                        cur.execute("INSERT INTO sale_items (sale_id, product_id, item_name, qty, unit_price, line_total) VALUES (?,?,?,?,?,?)", (sid, ci["product_id"], ci["item_name"], ci["qty"], ci["unit_price"], ci["line_total"]))
                        if deduct_stk and ci["product_id"] is not None:
                            pr = cur.execute("SELECT stock, name FROM products WHERE id=?", (ci["product_id"],)).fetchone()
                            if pr:
                                cs = int(pr["stock"] or 0)
                                if ci["qty"] > cs:
                                    raise ValueError(f"สต็อก '{pr['name']}' ไม่เพียงพอ (คงเหลือ {cs})")
                                cur.execute("UPDATE products SET stock=? WHERE id=?", (cs - ci["qty"], ci["product_id"]))
                                cur.execute("INSERT INTO inventory_movements (product_id, movement_type, quantity, balance_after, reference, created_by) VALUES (?,'Issue',?,?,?,?)", (ci["product_id"], ci["qty"], cs - ci["qty"], f"ขายตาม {d_no.strip()}", user["full_name"]))
                    dr = ("11300", "ลูกหนี้การค้า") if st_val != "ชำระแล้ว" else (("11200", "เงินรับผ่านบัตรเครดิต") if pm == "บัตรเครดิต" else ("11100", "เงินสด/เงินฝากธนาคาร"))
                    if st_val == "ชำระแล้ว" and calc["net_receivable"] > 0:
                        cur.execute("INSERT INTO sales_payments (sale_id, amount, payment_method, received_by) VALUES (?,?,?,?)", (sid, calc["net_receivable"], pm, user["full_name"]))
                    td, jrows = date.today().isoformat(), []
                    if calc["net_receivable"] > 0:
                        jrows.append((td, dr[0], dr[1], calc["net_receivable"], 0.0, f"รับรู้ยอดขาย {d_no.strip()}"))
                    if calc["wht_amount"] > 0:
                        jrows.append((td, "11400", "ภาษีเงินได้หัก ณ ที่จ่ายถูกหัก", calc["wht_amount"], 0.0, f"WHT {d_no.strip()}"))
                    if calc["amount"] > 0:
                        jrows.append((td, "41100", "รายได้จากการขายและบริการ", 0.0, calc["amount"], f"รับรู้ยอดขาย {d_no.strip()}"))
                    if calc["vat"] > 0:
                        jrows.append((td, "21300", "ภาษีขาย (Output VAT)", 0.0, calc["vat"], f"ภาษีขาย {d_no.strip()}"))
                    cur.executemany("INSERT INTO journal_entries (entry_date, account_code, account_name, debit, credit, description) VALUES (?,?,?,?,?,?)", jrows)
                    conn.commit()
                    ok = True
                except (ValueError, *DB_ERRORS) as err:
                    safe_rollback(conn)
                    st.error(str(err))
                finally:
                    conn.close()
                if ok:
                    log_audit(user["full_name"], f"ออกใบกำกับภาษี {d_no.strip()} (฿{calc['total']:,.2f})")
                    st.session_state.etax_cart = []
                    queue_input("etax_doc_no", f"INV-{date.today():%Y%m%d}-{uuid.uuid4().hex[:8].upper()}")
                    set_flash("success", f"บันทึกเอกสาร {d_no.strip()} เรียบร้อยแล้ว!")
                    st.rerun()

    with c2:
        st.subheader("🧾 ตัวอย่างเอกสาร (Live Preview)")
        it_rows = "".join(f"<tr><td>{i}. {safe_text(ci['item_name'])}</td><td class='num'>{ci['qty']}</td><td class='num'>฿{ci['line_total']:,.2f}</td></tr>" for i, ci in enumerate(st.session_state.etax_cart, 1))
        it_tbl = f"<table><thead><tr><th>รายการ</th><th class='num'>จำนวน</th><th class='num'>รวม</th></tr></thead><tbody>{it_rows}</tbody></table>" if it_rows else ""
        st.markdown(
            f"""<div class="receipt-paper">
            <div style="text-align:center; font-weight:800; font-size:17px; color:#1E3A8A;">{safe_text(company['company_name'])}</div>
            <div style="text-align:center; font-size:12px; color:#64748B;">เลขผู้เสียภาษี: {safe_text(company['tax_id'])} ({safe_text(company['branch_name'])})</div>
            <div style="text-align:center; font-weight:700; margin-top:6px;">ใบกำกับภาษี / ใบเสร็จรับเงิน</div><hr>
            <div><b>เลขที่:</b> {safe_text(d_no)} | <b>ครบกำหนด:</b> {safe_text(str(due_dt))}</div>
            <div><b>ลูกค้า:</b> {safe_text(cust)} | <b>เลขผู้เสียภาษี:</b> {safe_text(tax_id.strip() or '-')}</div>
            {it_tbl}<hr>
            <div>ส่วนลด: <b>-฿{calc['discount']:,.2f}</b> | ก่อน VAT: <b>฿{calc['amount']:,.2f}</b> | VAT: <b>฿{calc['vat']:,.2f}</b></div>
            <div>รวมทั้งสิ้น: <b>฿{calc['total']:,.2f}</b> | หัก ณ ที่จ่าย ({float(w_rate):.1f}%): <b>-฿{calc['wht_amount']:,.2f}</b></div>
            <h4 style="color:#2563EB; margin:8px 0 0 0;">ยอดสุทธิที่ต้องชำระ: ฿{calc['net_receivable']:,.2f}</h4>
            </div>""",
            unsafe_allow_html=True,
        )
        if pm == "PromptPay" and pp_id.strip():
            try:
                st.subheader("💳 Dynamic PromptPay QR Code")
                st.image(qr_png_bytes(promptpay_payload(pp_id, calc["net_receivable"] or calc["total"])), caption=f"สแกนชำระเงิน ฿{calc['net_receivable']:,.2f}", width=240)
            except (ValueError, RuntimeError) as err:
                st.error(str(err))
        elif pm == "PromptPay":
            st.info("กรอกเลข PromptPay ด้านซ้ายเพื่อสร้าง QR Code")

    st.markdown("---")
    conn = get_conn()
    try:
        df_sales = read_df(conn, "SELECT id, doc_no, customer, customer_tax_id, amount, tax, total, COALESCE(wht_amount,0) AS wht_amount, COALESCE(NULLIF(net_receivable,0), total) AS net_receivable, status, payment_method, due_date, created_at FROM sales ORDER BY id DESC")
        raw_open = conn.execute(
            """SELECT s.id, s.doc_no, s.customer, s.total, s.net_receivable, COALESCE(p.paid,0) AS paid
               FROM sales s LEFT JOIN (SELECT sale_id, SUM(amount) AS paid FROM sales_payments GROUP BY sale_id) p ON p.sale_id=s.id
               WHERE s.status != 'ชำระแล้ว' ORDER BY s.id DESC"""
        ).fetchall()
    finally:
        conn.close()

    open_rows = []
    for r in raw_open:
        nr = float(r["net_receivable"] or 0.0)
        coll = round(nr if nr > 0 else float(r["total"]), 2)
        due_amt = round(coll - float(r["paid"] or 0.0), 2)
        if due_amt >= 0.01:
            d = dict(r)
            d["collectible"] = coll
            d["due"] = due_amt
            open_rows.append(d)

    st.subheader("📋 รายการใบกำกับภาษีทั้งหมด & พิมพ์เอกสาร")
    sf1, sf2 = st.columns([2, 1])
    with sf1:
        sq = st.text_input("🔍 ค้นหาเลขที่บิล / ชื่อลูกค้า", key="sales_q")
    with sf2:
        ssf = st.selectbox("กรองสถานะ", ["ทั้งหมด", "ชำระแล้ว", "รอชำระ"], key="sales_sf")
    df_sv = df_sales.copy()
    if sq.strip() and not df_sv.empty:
        df_sv = df_sv[df_sv["doc_no"].astype(str).str.contains(sq.strip(), case=False, na=False) | df_sv["customer"].astype(str).str.contains(sq.strip(), case=False, na=False)]
    if ssf != "ทั้งหมด" and not df_sv.empty:
        df_sv = df_sv[df_sv["status"] == ssf]
    ui_dataframe(df_sv.drop(columns=["id"], errors="ignore"), hide_index=True)

    if not df_sv.empty:
        d1, d2 = st.columns([1, 2])
        with d1:
            st.download_button("⬇️ ดาวน์โหลดรายงานขาย (CSV)", df_sv.to_csv(index=False).encode("utf-8-sig"), f"taxmate_sales_{date.today().isoformat()}.csv", "text/csv")
        with d2:
            pmap = {f"{r['doc_no']} · {r['customer']} · ฿{float(r['total']):,.2f}": int(r["id"]) for _, r in df_sv.iterrows()}
            sp_id = pmap[st.selectbox("เลือกเอกสารเพื่อดาวน์โหลดใบกำกับภาษี (HTML/PDF)", list(pmap), key="pr_inv_sel")]
            conn = get_conn()
            try:
                sf_row = dict(conn.execute("SELECT * FROM sales WHERE id=?", (sp_id,)).fetchone())
                si_rows = [dict(x) for x in conn.execute("SELECT * FROM sale_items WHERE sale_id=?", (sp_id,)).fetchall()]
            finally:
                conn.close()
            st.download_button("🖨️ ดาวน์โหลดใบกำกับภาษีพร้อมพิมพ์ (HTML)", build_invoice_html(company, sf_row, si_rows).encode("utf-8"), f"{sf_row['doc_no']}.html", "text/html")

    if open_rows:
        st.subheader("💳 รับชำระใบแจ้งหนี้ค้างรับ")
        s_opts = {f"{r['doc_no']} · {r['customer']} · ค้าง ฿{r['due']:,.2f}": r for r in open_rows}
        sel_s = s_opts[st.selectbox("เลือกเอกสารค้างชำระ", list(s_opts), key="ar_sel")]
        due = sel_s["due"]
        with st.form("ar_pay_form"):
            rm = st.selectbox("ช่องทางรับชำระ", ["เงินสด", "โอนเงินผ่านธนาคาร", "บัตรเครดิต", "PromptPay"])
            ra = st.number_input(f"ยอดรับชำระ (ยอดคงค้าง ฿{due:,.2f})", min_value=0.01, max_value=max(due, 0.02), value=max(due, 0.01), key=f"ar_{sel_s['id']}_{due:.2f}")
            if st.form_submit_button("บันทึกรับชำระ", type="primary"):
                try:
                    rem_due = record_payment(sel_s["id"], ra, rm, user["full_name"])
                except (ValueError, *DB_ERRORS) as err:
                    st.error(str(err))
                else:
                    log_audit(user["full_name"], f"รับชำระ {sel_s['doc_no']} ฿{ra:,.2f}")
                    set_flash("success", f"รับชำระเรียบร้อย · ยอดคงค้าง ฿{rem_due:,.2f}")
                    st.rerun()

# ------------------------------------------------------------------------------
# MODULE: THAI TAX COMPLIANCE CENTER (ภ.พ.30 & ภ.ง.ด.)
# ------------------------------------------------------------------------------
elif app_menu == "🏛️ ศูนย์สรุปภาษีไทย (ภ.พ.30 & ภ.ง.ด.)":
    tm = st.text_input("📅 เลือกเดือนภาษี (YYYY-MM · เว้นว่างเพื่อดูทั้งหมด)", value=date.today().strftime("%Y-%m"))
    conn = get_conn()
    try:
        df_sv = read_df(conn, "SELECT doc_no, customer, customer_tax_id, amount, tax, total, COALESCE(wht_amount,0) AS wht_amount, created_at FROM sales ORDER BY id DESC")
        df_ev = read_df(conn, "SELECT exp_no, vendor_name, tax_inv_no, category, amount, COALESCE(vat_amount,0) AS vat_amount, COALESCE(wht_amount,0) AS wht_amount, created_at FROM expenses WHERE status='Approved' ORDER BY id DESC")
    finally:
        conn.close()
    if tm.strip():
        if not df_sv.empty:
            df_sv = df_sv[df_sv["created_at"].fillna("").astype(str).str.startswith(tm.strip())]
        if not df_ev.empty:
            df_ev = df_ev[df_ev["created_at"].fillna("").astype(str).str.startswith(tm.strip())]

    out_v = float(df_sv["tax"].fillna(0).sum()) if not df_sv.empty else 0.0
    in_v = float(df_ev["vat_amount"].fillna(0).sum()) if not df_ev.empty else 0.0
    pp30 = round(out_v - in_v, 2)
    t1, t2, t3, t4, t5 = st.columns(5)
    t1.metric("ภาษีขาย (Output VAT)", f"฿{out_v:,.2f}")
    t2.metric("ภาษีซื้อ (Input VAT)", f"฿{in_v:,.2f}")
    t3.metric("ภ.พ.30 สุทธิ", f"฿{pp30:,.2f}", delta="ต้องนำส่ง" if pp30 > 0 else "เครดิตยกไป")
    t4.metric("ภ.ง.ด. ที่ต้องนำส่ง", f"฿{float(df_ev['wht_amount'].fillna(0).sum()) if not df_ev.empty else 0:,.2f}")
    t5.metric("WHT ถูกหักไว้", f"฿{float(df_sv['wht_amount'].fillna(0).sum()) if not df_sv.empty else 0:,.2f}")

    tab_ov, tab_iv = st.tabs(["📤 รายงานภาษีขาย", "📥 รายงานภาษีซื้อและหัก ณ ที่จ่าย"])
    with tab_ov:
        ui_dataframe(df_sv, hide_index=True)
        if not df_sv.empty:
            st.download_button("⬇️ ดาวน์โหลดรายงานภาษีขาย (CSV)", df_sv.to_csv(index=False).encode("utf-8-sig"), f"output_vat_{tm or 'all'}.csv", "text/csv")
    with tab_iv:
        ui_dataframe(df_ev, hide_index=True)
        if not df_ev.empty:
            st.download_button("⬇️ ดาวน์โหลดรายงานภาษีซื้อ (CSV)", df_ev.to_csv(index=False).encode("utf-8-sig"), f"input_vat_{tm or 'all'}.csv", "text/csv")

# ------------------------------------------------------------------------------
# MODULE: CRM & VIP
# ------------------------------------------------------------------------------
elif app_menu == "🤝 ระบบลูกค้าสัมพันธ์ (CRM & VIP)":
    c1, c2 = st.columns([1.2, 1])
    with c1:
        with st.expander("➕ ลงทะเบียนลูกค้าใหม่", expanded=False):
            with st.form("crm_form"):
                cc = gen_input("รหัสลูกค้า", "crm_code", lambda: f"CUST-{uuid.uuid4().hex[:8].upper()}")
                cn = st.text_input("ชื่อบริษัท / คุณลูกค้า")
                ctax = st.text_input("เลขผู้เสียภาษี 13 หลัก")
                cp = st.text_input("เบอร์โทรศัพท์")
                ce = st.text_input("อีเมล")
                caddr = st.text_input("ที่อยู่")
                ct = st.selectbox("ระดับสิทธิประโยชน์ (Tier)", ["Silver", "Gold", "Platinum", "Diamond"])
                ccred = st.number_input("วงเงินเครดิต (บาท)", min_value=0.0, value=50000.0, step=5000.0)
                cpt = st.number_input("คะแนนสะสมเริ่มต้น", min_value=0, value=100, step=50)
                cnote = st.text_input("หมายเหตุ")
                if st.form_submit_button("บันทึกข้อมูลลูกค้า", type="primary"):
                    if not cc.strip() or not cn.strip():
                        st.error("กรุณาระบุรหัสและชื่อลูกค้า")
                    else:
                        ok = False
                        conn = get_conn()
                        try:
                            conn.execute("INSERT INTO crm_customers (cust_code, name, phone, email, tier, points, tax_id, address, credit_limit, notes) VALUES (?,?,?,?,?,?,?,?,?,?)", (cc.strip(), cn.strip(), cp.strip(), ce.strip(), ct, int(cpt), ctax.strip(), caddr.strip(), round(float(ccred), 2), cnote.strip()))
                            conn.commit()
                            ok = True
                        except DB_ERRORS as err:
                            safe_rollback(conn)
                            st.error(f"บันทึกไม่สำเร็จ: {err}")
                        finally:
                            conn.close()
                        if ok:
                            log_audit(user["full_name"], f"เพิ่มลูกค้า {cn.strip()}")
                            queue_input("crm_code", f"CUST-{uuid.uuid4().hex[:8].upper()}")
                            set_flash("success", "บันทึกข้อมูลลูกค้าเรียบร้อยแล้ว!")
                            st.rerun()

    conn = get_conn()
    try:
        df_crm = read_df(conn, "SELECT * FROM crm_customers ORDER BY id DESC")
        df_cs = read_df(conn, "SELECT customer, SUM(total) AS total_spent, COUNT(*) AS orders FROM sales GROUP BY customer")
    finally:
        conn.close()
    if not df_crm.empty and not df_cs.empty:
        df_crm = df_crm.merge(df_cs, left_on="name", right_on="customer", how="left").drop(columns=["customer"], errors="ignore")
        df_crm["total_spent"] = df_crm["total_spent"].fillna(0.0)
        df_crm["orders"] = df_crm["orders"].fillna(0).astype(int)
    with c2:
        if not df_crm.empty:
            tc = df_crm["tier"].fillna("Silver").value_counts().reset_index()
            tc.columns = ["tier", "count"]
            ui_plotly(px.pie(tc, names="tier", values="count", title="สัดส่วนระดับสมาชิกลูกค้า", hole=0.35))
        else:
            st.info("ยังไม่มีข้อมูลลูกค้า")

    cq = st.text_input("🔍 ค้นหาลูกค้า (รหัส / ชื่อ)", key="crm_q")
    df_cv = df_crm[df_crm["name"].astype(str).str.contains(cq.strip(), case=False, na=False) | df_crm["cust_code"].astype(str).str.contains(cq.strip(), case=False, na=False)] if (cq.strip() and not df_crm.empty) else df_crm
    ui_dataframe(df_cv, hide_index=True)

    if not df_crm.empty:
        with st.expander("✏️ แก้ไขข้อมูลลูกค้า / ปรับคะแนนสะสมและระดับ VIP"):
            cmap = {f"{r.cust_code} · {r.name} ({r.tier} | {int(r.points or 0)} แต้ม)": r for r in df_crm.itertuples()}
            sc = cmap[st.selectbox("เลือกลูกค้า", list(cmap), key="crm_esel")]
            tiers = ["Silver", "Gold", "Platinum", "Diamond"]
            with st.form("crm_eform"):
                et = st.selectbox("ระดับ VIP", tiers, index=tiers.index(sc.tier) if sc.tier in tiers else 0)
                ep = st.number_input("คะแนนสะสม", min_value=0, value=int(sc.points or 0), step=50)
                eph = st.text_input("เบอร์โทร", value=str(sc.phone or ""))
                etx = st.text_input("เลขผู้เสียภาษี", value=str(getattr(sc, "tax_id", "") or ""))
                if st.form_submit_button("💾 อัปเดตลูกค้า", type="primary"):
                    conn = get_conn()
                    try:
                        conn.execute("UPDATE crm_customers SET tier=?, points=?, phone=?, tax_id=? WHERE id=?", (et, int(ep), eph.strip(), etx.strip(), int(sc.id)))
                        conn.commit()
                    finally:
                        conn.close()
                    log_audit(user["full_name"], f"อัปเดตลูกค้า {sc.name} ({et}/{ep} แต้ม)")
                    set_flash("success", "อัปเดตข้อมูลลูกค้าเรียบร้อยแล้ว")
                    st.rerun()

# ------------------------------------------------------------------------------
# MODULE: FINANCIAL FORECAST
# ------------------------------------------------------------------------------
elif app_menu == "📈 คาดการณ์ทางการเงิน (Forecast)":
    conn = get_conn()
    try:
        df_s_raw = read_df(conn, "SELECT created_at, total FROM sales")
    finally:
        conn.close()

    if not df_s_raw.empty:
        df_s_raw["period"] = df_s_raw["created_at"].fillna(date.today().isoformat()).astype(str).str[:7]
        df_fc = df_s_raw.groupby("period", as_index=False)["total"].sum().sort_values("period")
    else:
        df_fc = pd.DataFrame(columns=["period", "total"])

    rev_sum = float(df_fc["total"].fillna(0).sum()) if not df_fc.empty else 0.0
    base = float(df_fc["total"].fillna(0).tail(3).mean()) if not df_fc.empty else 0.0
    f1, f2, f3 = st.columns(3)
    f1.metric("รายได้สะสม", f"฿{rev_sum:,.2f}")
    f2.metric("ฐานเฉลี่ยเดือนล่าสุด (สูงสุด 3 เดือน)", f"฿{base:,.2f}")
    f3.metric("จำนวนเดือนที่มีข้อมูล", f"{len(df_fc)} เดือน")

    if df_fc.empty:
        st.info("ยังไม่มีข้อมูลยอดขายสำหรับคำนวณประมาณการ")
    else:
        g = st.slider("สมมติฐานอัตราเติบโตต่อเดือน (%)", -20, 30, 5, 1)
        td = date.today()
        months = [f"{td.year + (td.month - 1 + i) // 12:04d}-{(td.month - 1 + i) % 12 + 1:02d}" for i in range(1, 7)]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=months, y=[round(base * ((1 + g / 100.0) ** i), 2) for i in range(1, 7)], mode="lines+markers", name=f"กรณีฐาน ({g:+d}%/เดือน)", line=dict(color="#2563EB", width=4)))
        fig.add_trace(go.Scatter(x=months, y=[round(base * ((1 + (g + 5) / 100.0) ** i), 2) for i in range(1, 7)], mode="lines+markers", name="กรณีเชิงบวก (+5%)", line=dict(color="#16A34A", dash="dash")))
        fig.add_trace(go.Scatter(x=months, y=[round(base * ((1 + max(g - 5, -50) / 100.0) ** i), 2) for i in range(1, 7)], mode="lines+markers", name="กรณีระมัดระวัง (-5%)", line=dict(color="#DC2626", dash="dot")))
        fig.update_layout(title="ประมาณการยอดขาย 6 เดือน (3 สถานการณ์จำลอง)", xaxis_title="เดือน", yaxis_title="บาท")
        ui_plotly(fig)

# ------------------------------------------------------------------------------
# MODULE: PURCHASE ORDERS & RECEIVE STOCK
# ------------------------------------------------------------------------------
elif app_menu == "🛍️ จัดซื้อและรับสินค้า (PO)":
    conn = get_conn()
    try:
        prod_rows = conn.execute("SELECT id, sku, name, cost_price FROM products ORDER BY name").fetchall()
    finally:
        conn.close()
    with st.expander("➕ สร้างใบสั่งซื้อ (PO) ใหม่", expanded=True):
        with st.form("po_form"):
            po_no = gen_input("เลขที่ PO", "po_no", lambda: f"PO-{date.today():%Y%m%d}-{uuid.uuid4().hex[:8].upper()}")
            vn = st.text_input("ชื่อซัพพลายเออร์ / คู่ค้า", "บริษัท ซัพพลายฮับ จำกัด")
            pl_opts = ["-- ไม่ผูกสินค้าในคลัง --"] + [f"{r['sku']} · {r['name']}" for r in prod_rows]
            pl = st.selectbox("ผูกสินค้าในคลัง (เพื่อรับเข้าสต็อกเมื่ออนุมัติ)", pl_opts)
            mp = next((r for r in prod_rows if f"{r['sku']} · {r['name']}" == pl), None)
            iname = st.text_input("รายการสินค้า / บริการ", value=mp["name"] if mp else "")
            pc1, pc2, pc3 = st.columns(3)
            with pc1:
                qty = st.number_input("จำนวน", min_value=1, value=10, step=1)
            with pc2:
                up = st.number_input("ราคาทุนต่อหน่วย (บาท)", min_value=0.01, value=float(mp["cost_price"] or 1000.0) if mp else 1000.0, step=100.0)
            with pc3:
                pvat = st.checkbox("รวม VAT 7%", value=True)
            edt = st.date_input("วันนัดส่งสินค้า", value=date.today() + timedelta(days=7))
            if st.form_submit_button("ส่งใบสั่งซื้อขออนุมัติ (PO)", type="primary"):
                if not all(v.strip() for v in (po_no, vn, iname)):
                    st.error("กรุณากรอกข้อมูลให้ครบ")
                else:
                    sub = round(int(qty) * float(up), 2)
                    vat_p = round(sub * 0.07, 2) if pvat else 0.0
                    tot_p = round(sub + vat_p, 2)
                    ok = False
                    conn = get_conn()
                    try:
                        cur = conn.cursor()
                        cur.execute("BEGIN IMMEDIATE")
                        po_id = insert_returning_id(
                            cur,
                            "INSERT INTO purchase_orders (po_no, vendor_name, item_name, qty, unit_price, vat_amount, total_amount, status, requested_by, expected_date, received_status, product_id) VALUES (?,?,?,?,?,?,?,'Pending Approval',?,?,'รอรับสินค้า',?)",
                            (po_no.strip(), vn.strip(), iname.strip(), int(qty), round(float(up), 2), vat_p, tot_p, user["full_name"], str(edt), int(mp["id"]) if mp else None),
                        )
                        cur.execute("INSERT INTO approvals (doc_type, title, amount, requested_by, status, document_id) VALUES ('PO',?,?,?,'Pending Approval',?)", (f"{po_no.strip()} · {vn.strip()} · {iname.strip()}", tot_p, user["full_name"], po_id))
                        conn.commit()
                        ok = True
                    except DB_ERRORS as err:
                        safe_rollback(conn)
                        st.error(f"บันทึก PO ไม่สำเร็จ: {err}")
                    finally:
                        conn.close()
                    if ok:
                        log_audit(user["full_name"], f"สร้าง PO {po_no.strip()} (฿{tot_p:,.2f})")
                        queue_input("po_no", f"PO-{date.today():%Y%m%d}-{uuid.uuid4().hex[:8].upper()}")
                        set_flash("success", f"บันทึก PO {po_no.strip()} และส่งขออนุมัติแล้ว!")
                        st.rerun()

    conn = get_conn()
    try:
        df_po = read_df(conn, "SELECT * FROM purchase_orders ORDER BY id DESC")
        ready_pos = conn.execute("SELECT id, po_no, item_name, qty, product_id FROM purchase_orders WHERE status='Approved' AND COALESCE(received_status,'รอรับสินค้า') != 'รับสินค้าแล้ว' ORDER BY id DESC").fetchall()
    finally:
        conn.close()
    ui_dataframe(df_po, hide_index=True)

    if ready_pos and prod_rows:
        st.subheader("📥 รับสินค้าเข้าคลังจาก PO ที่อนุมัติแล้ว")
        po_map = {f"{r['po_no']} · {r['item_name']} (จำนวน {r['qty']})": r for r in ready_pos}
        srpo = po_map[st.selectbox("เลือก PO ที่ต้องการรับของเข้าคลัง", list(po_map), key="rcv_po_sel")]
        pd_map = {f"{r['sku']} · {r['name']}": int(r["id"]) for r in prod_rows}
        d_idx = next((i for i, r in enumerate(prod_rows) if srpo["product_id"] == r["id"]), 0)
        sdest = pd_map[st.selectbox("เลือกสินค้าปลายทางในคลัง", list(pd_map), index=d_idx, key="rcv_po_prod")]
        if ui_button("📥 ยืนยันรับสินค้าเข้าสต็อก", type="primary", key="btn_rcv_po"):
            try:
                ns = receive_po_to_stock(int(srpo["id"]), sdest, user["full_name"])
            except (ValueError, *DB_ERRORS) as err:
                st.error(str(err))
            else:
                log_audit(user["full_name"], f"รับสินค้าตาม {srpo['po_no']} เข้าคลัง (คงเหลือ {ns})")
                set_flash("success", f"รับสินค้าตาม {srpo['po_no']} เข้าคลังเรียบร้อยแล้ว (สต็อกใหม่ {ns} ชิ้น)")
                st.rerun()

# ------------------------------------------------------------------------------
# MODULE: EXPENSES (INPUT VAT + WHT)
# ------------------------------------------------------------------------------
elif app_menu == "💸 คุมงบประมาณและค่าใช้จ่าย (Expenses)":
    c1, c2 = st.columns(2)
    with c1:
        with st.form("exp_form"):
            eno = gen_input("เลขที่ใบสำคัญจ่าย", "exp_no", lambda: f"EXP-{date.today():%Y%m%d}-{uuid.uuid4().hex[:8].upper()}")
            evend = st.text_input("ชื่อผู้ขาย / ผู้รับเงิน", placeholder="เช่น การไฟฟ้านครหลวง")
            etax = st.text_input("เลขที่ใบกำกับภาษีซื้อ (ไม่บังคับ)")
            ecat = st.selectbox("หมวดหมู่", ["ค่าสาธารณูปโภค", "ค่าการตลาด", "ค่าเช่าสถานที่", "อุปกรณ์สำนักงาน", "ค่าบริการวิชาชีพ", "ค่าเดินทาง", "อื่นๆ"])
            edesc = st.text_input("รายละเอียดค่าใช้จ่าย")
            ex1, ex2, ex3 = st.columns(3)
            with ex1:
                eamt = st.number_input("ยอดก่อนภาษี (บาท)", min_value=0.01, value=1000.0, step=100.0)
            with ex2:
                evat = st.checkbox("มีภาษีซื้อ 7%", value=True)
            with ex3:
                ewht = st.selectbox("หัก ณ ที่จ่าย (%)", [0.0, 1.0, 2.0, 3.0, 5.0])
            if st.form_submit_button("บันทึกและส่งขออนุมัติค่าใช้จ่าย", type="primary"):
                if not eno.strip() or not edesc.strip():
                    st.error("กรุณาระบุเลขที่และรายละเอียด")
                else:
                    be = round(float(eamt), 2)
                    ve = round(be * 0.07, 2) if evat else 0.0
                    we = round(be * (float(ewht) / 100.0), 2)
                    ne = round(be + ve - we, 2)
                    ok = False
                    conn = get_conn()
                    try:
                        cur = conn.cursor()
                        cur.execute("BEGIN IMMEDIATE")
                        exp_id = insert_returning_id(
                            cur,
                            "INSERT INTO expenses (exp_no, category, description, amount, approved_by, status, vendor_name, tax_inv_no, vat_amount, wht_rate, wht_amount, payment_status) VALUES (?,?,?,?,NULL,'Pending Approval',?,?,?,?,?,'รอจ่าย')",
                            (eno.strip(), ecat, edesc.strip(), be, evend.strip(), etax.strip(), ve, float(ewht), we),
                        )
                        cur.execute("INSERT INTO approvals (doc_type, title, amount, requested_by, status, document_id) VALUES ('EXPENSE',?,?,?,'Pending Approval',?)", (f"{eno.strip()} · {ecat} · {edesc.strip()}", ne, user["full_name"], exp_id))
                        conn.commit()
                        ok = True
                    except DB_ERRORS as err:
                        safe_rollback(conn)
                        st.error(f"บันทึกไม่สำเร็จ: {err}")
                    finally:
                        conn.close()
                    if ok:
                        log_audit(user["full_name"], f"บันทึกค่าใช้จ่าย {eno.strip()} (สุทธิ ฿{ne:,.2f})")
                        queue_input("exp_no", f"EXP-{date.today():%Y%m%d}-{uuid.uuid4().hex[:8].upper()}")
                        set_flash("success", f"บันทึกค่าใช้จ่าย {eno.strip()} และส่งขออนุมัติแล้ว!")
                        st.rerun()
    conn = get_conn()
    try:
        df_exp = read_df(conn, "SELECT * FROM expenses ORDER BY id DESC")
    finally:
        conn.close()
    with c2:
        if not df_exp.empty:
            es = df_exp.assign(category=df_exp["category"].fillna("อื่นๆ"), amount=df_exp["amount"].fillna(0.0)).groupby("category", as_index=False)["amount"].sum()
            es = es[es["amount"] > 0]
            if not es.empty:
                ui_plotly(px.pie(es, names="category", values="amount", title="สัดส่วนค่าใช้จ่ายตามหมวดหมู่", hole=0.35))
        else:
            st.info("ยังไม่มีข้อมูลค่าใช้จ่าย")
    ui_dataframe(df_exp, hide_index=True)
    if not df_exp.empty:
        st.download_button("⬇️ ดาวน์โหลดรายงานค่าใช้จ่าย (CSV)", df_exp.to_csv(index=False).encode("utf-8-sig"), f"taxmate_expenses_{date.today().isoformat()}.csv", "text/csv")

# ------------------------------------------------------------------------------
# MODULE: SMART INVENTORY WMS
# ------------------------------------------------------------------------------
elif app_menu == "📦 Smart Inventory WMS":
    with st.expander("➕ เพิ่มรายการสินค้าใหม่"):
        with st.form("prod_form"):
            psku = gen_input("รหัสสินค้า (SKU)", "prod_sku", lambda: f"SKU-{uuid.uuid4().hex[:8].upper()}")
            pname = st.text_input("ชื่อสินค้า")
            pc1, pc2, pc3 = st.columns(3)
            with pc1:
                pcost = st.number_input("ราคาทุน (บาท)", min_value=0.0, value=600.0, step=50.0)
                pprice = st.number_input("ราคาขาย (บาท)", min_value=0.0, value=1000.0, step=50.0)
            with pc2:
                pstock = st.number_input("สต็อกเริ่มต้น", min_value=0, value=10, step=1)
                pmin = st.number_input("จุดแจ้งเตือนสต็อกต่ำ", min_value=0, value=5, step=1)
            with pc3:
                punit = st.text_input("หน่วยนับ", value="ชิ้น")
                ploc = st.text_input("คลัง / ชั้นวาง", value="คลังหลัก")
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
                        pid = insert_returning_id(
                            cur,
                            "INSERT INTO products (sku, name, price, stock, category, min_stock, cost_price, unit, location) VALUES (?,?,?,?,?,?,?,?,?)",
                            (psku.strip(), pname.strip(), round(float(pprice), 2), int(pstock), pcat, int(pmin), round(float(pcost), 2), punit.strip() or "ชิ้น", ploc.strip() or "คลังหลัก"),
                        )
                        if int(pstock) > 0:
                            cur.execute("INSERT INTO inventory_movements (product_id, movement_type, quantity, balance_after, reference, created_by) VALUES (?,'Receipt',?,?,'ยอดตั้งต้น',?)", (pid, int(pstock), int(pstock), user["full_name"]))
                        conn.commit()
                        ok = True
                    except DB_ERRORS as err:
                        safe_rollback(conn)
                        st.error(f"บันทึกไม่สำเร็จ: {err}")
                    finally:
                        conn.close()
                    if ok:
                        log_audit(user["full_name"], f"เพิ่มสินค้า {psku.strip()}")
                        queue_input("prod_sku", f"SKU-{uuid.uuid4().hex[:8].upper()}")
                        set_flash("success", "เพิ่มสินค้าเรียบร้อยแล้ว!")
                        st.rerun()

    conn = get_conn()
    try:
        df_p = read_df(conn, "SELECT * FROM products ORDER BY name")
        df_mv = read_df(conn, "SELECT m.created_at AS \"เวลา\", p.sku AS \"SKU\", p.name AS \"สินค้า\", m.movement_type AS \"ประเภท\", m.quantity AS \"จำนวน\", m.balance_after AS \"คงเหลือ\", m.reference AS \"อ้างอิง\", m.created_by AS \"ผู้บันทึก\" FROM inventory_movements m JOIN products p ON p.id=m.product_id ORDER BY m.id DESC LIMIT 500")
    finally:
        conn.close()

    if not df_p.empty:
        df_p["stock"] = df_p["stock"].fillna(0).astype(int)
        df_p["min_stock"] = df_p["min_stock"].fillna(10).astype(int)
        df_p["cost_price"] = df_p["cost_price"].fillna(0.0)
        df_p["stock_value"] = (df_p["price"].fillna(0.0) * df_p["stock"]).round(2)
        low_c = len(df_p[df_p["stock"] <= df_p["min_stock"]])
        w1, w2, w3 = st.columns(3)
        w1.metric("จำนวน SKU", f"{len(df_p):,} รายการ")
        w2.metric("มูลค่าขายรวมในคลัง", f"฿{float(df_p['stock_value'].sum()):,.2f}")
        w3.metric("สินค้าต่ำกว่าเกณฑ์", f"{low_c} รายการ")
        if low_c > 0:
            st.warning(f"⚠️ มีสินค้าต่ำกว่าจุดแจ้งเตือน {low_c} รายการ")

    pq1, pq2 = st.columns([2, 1])
    with pq1:
        ps = st.text_input("🔍 ค้นหา SKU / ชื่อสินค้า", key="wms_q")
    with pq2:
        pcf = st.selectbox("กรองหมวดหมู่", ["ทั้งหมด", "Software", "Hardware", "Service", "General"], key="wms_cf")
    df_pv = df_p.copy()
    if ps.strip() and not df_pv.empty:
        df_pv = df_pv[df_pv["sku"].astype(str).str.contains(ps.strip(), case=False, na=False) | df_pv["name"].astype(str).str.contains(ps.strip(), case=False, na=False)]
    if pcf != "ทั้งหมด" and not df_pv.empty:
        df_pv = df_pv[df_pv["category"] == pcf]
    ui_dataframe(df_pv, hide_index=True)

    if not df_p.empty:
        ca, ce = st.columns(2)
        p_opts = {f"{r.sku} · {r.name} · คงเหลือ {int(r.stock)} {r.unit}": r for r in df_p.itertuples()}
        with ca:
            st.subheader("🔄 ปรับยอดรับเข้า / เบิกออกสินค้า")
            with st.form("adj_stock_form"):
                sp = st.selectbox("เลือกสินค้า", list(p_opts), key="adj_p")
                mt = st.selectbox("ประเภท", ["Receipt", "Issue"], format_func=lambda v: "รับเข้า" if v == "Receipt" else "เบิกออก")
                mq = st.number_input("จำนวน", min_value=1, value=1, step=1)
                mref = st.text_input("เหตุผล / เลขอ้างอิง")
                if st.form_submit_button("บันทึกการเคลื่อนไหวสต็อก", type="primary"):
                    try:
                        ns = adjust_stock(int(p_opts[sp].id), mt, mq, mref, user["full_name"])
                    except (ValueError, *DB_ERRORS) as err:
                        st.error(str(err))
                    else:
                        log_audit(user["full_name"], f"ปรับสต็อก {sp} -> {ns}")
                        set_flash("success", f"บันทึกแล้ว · คงเหลือ {ns} ชิ้น")
                        st.rerun()
        with ce:
            st.subheader("✏️ แก้ไขราคา / จุดแจ้งเตือนสินค้า")
            sep = p_opts[st.selectbox("เลือกสินค้าที่ต้องการแก้ไข", list(p_opts), key="edit_p")]
            with st.form("edit_prod_form"):
                epc = st.number_input("ราคาทุน", min_value=0.0, value=float(sep.cost_price or 0.0), step=50.0, key=f"epc_{sep.id}")
                epp = st.number_input("ราคาขาย", min_value=0.0, value=float(sep.price or 0.0), step=50.0, key=f"epp_{sep.id}")
                epm = st.number_input("Min Stock", min_value=0, value=int(sep.min_stock or 5), step=1, key=f"epm_{sep.id}")
                epl = st.text_input("คลัง / ชั้นวาง", value=str(sep.location or "คลังหลัก"), key=f"epl_{sep.id}")
                if st.form_submit_button("💾 บันทึกการแก้ไขสินค้า", type="primary"):
                    conn = get_conn()
                    try:
                        conn.execute("UPDATE products SET cost_price=?, price=?, min_stock=?, location=? WHERE id=?", (round(float(epc), 2), round(float(epp), 2), int(epm), epl.strip(), int(sep.id)))
                        conn.commit()
                    finally:
                        conn.close()
                    log_audit(user["full_name"], f"แก้ไขข้อมูลสินค้า {sep.sku}")
                    set_flash("success", f"บันทึกข้อมูลสินค้า {sep.sku} เรียบร้อยแล้ว")
                    st.rerun()
    st.subheader("📋 ประวัติการเคลื่อนไหวสต็อก")
    ui_dataframe(df_mv, hide_index=True)

# ------------------------------------------------------------------------------
# MODULE: HR & PAYROLL (SSO 5% + PAYSLIP HTML)
# ------------------------------------------------------------------------------
elif app_menu == "👥 HR & Payroll (ปกส./สลิป)":
    with st.expander("➕ เพิ่มพนักงานใหม่"):
        with st.form("emp_form"):
            ec = gen_input("รหัสพนักงาน", "emp_code", lambda: f"EMP-{uuid.uuid4().hex[:8].upper()}")
            en = st.text_input("ชื่อ-นามสกุล")
            ep = st.text_input("ตำแหน่ง")
            h1, h2 = st.columns(2)
            with h1:
                esal = st.number_input("เงินเดือน (บาท)", min_value=0.0, value=30000.0, step=1000.0)
                edept = st.selectbox("แผนก", ["บริหาร", "บัญชีและการเงิน", "การขาย", "ทรัพยากรบุคคล", "ไอที"])
                esso = st.checkbox("หักประกันสังคม 5% (สูงสุด 750 บาท) อัตโนมัติ", value=True)
            with h2:
                ephone = st.text_input("เบอร์โทรศัพท์")
                eemail = st.text_input("อีเมล (ใช้เชื่อมสลิปใน User Portal)")
                ebank = st.text_input("เลขบัญชีรับเงินเดือน")
            if st.form_submit_button("บันทึกพนักงานใหม่", type="primary"):
                if not all(v.strip() for v in (ec, en, ep)):
                    st.error("กรุณากรอกรหัส ชื่อ และตำแหน่ง")
                else:
                    ok = False
                    conn = get_conn()
                    try:
                        conn.execute("INSERT INTO employees (emp_code, name, position, salary, department, phone, email, bank_account, sso_enabled) VALUES (?,?,?,?,?,?,?,?,?)", (ec.strip(), en.strip(), ep.strip(), round(float(esal), 2), edept, ephone.strip(), eemail.strip(), ebank.strip(), 1 if esso else 0))
                        conn.commit()
                        ok = True
                    except DB_ERRORS as err:
                        safe_rollback(conn)
                        st.error(f"บันทึกไม่สำเร็จ: {err}")
                    finally:
                        conn.close()
                    if ok:
                        log_audit(user["full_name"], f"เพิ่มพนักงาน {ec.strip()}")
                        queue_input("emp_code", f"EMP-{uuid.uuid4().hex[:8].upper()}")
                        set_flash("success", "เพิ่มพนักงานเรียบร้อยแล้ว!")
                        st.rerun()

    conn = get_conn()
    try:
        df_emp = read_df(conn, "SELECT * FROM employees ORDER BY emp_code")
        runs = conn.execute("SELECT id, period, status FROM payroll_runs ORDER BY period DESC").fetchall()
    finally:
        conn.close()
    ui_dataframe(df_emp, hide_index=True)

    st.markdown("---")
    st.subheader("💸 รอบจ่ายเงินเดือน & สลิปเงินเดือน (Payslip)")
    with st.form("pr_create"):
        per = st.text_input("รอบเงินเดือน (YYYY-MM)", value=date.today().strftime("%Y-%m"))
        if st.form_submit_button("สร้างรอบเงินเดือนแบบร่าง (คำนวณ ปกส. 5% อัตโนมัติ)"):
            try:
                _, ecnt = create_payroll(per, user["full_name"])
            except DB_INTEGRITY_ERRORS:
                st.error("มีรอบเงินเดือนนี้อยู่แล้ว")
            except (ValueError, *DB_ERRORS) as err:
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
                """SELECT pi.employee_id, e.emp_code, e.name, e.position, e.department, e.bank_account,
                          pi.gross_pay, pi.bonus, pi.sso_deduction, pi.tax_deduction, pi.other_deduction, pi.deductions, pi.net_pay
                   FROM payroll_items pi JOIN employees e ON e.id=pi.employee_id WHERE pi.payroll_run_id=? ORDER BY e.emp_code""",
                (sel_r["id"],),
            ).fetchall()
        finally:
            conn.close()
        if items:
            ui_dataframe(pd.DataFrame([{"รหัส": i["emp_code"], "ชื่อ": i["name"], "เงินเดือน": i["gross_pay"], "OT/โบนัส": i["bonus"], "ปกส.": i["sso_deduction"], "ภาษี": i["tax_deduction"], "หักอื่น": i["other_deduction"], "รวมหัก": i["deductions"], "สุทธิ": i["net_pay"]} for i in items]), hide_index=True)
            e_opts = {f"{i['emp_code']} · {i['name']}": dict(i) for i in items}
            sel_e = e_opts[st.selectbox("เลือกพนักงาน (สำหรับปรับยอด / ดาวน์โหลดสลิป)", list(e_opts), key=f"pe_{sel_r['id']}")]
            st.download_button(f"🖨️ ดาวน์โหลดสลิปเงินเดือน {sel_e['name']} ({sel_r['period']})", build_payslip_html(company, sel_r["period"], sel_e).encode("utf-8"), f"payslip_{sel_r['period']}_{sel_e['emp_code']}.html", "text/html")
            if sel_r["status"] == "Draft":
                with st.form("pr_ded_form"):
                    pd1, pd2, pd3, pd4 = st.columns(4)
                    with pd1:
                        bv = st.number_input("OT / โบนัส", min_value=0.0, value=float(sel_e["bonus"]), step=500.0)
                    with pd2:
                        sv = st.number_input("ประกันสังคม (SSO)", min_value=0.0, value=float(sel_e["sso_deduction"]), step=50.0)
                    with pd3:
                        tv = st.number_input("ภาษี ภ.ง.ด.1", min_value=0.0, value=float(sel_e["tax_deduction"]), step=100.0)
                    with pd4:
                        ov = st.number_input("หักอื่น ๆ", min_value=0.0, value=float(sel_e["other_deduction"]), step=100.0)
                    if st.form_submit_button("💾 บันทึกรายได้เพิ่มและยอดหัก"):
                        try:
                            update_payroll_item(sel_r["id"], sel_e["employee_id"], bv, sv, tv, ov)
                        except (ValueError, *DB_ERRORS) as err:
                            st.error(str(err))
                        else:
                            set_flash("success", "บันทึกยอดเงินเดือนเรียบร้อยแล้ว")
                            st.rerun()
                if ui_button("✅ ยืนยันจ่ายเงินเดือนและบันทึกบัญชีอัตโนมัติ", type="primary", key=f"btn_pay_pr_{sel_r['id']}"):
                    try:
                        net_p = pay_payroll(sel_r["id"])
                    except (ValueError, *DB_ERRORS) as err:
                        st.error(str(err))
                    else:
                        log_audit(user["full_name"], f"จ่ายเงินเดือนรอบ {sel_r['period']} ฿{net_p:,.2f}")
                        set_flash("success", "จ่ายเงินเดือนและบันทึกบัญชีเรียบร้อยแล้ว")
                        st.rerun()

# ------------------------------------------------------------------------------
# MODULE: JOURNAL ENTRIES & FINANCIAL STATEMENTS (4 TABS)
# ------------------------------------------------------------------------------
elif app_menu == "📒 บันทึกบัญชีและงบการเงิน (GL)":
    tj, ttb, tpl, tbs = st.tabs(["📒 สมุดรายวัน (Journal)", "⚖️ งบทดลอง (Trial Balance)", "📊 งบกำไรขาดทุน (P&L)", "🏛️ งบแสดงฐานะการเงิน (Balance Sheet)"])
    conn = get_conn()
    try:
        df_j = read_df(conn, "SELECT * FROM journal_entries ORDER BY id DESC")
    finally:
        conn.close()

    with tj:
        coa_labels = [f"{code} · {name}" for code, name in THAI_COA]
        with st.form("gl_form"):
            g1, g2 = st.columns(2)
            with g1:
                jd = st.date_input("วันที่", date.today())
                dr_p = st.selectbox("บัญชีเดบิต (ผังบัญชีมาตรฐาน)", coa_labels, index=0)
            with g2:
                ja = st.number_input("จำนวนเงิน (บาท)", min_value=0.01, value=1000.0, step=100.0)
                cr_p = st.selectbox("บัญชีเครดิต (ผังบัญชีมาตรฐาน)", coa_labels, index=12)
            jdesc = st.text_input("คำอธิบายรายการ")
            if st.form_submit_button("บันทึกรายการบัญชีคู่ (Double-Entry)", type="primary"):
                jdc, jdn = dr_p.split(" · ", 1)
                jcc, jcn = cr_p.split(" · ", 1)
                if not jdesc.strip() or jdc == jcc:
                    st.error("กรุณาระบุคำอธิบาย และเลือกบัญชีเดบิต/เครดิตให้ต่างกัน")
                else:
                    av = round(float(ja), 2)
                    conn = get_conn()
                    try:
                        conn.executemany("INSERT INTO journal_entries (entry_date, account_code, account_name, debit, credit, description) VALUES (?,?,?,?,?,?)", [(str(jd), jdc, jdn, av, 0.0, jdesc.strip()), (str(jd), jcc, jcn, 0.0, av, jdesc.strip())])
                        conn.commit()
                    finally:
                        conn.close()
                    log_audit(user["full_name"], f"บันทึกสมุดรายวัน ฿{av:,.2f}")
                    set_flash("success", "บันทึกรายการเดบิตและเครดิตเรียบร้อยแล้ว")
                    st.rerun()
        gq = st.text_input("🔍 ค้นหาในสมุดรายวัน", key="gl_q")
        df_jv = df_j[df_j["account_code"].astype(str).str.contains(gq.strip(), case=False, na=False) | df_j["description"].fillna("").astype(str).str.contains(gq.strip(), case=False, na=False)] if (gq.strip() and not df_j.empty) else df_j
        ui_dataframe(df_jv, hide_index=True)
        if not df_jv.empty:
            st.download_button("⬇️ ดาวน์โหลดสมุดรายวัน (CSV)", df_jv.to_csv(index=False).encode("utf-8-sig"), f"taxmate_gl_{date.today().isoformat()}.csv", "text/csv")

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
            ui_dataframe(tb, hide_index=True)

    with tpl:
        if df_j.empty:
            st.info("ยังไม่มีรายการบัญชี")
        else:
            codes = df_j["account_code"].fillna("").astype(str).str.strip()
            rev_df, exp_df = df_j[codes.str.startswith("4")], df_j[codes.str.startswith(("5", "6"))]
            t_rev = float(rev_df["credit"].fillna(0).sum() - rev_df["debit"].fillna(0).sum())
            t_exp = float(exp_df["debit"].fillna(0).sum() - exp_df["credit"].fillna(0).sum())
            p1, p2, p3 = st.columns(3)
            p1.metric("รายได้รวม (หมวด 4)", f"฿{t_rev:,.2f}")
            p2.metric("ค่าใช้จ่ายรวม (หมวด 5-6)", f"฿{t_exp:,.2f}")
            p3.metric("กำไร (ขาดทุน) สุทธิ", f"฿{t_rev - t_exp:,.2f}")
            ui_plotly(px.bar(pd.DataFrame({"รายการ": ["รายได้รวม", "ค่าใช้จ่ายรวม", "กำไรสุทธิ"], "จำนวนเงิน": [t_rev, t_exp, t_rev - t_exp]}), x="รายการ", y="จำนวนเงิน", title="สรุปงบกำไรขาดทุนเบื้องต้น"))

    with tbs:
        if df_j.empty:
            st.info("ยังไม่มีรายการบัญชี")
        else:
            codes = df_j["account_code"].fillna("").astype(str).str.strip()
            assets = round(float(df_j[codes.str.startswith("1")]["debit"].fillna(0).sum() - df_j[codes.str.startswith("1")]["credit"].fillna(0).sum()), 2)
            liab = round(float(df_j[codes.str.startswith("2")]["credit"].fillna(0).sum() - df_j[codes.str.startswith("2")]["debit"].fillna(0).sum()), 2)
            ret = round(float(df_j[codes.str.startswith("4")]["credit"].fillna(0).sum() - df_j[codes.str.startswith("4")]["debit"].fillna(0).sum()) - float(df_j[codes.str.startswith(("5", "6"))]["debit"].fillna(0).sum() - df_j[codes.str.startswith(("5", "6"))]["credit"].fillna(0).sum()), 2)
            eq = round(float(df_j[codes.str.startswith("3")]["credit"].fillna(0).sum() - df_j[codes.str.startswith("3")]["debit"].fillna(0).sum()) + ret, 2)
            b1, b2, b3 = st.columns(3)
            b1.metric("สินทรัพย์รวม (หมวด 1)", f"฿{assets:,.2f}")
            b2.metric("หนี้สินรวม (หมวด 2)", f"฿{liab:,.2f}")
            b3.metric("ส่วนของเจ้าของ + กำไรสะสม", f"฿{eq:,.2f}")
            st.caption(f"สมการบัญชี: สินทรัพย์ (฿{assets:,.2f}) = หนี้สิน + ส่วนของเจ้าของ (฿{liab + eq:,.2f})")

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
                    conn.execute("INSERT INTO approvals (doc_type, title, amount, requested_by, status) VALUES (?,?,?,?,'Pending Approval')", (at, atitle.strip(), round(float(aamt), 2), user["full_name"]))
                    conn.commit()
                finally:
                    conn.close()
                log_audit(user["full_name"], f"ส่งคำขออนุมัติ: {atitle.strip()}")
                set_flash("success", "ส่งคำขออนุมัติเรียบร้อยแล้ว!")
                st.rerun()

    conn = get_conn()
    try:
        pend_rows = conn.execute("SELECT id, doc_type, title, amount, requested_by FROM approvals WHERE status='Pending Approval' ORDER BY id").fetchall()
        df_app = read_df(conn, "SELECT * FROM approvals ORDER BY id DESC LIMIT 1000")
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
                    except (ValueError, *DB_ERRORS) as err:
                        st.error(str(err))
                    else:
                        log_audit(user["full_name"], f"{dec}คำขอ {sel_a}")
                        set_flash("success", "บันทึกผลการพิจารณาเรียบร้อยแล้ว")
                        st.rerun()
        else:
            st.info("ไม่มีคำขอที่รอพิจารณา")
    else:
        st.info("คุณสามารถส่งและติดตามคำขอได้ (สิทธิ์อนุมัติสงวนไว้สำหรับ Admin / ผู้บริหาร)")
    ui_dataframe(df_app, hide_index=True)

# ------------------------------------------------------------------------------
# MODULE: RESET DATA (ADMIN ONLY)
# ------------------------------------------------------------------------------
elif app_menu == "🗑️ ล้างข้อมูลระบบ (Reset Data)":
    st.warning("⚠️ การลบข้อมูลจะลบออกจากฐานข้อมูลทันทีและไม่สามารถกู้คืนได้")
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
            st.markdown("#### 1. ล้างข้อมูลธุรกรรมทั้งหมด (เก็บบัญชีผู้ใช้และตั้งค่าบริษัทไว้)")
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
                        reset_tables(ALL_TX_TABLES + ["users", "company_settings"], include_extra=True)
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
            "🧾 ใบกำกับภาษี (Sales)": ("sales", "SELECT id, doc_no, customer, total FROM sales ORDER BY id DESC", (), lambda r: f"{r['doc_no']} · {r['customer']} · ฿{float(r['total']):,.2f}"),
            "📦 สินค้า (Products)": ("products", "SELECT id, sku, name, stock FROM products ORDER BY id DESC", (), lambda r: f"{r['sku']} · {r['name']} · คงเหลือ {int(r['stock'])}"),
            "🤝 ลูกค้า (CRM)": ("crm_customers", "SELECT id, cust_code, name, tier FROM crm_customers ORDER BY id DESC", (), lambda r: f"{r['cust_code']} · {r['name']} · {r['tier']}"),
            "🛍️ ใบสั่งซื้อ (PO)": ("purchase_orders", "SELECT id, po_no, vendor_name, item_name FROM purchase_orders ORDER BY id DESC", (), lambda r: f"{r['po_no']} · {r['vendor_name']} · {r['item_name']}"),
            "💸 ค่าใช้จ่าย (Expenses)": ("expenses", "SELECT id, exp_no, category, description FROM expenses ORDER BY id DESC", (), lambda r: f"{r['exp_no']} · {r['category']} · {r['description']}"),
            "👥 พนักงาน (Employees)": ("employees", "SELECT id, emp_code, name, position FROM employees ORDER BY id DESC", (), lambda r: f"{r['emp_code']} · {r['name']} · {r['position']}"),
            "📒 สมุดรายวัน (GL)": ("journal_entries", "SELECT id, entry_date, account_code, account_name FROM journal_entries ORDER BY id DESC", (), lambda r: f"{r['entry_date']} · {r['account_code']} {r['account_name']}"),
            "🛡️ คำขออนุมัติ (Approvals)": ("approvals", "SELECT id, doc_type, title, status FROM approvals ORDER BY id DESC", (), lambda r: f"{r['doc_type']} · {r['title']} · {r['status']}"),
            "📜 ประวัติการใช้งาน (Audit Logs)": ("audit_logs", "SELECT id, user_name, action, timestamp FROM audit_logs ORDER BY id DESC", (), lambda r: f"{r['user_name']} · {r['action']} · {r['timestamp'] or ''}"),
            "👤 บัญชีผู้ใช้งานอื่น (Users)": ("users", "SELECT id, username, full_name, role FROM users WHERE id != ? ORDER BY id DESC", (int(user["id"]),), lambda r: f"{r['username']} · {r['full_name']} · {r['role']}"),
        }
        cat = st.selectbox("เลือกหมวดหมู่", list(cfg), key="sdel_cat")
        t_key, q_sql, q_params, fmt_fn = cfg[cat]
        conn = get_conn()
        try:
            i_rows = conn.execute(q_sql, q_params).fetchall()
        finally:
            conn.close()
        if not i_rows:
            st.info("ไม่มีรายการให้ลบในหมวดนี้")
        else:
            imap = {f"#{r['id']} · {fmt_fn(r)}": int(r["id"]) for r in i_rows}
            sel_i = st.selectbox("เลือกรายการที่ต้องการลบ", list(imap), key=f"sdel_i_{t_key}")
            if ui_button("🗑️ ลบรายการนี้ถาวร", type="primary", key=f"btn_sdel_{t_key}"):
                try:
                    delete_record(t_key, imap[sel_i], user["full_name"], self_id=int(user["id"]))
                except (ValueError, *DB_ERRORS) as err:
                    st.error(str(err))
                else:
                    set_flash("success", f"ลบรายการ {sel_i} เรียบร้อยแล้ว")
                    st.rerun()