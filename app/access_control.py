# -*- coding: utf-8 -*-
"""بوابة اشتراك: تسجيل بالهاتف ← دفع مباشر (P2P) ← تفعيل يدوي من المشرف بعد التحقق ← دخول.

الاستخدام في main.py (بعد st.set_page_config مباشرة):
    from access_control import require_access
    user = require_access()          # يوقف التنفيذ إن لم يكن المستخدم مفعّلاً

الأسرار (Streamlit Cloud ← Settings ← Secrets):
    ADMIN_PASSWORD = "abosadeer_1987"          # كلمة مرور المشرف
    WHATSAPP = "9647740884754"               # رقم الاستلام بالصيغة الدولية بلا +
    SUPABASE_URL = "https://znrpogzykevvvvtrrlrx.supabase.co"
    SUPABASE_KEY = "sb_secret_BF3vfibvJD2KCJajNDrwyw_bWk-1HyY"        # لا تضعه في الكود أبداً
    [payment]
    "زين كاش" = "07xx xxx xxxx - باسم ..."
    "كي كارد" = "4269127660/ABDULGHAFOR IDAN"

جداول Supabase (SQL Editor):
    create table users(phone text primary key, name text, pin_hash text, salt text, status text,
      expires_at text, fail_count int default 0, locked_until text, sess text, created_at text);
    create table requests(id text primary key, phone text, plan text, amount int, method text,
      code text, status text, created_at text, decided_at text);
    alter table users enable row level security;  alter table requests enable row level security;
"""
import hashlib, hmac, os, re, secrets, sqlite3, time, urllib.parse
from datetime import datetime, timedelta, timezone
import pandas as pd
import requests
import streamlit as st

PLANS = {"شهري": (30, 10000), "ربع سنوي": (90, 25000), "سنوي": (365, 75000)}   # (أيام, د.ع) - عدّل أسعارك
LOCK_AFTER, LOCK_MIN, REVALIDATE_S = 5, 15, 300

now = lambda: datetime.now(timezone.utc)
iso = lambda d: d.isoformat(timespec="seconds")
parse = lambda s: datetime.fromisoformat(s) if s else None


def get_secret(key, default=None):
    try:
        return st.secrets[key]
    except Exception:
        return default


# ------------------------------------------------------------------ التخزين
class SQLiteStore:
    """للتطوير المحلي فقط: ملفات Streamlit Cloud تُمسح عند إعادة التشغيل."""
    def __init__(self, path):
        self.c = sqlite3.connect(path, check_same_thread=False)
        self.c.row_factory = sqlite3.Row
        self.c.execute("create table if not exists users(phone text primary key, name text, pin_hash text, salt text, status text, expires_at text, fail_count integer default 0, locked_until text, sess text, created_at text)")
        self.c.execute("create table if not exists requests(id text primary key, phone text, plan text, amount integer, method text, code text, status text, created_at text, decided_at text)")

    def _q(self, sql, a=()):
        cur = self.c.execute(sql, a); self.c.commit()
        return [dict(r) for r in cur.fetchall()] if cur.description else []

    def get_user(self, phone):
        r = self._q("select * from users where phone=?", (phone,)); return r[0] if r else None

    def upsert_user(self, u):
        upd = ",".join(f"{k}=excluded.{k}" for k in u if k != "phone")
        self._q(f"insert into users({','.join(u)}) values({','.join('?' * len(u))}) on conflict(phone) do update set {upd}", tuple(u.values()))

    def update_user(self, phone, **f):
        self._q(f"update users set {','.join(k + '=?' for k in f)} where phone=?", (*f.values(), phone))

    def add_request(self, r):
        self._q(f"insert into requests({','.join(r)}) values({','.join('?' * len(r))})", tuple(r.values()))

    def list_requests(self, status=None):
        return self._q("select * from requests" + (" where status=?" if status else "") + " order by created_at desc", (status,) if status else ())

    def update_request(self, rid, **f):
        self._q(f"update requests set {','.join(k + '=?' for k in f)} where id=?", (*f.values(), rid))

    def list_users(self):
        return self._q("select * from users order by created_at desc")


class SupabaseStore:
    def __init__(self, url, key):
        self.u = url.rstrip("/") + "/rest/v1/"
        self.h = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    def _r(self, m, t, params=None, json=None, prefer=None):
        h = dict(self.h, **({"Prefer": prefer} if prefer else {}))
        r = requests.request(m, self.u + t, headers=h, params=params, json=json, timeout=15)
        r.raise_for_status()
        return r.json() if r.text else []

    def get_user(self, phone):
        x = self._r("GET", "users", {"phone": f"eq.{phone}"}); return x[0] if x else None

    def upsert_user(self, u):
        self._r("POST", "users", {"on_conflict": "phone"}, u, "resolution=merge-duplicates")

    def update_user(self, phone, **f):
        self._r("PATCH", "users", {"phone": f"eq.{phone}"}, f)

    def add_request(self, r):
        self._r("POST", "requests", json=r)

    def list_requests(self, status=None):
        p = {"order": "created_at.desc"}
        if status:
            p["status"] = f"eq.{status}"
        return self._r("GET", "requests", p)

    def update_request(self, rid, **f):
        self._r("PATCH", "requests", {"id": f"eq.{rid}"}, f)

    def list_users(self):
        return self._r("GET", "users", {"order": "created_at.desc"})


@st.cache_resource
def get_store():
    url, key = get_secret("SUPABASE_URL"), get_secret("SUPABASE_KEY")
    if url and key:
        return SupabaseStore(url, key)
    return SQLiteStore(os.environ.get("ACCESS_DB", "local_access.db"))


# ------------------------------------------------------------------ المنطق
def norm_phone(s):
    d = re.sub(r"\D", "", s or "")
    d = d[5:] if d.startswith("00964") else d[3:] if d.startswith("964") else d
    d = d[1:] if d.startswith("0") else d
    return "+964" + d if re.fullmatch(r"7\d{9}", d) else None


def hash_pin(pin, salt):
    return hashlib.pbkdf2_hmac("sha256", pin.encode(), bytes.fromhex(salt), 200_000).hex()


def check_pin(pin, u):
    return hmac.compare_digest(hash_pin(pin, u["salt"]), u["pin_hash"])


def is_active(u):
    exp = parse(u.get("expires_at"))
    return bool(u.get("status") == "active" and exp and exp > now())


def login(store, phone, pin):
    u = store.get_user(phone)
    if not u:
        return None, "الرقم غير مسجّل. سجّل من تبويب «تسجيل وطلب اشتراك»."
    lock = parse(u.get("locked_until"))
    if lock and lock > now():
        return None, f"الحساب مقفل مؤقتاً بعد محاولات خاطئة. أعد المحاولة بعد {LOCK_MIN} دقيقة."
    if not check_pin(pin, u):
        fc = (u.get("fail_count") or 0) + 1
        f = dict(fail_count=fc)
        if fc >= LOCK_AFTER:
            f = dict(fail_count=0, locked_until=iso(now() + timedelta(minutes=LOCK_MIN)))
        store.update_user(phone, **f)
        return None, "الرقم السري غير صحيح."
    if u["status"] == "suspended":
        return None, "الحساب موقوف. تواصل مع المشرف."
    if not is_active(u):
        return None, ("طلبك بانتظار التحقق من الدفع وتفعيله." if u["status"] == "pending"
                      else "انتهى اشتراكك. جدّده من تبويب «تسجيل وطلب اشتراك» (بنفس الرقم والرقم السري).")
    u["sess"] = secrets.token_hex(8)
    store.update_user(phone, fail_count=0, locked_until=None, sess=u["sess"])
    return u, ""


def approve(store, req):
    u = store.get_user(req["phone"]) or {}
    base = max(now(), parse(u.get("expires_at")) or now())
    exp = base + timedelta(days=PLANS.get(req["plan"], (30,))[0])
    store.update_user(req["phone"], status="active", expires_at=iso(exp), fail_count=0, locked_until=None)
    store.update_request(req["id"], status="approved", decided_at=iso(now()))


# ------------------------------------------------------------------ الواجهة
def tab_login(store):
    c = st.columns(2)
    ph = c[0].text_input("رقم الهاتف", key="lg_phone", placeholder="07701234567")
    pin = c[1].text_input("الرقم السري", type="password", key="lg_pin")
    if st.button("دخول", key="lg_btn", type="primary"):
        phone = norm_phone(ph)
        if not phone:
            st.error("رقم هاتف غير صالح.")
            return
        u, msg = login(store, phone, pin)
        if u:
            st.session_state.update(auth=u, auth_ts=time.time())
            st.rerun()
        st.error(msg)


def tab_register(store):
    ss = st.session_state
    pay = dict(get_secret("payment", {}) or {})
    c = st.columns(2)
    name = c[0].text_input("الاسم", key="rg_name")
    ph = c[1].text_input("رقم الهاتف (واتساب)", key="rg_phone", placeholder="07701234567")
    pin = st.text_input("رقم سري (6 خانات فأكثر) — للتجديد استخدم نفس الرقم السري", type="password", key="rg_pin")
    c = st.columns(2)
    plan = c[0].selectbox("الباقة", list(PLANS), key="rg_plan",
                          format_func=lambda p: f"{p} — {PLANS[p][1]:,} د.ع / {PLANS[p][0]} يوم")
    method = c[1].selectbox("طريقة الدفع", list(pay) or ["تحويل مباشر"], key="rg_method")
    if st.button("إرسال طلب الاشتراك", key="rg_btn", type="primary"):
        phone = norm_phone(ph)
        if not name.strip() or not phone or len(pin) < 6:
            st.error("أكمل الاسم ورقم هاتف عراقي صحيح ورقماً سرياً من 6 خانات على الأقل.")
        else:
            u = store.get_user(phone)
            if u and not check_pin(pin, u):
                st.error("هذا الرقم مسجّل مسبقاً. أدخل رقمه السري الصحيح أو تواصل مع المشرف.")
            else:
                if not u:
                    salt = secrets.token_hex(16)
                    store.upsert_user(dict(phone=phone, name=name.strip(), salt=salt, pin_hash=hash_pin(pin, salt),
                                           status="pending", fail_count=0, created_at=iso(now())))
                req = dict(id=secrets.token_hex(8), phone=phone, plan=plan, amount=PLANS[plan][1], method=method,
                           code=secrets.token_hex(3).upper(), status="pending", created_at=iso(now()))
                store.add_request(req)
                ss["last_req"] = dict(req, account=pay.get(method, ""))
    r = ss.get("last_req")
    if r:
        st.success(f"تم استلام طلبك. **رقم الطلب: {r['code']}**")
        st.markdown(f"حوّل **{r['amount']:,} د.ع** عبر **{r['method']}**" + (f" إلى: `{r['account']}`" if r["account"] else ""))
        wa = get_secret("WHATSAPP")
        if wa:
            msg = f"طلب اشتراك {r['code']} - باقة {r['plan']} - هاتف {r['phone']}. مرفق إيصال الدفع."
            st.link_button("📲 أرسل الإيصال عبر واتساب", f"https://wa.me/{wa}?text={urllib.parse.quote(msg)}")
        st.caption("يُفعَّل حسابك بعد التحقق من وصول المبلغ، ثم سجّل الدخول بالهاتف والرقم السري.")


def tab_admin(store):
    ss, pw = st.session_state, get_secret("ADMIN_PASSWORD")
    if not pw:
        st.info("لم يُضبط ADMIN_PASSWORD في Secrets.")
        return
    if not ss.get("is_admin"):
        x = st.text_input("كلمة مرور المشرف", type="password", key="adm_pw")
        if st.button("دخول المشرف", key="adm_btn"):
            if hmac.compare_digest(x, pw):
                ss["is_admin"] = True; st.rerun()
            time.sleep(1.5); st.error("كلمة المرور غير صحيحة.")
        return
    if isinstance(store, SQLiteStore):
        st.warning("تخزين SQLite محلي مؤقت — لا يصلح للنشر. اضبط SUPABASE_URL وSUPABASE_KEY.")
    c = st.columns(2)
    if c[0].button("🚀 دخول التطبيق كمشرف", key="adm_app"):
        ss.update(auth=dict(phone="admin", name="المشرف", admin=True), auth_ts=time.time()); st.rerun()
    if c[1].button("خروج المشرف", key="adm_out"):
        ss["is_admin"] = False; st.rerun()
    users, pend = store.list_users(), store.list_requests("pending")
    names = {u["phone"]: u.get("name", "") for u in users}
    st.subheader(f"طلبات بانتظار التحقق ({len(pend)})")
    st.caption("تحقق من وصول المبلغ في تطبيق محفظتك/مصرفك نفسه، ولا تعتمد على لقطة الشاشة وحدها.")
    for r in pend:
        with st.container(border=True):
            st.write(f"**{names.get(r['phone'], '')}** | {r['phone']} | {r['plan']} | {int(r.get('amount') or 0):,} د.ع | "
                     f"{r['method']} | رمز `{r['code']}` | {str(r['created_at'])[:16]}")
            c = st.columns(2)
            if c[0].button("✅ تأكيد الدفع وتفعيل", key=f"ap_{r['id']}"):
                approve(store, r); st.rerun()
            if c[1].button("❌ رفض", key=f"rj_{r['id']}"):
                store.update_request(r["id"], status="rejected", decided_at=iso(now())); st.rerun()
    st.subheader("المشتركون")
    if users:
        df = pd.DataFrame(users)[["phone", "name", "status", "expires_at", "created_at"]]
        st.dataframe(df, hide_index=True, use_container_width=True)
        c = st.columns(4)
        sel = c[0].selectbox("مشترك", [u["phone"] for u in users], key="adm_sel")
        days = c[1].number_input("تمديد (أيام)", 0, 3650, 30, key="adm_days")
        if c[2].button("تمديد/تفعيل", key="adm_ext"):
            u = store.get_user(sel)
            base = max(now(), parse(u.get("expires_at")) or now())
            store.update_user(sel, status="active", expires_at=iso(base + timedelta(days=int(days)))); st.rerun()
        if c[3].button("إيقاف", key="adm_sus"):
            store.update_user(sel, status="suspended", sess=None); st.rerun()
        c = st.columns(2)
        npin = c[0].text_input("رقم سري جديد للمشترك المحدد", type="password", key="adm_npin")
        if c[1].button("إعادة تعيين الرقم السري", key="adm_rst") and len(npin) >= 6:
            salt = secrets.token_hex(16)
            store.update_user(sel, salt=salt, pin_hash=hash_pin(npin, salt), fail_count=0, locked_until=None, sess=None)
            st.success("تم.")


def require_access():
    ss, store = st.session_state, get_store()
    u = ss.get("auth")
    if u and not u.get("admin") and time.time() - ss.get("auth_ts", 0) > REVALIDATE_S:
        fresh = store.get_user(u["phone"])
        if fresh and is_active(fresh) and fresh.get("sess") == u.get("sess"):
            ss.update(auth=dict(fresh), auth_ts=time.time()); u = ss["auth"]
        else:
            ss.pop("auth", None); u = None
            st.warning("انتهت الجلسة: اشتراك منتهٍ أو دخول من جهاز آخر. سجّل الدخول من جديد.")
    if u:
        with st.sidebar:
            if u.get("admin"):
                st.caption("👤 المشرف")
            else:
                left = (parse(u["expires_at"]) - now()).days
                st.caption(f"👤 {u.get('name', '')} | متبقٍ {left} يوم")
            if st.button("تسجيل الخروج", key="logout"):
                ss.pop("auth", None); ss["is_admin"] = False; st.rerun()
        return u
    st.title("🔐 الدخول إلى المنصة")
    t1, t2, t3 = st.tabs(["🔑 دخول", "🆕 تسجيل وطلب اشتراك", "🛡️ المشرف"])
    with t1: tab_login(store)
    with t2: tab_register(store)
    with t3: tab_admin(store)
    st.stop()
