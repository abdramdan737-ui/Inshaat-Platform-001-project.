# -*- coding: utf-8 -*-
from pathlib import Path
import streamlit as st

st.set_page_config(
    page_title="منصة إنشاءات للاستشارات الهندسية",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

from modules.feasibility_ui import render_feasibility

# تحميل ملف CSS مباشرة دون الاعتماد على assets.ui_style.py
BASE_DIR = Path(__file__).resolve().parent
CSS_PATH = BASE_DIR / "assets" / "styles.css"
if CSS_PATH.is_file():
    st.markdown(f"<style>{CSS_PATH.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)
else:
    st.warning("ملف التنسيق assets/styles.css غير موجود؛ ستعمل المنصة بالتنسيق الافتراضي.")

with st.sidebar:
    st.markdown(
        '<div class="brand"><div class="brand-mark">🏗️</div>'
        '<div><div class="brand-name">إنشاءات</div>'
        '<div class="brand-sub">للاستشارات الهندسية</div></div></div>',
        unsafe_allow_html=True,
    )
    st.markdown("---")
    st.markdown("**مرحباً بك في منصة إنشاءات**")
    choice = st.radio("اختر القسم", ["دراسة الجدوى الاقتصادية"], label_visibility="collapsed")
    st.caption("نسخة مجانية — منصة إنشاءات")

if choice == "دراسة الجدوى الاقتصادية":
    render_feasibility()

st.markdown(
    '<div class="footer">منصة إنشاءات للاستشارات الهندسية · جميع النتائج تعتمد على المدخلات والافتراضات التي يحددها المستخدم</div>',
    unsafe_allow_html=True,
)
