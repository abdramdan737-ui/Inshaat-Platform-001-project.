# -*- coding: utf-8 -*-
"""تنسيق التبويبات على شكل أقراص بيضوية تملأ عرض الصفحة (يدعم بنية Streamlit الحديثة والقديمة).
الاستخدام: from ui_style import pill_tabs ثم pill_tabs() قبل st.tabs(...).
لتطبيقه على كل تبويبات التطبيق: استدعِه مرة واحدة في main.py بعد require_access()."""
from pathlib import Path
import streamlit as st

PRIMARY = "#1e5bd8"     # لون الإطار والقرص المحدد
SOFT = "#eaf0fb"        # خلفية الأقراص غير المحددة
TEXT = "#1e3a8a"        # لون نص القرص غير المحدد


def pill_tabs(primary=PRIMARY, soft=SOFT, text=TEXT):
    st.markdown(f"""
<style>
/* الشريط: يملأ العرض ويترك مساحة للإطار */
[data-testid="stTabs"] [role="tablist"] {{
    width: 100%; gap: 10px !important; padding: 6px 2px 10px 2px !important; border-bottom: none !important;
}}
/* إخفاء الخط السفلي القديم والمؤشر */
[data-testid="stTabs"] [role="tablist"]::after,
[data-testid="stTabs"] .react-aria-SelectionIndicator,
[data-testid="stTabs"] [data-baseweb="tab-highlight"],
[data-testid="stTabs"] [data-baseweb="tab-border"] {{ display: none !important; }}
/* القرص البيضوي: يتمدد ليملأ العرض ولا يصغر عن نصه */
[data-testid="stTabs"] [role="tab"] {{
    flex: 1 0 auto !important; justify-content: center !important; height: auto !important; margin: 0 !important;
    padding: 10px 22px !important; border-radius: 999px !important;
    background: {soft} !important; border: 2px solid {primary} !important;
    transition: background .15s, transform .1s;
}}
[data-testid="stTabs"] [role="tab"] p {{
    margin: 0 !important; font-weight: 700 !important; font-size: 1rem !important;
    color: {text} !important; white-space: nowrap;
}}
[data-testid="stTabs"] [role="tab"]:hover {{ background: #d6e2f8 !important; transform: translateY(-1px); }}
[data-testid="stTabs"] [role="tab"][aria-selected="true"],
[data-testid="stTabs"] [role="tab"][data-selected] {{ background: {primary} !important; }}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] p,
[data-testid="stTabs"] [role="tab"][data-selected] p {{ color: #ffffff !important; }}
</style>
""", unsafe_allow_html=True)


@st.cache_data
def _read_css(path, mtime):
    return Path(path).read_text(encoding="utf-8")


def load_css(filename="style.css"):
    """يقرأ ملف CSS الموجود بجانب هذا الملف ويحقنه في الصفحة (يتحدّث عند تعديل الملف)."""
    p = Path(__file__).resolve().parent / filename
    if p.exists():
        st.markdown(f"<style>{_read_css(str(p), p.stat().st_mtime)}</style>", unsafe_allow_html=True)
    else:
        st.warning(f"ملف التنسيق {filename} غير موجود بجانب ui_style.py")
