import hashlib
import hmac
import secrets
import smtplib
import time
from email.message import EmailMessage

import streamlit as st
from security.database import init_db, get_user, create_user, record_attempt, recent_failures

OTP_TTL = 300
MAX_FAILURES = 5
LOCK_SECONDS = 900

def _hash_password(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 310_000)
    return salt.hex() + "$" + digest.hex()

def _verify_password(password, encoded):
    try:
        salt_hex, digest_hex = encoded.split("$", 1)
        candidate = _hash_password(password, bytes.fromhex(salt_hex)).split("$", 1)[1]
        return hmac.compare_digest(candidate, digest_hex)
    except Exception:
        return False

def _send_otp(email, code):
    cfg = st.secrets.get("smtp", {})
    host = cfg.get("host")
    username = cfg.get("username")
    password = cfg.get("password")
    sender = cfg.get("sender", username)
    port = int(cfg.get("port", 587))
    if not all([host, username, password, sender]):
        raise RuntimeError("إعدادات SMTP غير مكتملة في secrets.toml.")
    msg = EmailMessage()
    msg["Subject"] = "رمز التحقق - منصة إنشاءات"
    msg["From"] = sender
    msg["To"] = email
    msg.set_content(f"رمز التحقق الخاص بك هو: {code}\nصلاحية الرمز خمس دقائق.")
    with smtplib.SMTP(host, port, timeout=20) as server:
        server.starttls()
        server.login(username, password)
        server.send_message(msg)

def _google_button():
    # يتطلب إعداد [auth] في .streamlit/secrets.toml وإعداد OAuth في Google Cloud.
    try:
        if "google" in st.secrets.get("auth", {}):
            st.login("google")
            return True
    except Exception as exc:
        st.error(f"تعذر بدء تسجيل Google: {exc}")
    return False

def render_auth():
    init_db()
    if "auth_user" in st.session_state:
        return st.session_state["auth_user"]

    st.markdown('<div class="auth-wrap">', unsafe_allow_html=True)
    st.markdown('<div class="auth-title">منصة إنشاءات</div>', unsafe_allow_html=True)
    st.markdown('<div class="auth-sub">تسجيل مجاني للوصول إلى أدوات دراسة الجدوى</div>', unsafe_allow_html=True)

    tab_login, tab_register, tab_google = st.tabs(["تسجيل الدخول", "إنشاء حساب مجاني", "Google"])

    with tab_login:
        email = st.text_input("البريد الإلكتروني", key="login_email").lower().strip()
        password = st.text_input("كلمة المرور", type="password", key="login_password")
        if st.button("دخول", use_container_width=True, key="login_btn"):
            now = time.time()
            if recent_failures(email, now - LOCK_SECONDS) >= MAX_FAILURES:
                st.error("تم إيقاف المحاولة مؤقتاً لكثرة المحاولات. حاول بعد 15 دقيقة.")
            else:
                user = get_user(email)
                ok = bool(user and user["is_active"] and _verify_password(password, user["password_hash"]))
                record_attempt(email, now, ok)
                if ok:
                    st.session_state["auth_user"] = {"email": user["email"], "display_name": user["display_name"]}
                    st.rerun()
                else:
                    st.error("البريد الإلكتروني أو كلمة المرور غير صحيحة.")

    with tab_register:
        name = st.text_input("الاسم الكامل", key="reg_name")
        email = st.text_input("البريد الإلكتروني", key="reg_email").lower().strip()
        password = st.text_input("كلمة المرور (8 أحرف على الأقل)", type="password", key="reg_password")
        confirm = st.text_input("تأكيد كلمة المرور", type="password", key="reg_confirm")
        if st.button("إرسال رمز التحقق", use_container_width=True, key="send_otp"):
            if not name.strip() or "@" not in email:
                st.error("أدخل الاسم والبريد الإلكتروني بصورة صحيحة.")
            elif len(password) < 8:
                st.error("كلمة المرور يجب ألا تقل عن 8 أحرف.")
            elif password != confirm:
                st.error("كلمتا المرور غير متطابقتين.")
            elif get_user(email):
                st.error("هذا البريد مسجل مسبقاً.")
            else:
                code = f"{secrets.randbelow(1_000_000):06d}"
                try:
                    _send_otp(email, code)
                    st.session_state["pending_registration"] = {
                        "name": name.strip(), "email": email, "password_hash": _hash_password(password),
                        "otp_hash": hashlib.sha256(code.encode()).hexdigest(), "expires": time.time() + OTP_TTL,
                        "tries": 0,
                    }
                    st.success("تم إرسال رمز التحقق إلى بريدك الإلكتروني.")
                except Exception as exc:
                    st.error(f"لم نتمكن من إرسال الرمز. تحقق من إعدادات البريد: {exc}")

        pending = st.session_state.get("pending_registration")
        if pending:
            otp = st.text_input("رمز التحقق المكوّن من 6 أرقام", max_chars=6, key="register_otp")
            if st.button("تأكيد التسجيل", use_container_width=True, key="verify_otp"):
                pending["tries"] += 1
                valid = (
                    time.time() <= pending["expires"] and pending["tries"] <= 5
                    and hmac.compare_digest(hashlib.sha256(otp.encode()).hexdigest(), pending["otp_hash"])
                )
                if valid:
                    try:
                        create_user(pending["email"], pending["name"], pending["password_hash"])
                        st.session_state.pop("pending_registration", None)
                        st.success("تم إنشاء الحساب بنجاح. يمكنك تسجيل الدخول.")
                    except Exception:
                        st.error("تعذر إنشاء الحساب؛ قد يكون البريد مسجلاً بالفعل.")
                else:
                    st.error("الرمز غير صحيح أو انتهت صلاحيته. يمكنك إعادة إرسال رمز جديد.")

    with tab_google:
        st.write("يمكنك استخدام حساب Google بعد إعداد OAuth في إعدادات التطبيق.")
        if st.button("المتابعة باستخدام Google", use_container_width=True):
            _google_button()

    st.markdown("</div>", unsafe_allow_html=True)

    # Streamlit OAuth callback: session user identity.
    try:
        if st.user.is_logged_in:
            email = st.user.email
            display_name = getattr(st.user, "name", None) or email.split("@")[0]
            existing = get_user(email)
            if not existing:
                # حساب Google موثّق من مزود OAuth؛ ينشأ محلياً دون كلمة مرور قابلة للاستخدام.
                create_user(email, display_name, _hash_password(secrets.token_urlsafe(32)))
            st.session_state["auth_user"] = {"email": email, "display_name": display_name}
            st.rerun()
    except Exception:
        pass
    return None
