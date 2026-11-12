# -*- coding: utf-8 -*-
import streamlit as st

st.set_page_config(
    page_title="منصة إنشاءات للاستشارات الهندسية",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

from assets.ui_style import load_css
from modules.feasibility_ui import render_feasibility

load_css()

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
