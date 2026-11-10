# -*- coding: utf-8 -*-
"""حفظ طلبات الخدمات في مجلد + ملف CSV (بلا قاعدة بيانات).
الاستخدام في main.py:
    from service_requests import render_service_request
    elif choice == "طلب خدمة":
        render_service_request(user)
مكان الحفظ: المجلد data/ بجانب main.py، أو المسار في المتغير DATA_DIR."""
import csv, io, json, os, re, secrets, zipfile
from datetime import datetime
from pathlib import Path
import pandas as pd
import streamlit as st

BASE = Path(os.environ.get("DATA_DIR", "data"))
SERVICES = ["استشارة إنشائية", "مراجعة وتدقيق تقرير", "دراسة جدوى", "تصميم محطة رفع/معالجة", "خبرة قضائية/فنية", "أخرى"]
ALLOWED = {".pdf", ".png", ".jpg", ".jpeg", ".docx", ".xlsx", ".csv", ".txt", ".dwg", ".zip"}
MAX_FILES, MAX_MB = 5, 10
FIELDS = ["id", "created_at", "phone", "name", "service", "details", "files"]


def save_request(user, service, details, files=()):
    rid = datetime.now().strftime("%Y%m%d-%H%M%S-") + secrets.token_hex(2).upper()
    d = BASE / "service_requests" / rid
    d.mkdir(parents=True, exist_ok=True)
    saved = []
    for i, f in enumerate(list(files)[:MAX_FILES]):
        ext = Path(f.name).suffix.lower()
        if ext not in ALLOWED or len(f.getbuffer()) > MAX_MB * 1024 * 1024:
            continue
        safe = f"{i + 1}_" + re.sub(r"[^\w.\-]", "_", Path(f.name).stem)[:60] + ext     # يمنع مسارات خطرة
        (d / safe).write_bytes(bytes(f.getbuffer()))
        saved.append(safe)
    rec = dict(id=rid, created_at=datetime.now().isoformat(timespec="seconds"), phone=user.get("phone", ""),
               name=user.get("name", ""), service=service, details=details, files=";".join(saved))
    (d / "request.json").write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
    csv_path = BASE / "service_requests.csv"
    new = not csv_path.exists()
    with open(csv_path, "a", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow(rec)
    return rid, saved


def render_service_request(user):
    st.header("📨 طلب خدمة")
    service = st.selectbox("نوع الخدمة", SERVICES, key="sr_service")
    details = st.text_area("تفاصيل الطلب", height=150, key="sr_details")
    files = st.file_uploader(f"مرفقات (حتى {MAX_FILES} ملفات، {MAX_MB}MB لكل ملف)", accept_multiple_files=True,
                             type=[e[1:] for e in sorted(ALLOWED)], key="sr_files")
    if st.button("إرسال الطلب", type="primary", key="sr_btn"):
        if len(details.strip()) < 10:
            st.error("اكتب وصفاً أوضح للطلب.")
        else:
            rid, saved = save_request(user, service, details.strip(), files)
            st.success(f"تم حفظ طلبك برقم **{rid}** ({len(saved)} مرفق).")


def _zip_dir(path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for p in Path(path).rglob("*"):
            if p.is_file():
                z.write(p, p.relative_to(path.parent if path != BASE else BASE))
    return buf.getvalue()


def admin_view():
    st.subheader("📨 طلبات الخدمات (من الملفات)")
    f = BASE / "service_requests.csv"
    if not f.exists():
        st.caption("لا توجد طلبات بعد.")
        return
    df = pd.read_csv(f, encoding="utf-8-sig", dtype=str).fillna("")
    st.dataframe(df.sort_values("created_at", ascending=False), hide_index=True, use_container_width=True)
    c = st.columns(2)
    c[0].download_button("تنزيل الطلبات CSV", df.to_csv(index=False).encode("utf-8-sig"), "service_requests.csv", "text/csv", key="sr_dl_csv")
    c[1].download_button("نسخة احتياطية كاملة (ZIP)", _zip_dir(BASE), "backup.zip", "application/zip", key="sr_dl_all")
    rid = st.selectbox("افتح طلباً", df["id"].tolist()[::-1], key="sr_pick")
    if re.fullmatch(r"\d{8}-\d{6}-[0-9A-F]{4}", rid or ""):
        row = df[df["id"] == rid].iloc[0]
        st.write(f"**{row['name']}** | {row['phone']} | {row['service']}")
        st.text(row["details"])
        folder = BASE / "service_requests" / rid
        if folder.exists():
            st.download_button("تنزيل ملفات الطلب (ZIP)", _zip_dir(folder), f"{rid}.zip", "application/zip", key="sr_dl_one")
