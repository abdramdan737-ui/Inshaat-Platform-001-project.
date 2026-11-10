# -*- coding: utf-8 -*-

import streamlit as st
import os
import pandas as pd
import numpy as np
import numpy_financial as npf
import urllib.parse
import math
import copy
from pathlib import Path
from google import genai
import wwtp_engine as we

# =====================================================
# 1. إعدادات الصفحة الأساسية (مرة واحدة فقط)
# =====================================================
st.set_page_config(
    page_title="منصة إنشاءات للاستشارات الهندسية",
    layout="wide",
    page_icon="🏗️"
)

# =====================================================
# 🎨 تنسيقات الألوان والـ CSS
# =====================================================
st.markdown("""
<style>
    /* 1. خلفية الصفحة الهادئة */
    .stApp {
        background-color: #F0F4F8;
    }
    
    /* 2. النصوص والعناوين واضحة باللون الأزرق الداكن */
    h1, h2, h3, h4, h5, h6, p, span, label {
        color: #1E3A8A !important;
        opacity: 1 !important;
    }

    /* 3. تثبيت ألوان الأزرار والأيقونات لتكون واضحة ودائمة الوضوح */
    .stButton>button, .stDownloadButton>button {
        background-color: #ede1e3 !important;
        color: white !important;
        opacity: 1 !important;
        border: 2px solid #2596be !important;
        font-weight: bold;
        transition: all 0.3s ease;
    }

    /* 4. تأثير واضح وجميل عند تمرير الماوس فوق الأزرار أو الأيقونات */
    .stButton>button:hover, .stDownloadButton>button:hover {
        background-color: #bf2443 !important;
        border-color: #bf2443 !important;
        color: white !important;
        opacity: 1 !important;
    }
</style>
""", unsafe_allow_html=True)

# =====================================================
# إعدادات الاتصال والـ API والمجلدات
# =====================================================
BASE_DIR = Path(__file__).resolve().parent
REFERENCE_FOLDER = str(BASE_DIR / "reference_files")

def get_api_key():
    try:
        return st.secrets["GEMINI_API_KEY"]
    except (KeyError, FileNotFoundError):
        return os.environ.get("GEMINI_API_KEY")

API_KEY = get_api_key()
if not API_KEY:
    st.error("مفتاح GEMINI_API_KEY غير موجود. أضفه في .streamlit/secrets.toml أو كمتغير بيئة.")
    st.stop()

client = genai.Client(api_key=API_KEY)

# =====================================================
# القوالب القطاعية لدراسة الجدوى (feasibility_templates)
# =====================================================
LAND_BUY, LAND_RENT, LAND_FREE = "شراء", "إيجار سنوي", "مقدَّمة بلا كلفة"
FX, PCT = "ثابت سنوي", "% من الإيراد"

TEMPLATES = {
    "سكني (مجمع للإيجار)": dict(
        size_label="المساحة البنائية (م²)", size=5000.0, Nc=2, No=30, cont=5, wc=2, land=LAND_BUY,
        note="مجمع شقق مؤجرة. المساحة المؤجرة 80% من البنائية. مشاريع البيع تحتاج نموذج مبيعات (غير مشمول).",
        capex=[("أعمال مدنية وإنشائية", 450_000, 30), ("أعمال ميكانيكية وكهربائية", 120_000, 15),
               ("تشطيبات وتجهيزات", 80_000, 10), ("تصميم وإشراف واستشارات", 40_000, 30), ("تراخيص وتأسيس", 15_000, 5)],
        revenue=[("إيجار شقق", 0.80, 120_000, 90, 2, 3)],
        opex=[("صيانة وتشغيل", FX, 12_000, 3), ("خدمات مشتركة (كهرباء/مياه)", FX, 4_000, 3),
              ("إدارة وعمولات", PCT, 5, 0), ("رسوم وضرائب عقار", PCT, 2, 0)],
        repl=[("تجديد مصاعد وأنظمة ميكانيكية", 15, 40_000)], benefits=[]),

    "تجاري (مجمع/محلات)": dict(
        size_label="المساحة البنائية (م²)", size=8000.0, Nc=2, No=30, cont=5, wc=2, land=LAND_BUY,
        note="مجمع تجاري. المساحة المؤجرة 65% من البنائية، وإشغال مرتفع بعد 3 سنوات استقرار.",
        capex=[("أعمال مدنية وإنشائية", 500_000, 30), ("أعمال ميكانيكية وكهربائية (تكييف/إطفاء)", 180_000, 15),
               ("تشطيبات وواجهات", 150_000, 10), ("تصميم وإشراف واستشارات", 45_000, 30), ("تراخيص وتأسيس", 20_000, 5)],
        revenue=[("إيجار محلات ومعارض", 0.65, 220_000, 88, 3, 3)],
        opex=[("صيانة وتشغيل", FX, 15_000, 3), ("أمن ونظافة وخدمات مشتركة", FX, 10_000, 3),
              ("تسويق وإدارة", PCT, 6, 0)],
        repl=[("تجديد أنظمة التكييف والمصاعد", 12, 60_000)], benefits=[]),

    "صناعي (مصنع/مخازن)": dict(
        size_label="مساحة المنشأة (م²)", size=5000.0, Nc=2, No=25, cont=7, wc=15, land=LAND_BUY,
        note="مبيعات لكل م² منشأة وفق الطاقة المستغلة. المواد الأولية كنسبة من المبيعات. عدّل لكل صناعة.",
        capex=[("مباني وهياكل", 300_000, 30), ("خدمات وكهرباء وبنية داخلية", 150_000, 15),
               ("خطوط إنتاج وماكينات", 600_000, 10), ("تصميم وإشراف", 25_000, 30), ("تراخيص وتأسيس", 10_000, 5)],
        revenue=[("مبيعات الإنتاج", 1.0, 650_000, 75, 3, 3)],
        opex=[("مواد أولية ومستلزمات", PCT, 50, 0), ("رواتب وأجور", FX, 60_000, 4),
              ("طاقة ووقود", PCT, 4, 0), ("صيانة", FX, 20_000, 3), ("إدارة وتسويق", PCT, 4, 0)],
        repl=[("استبدال/تحديث ماكينات", 10, 200_000)], benefits=[]),

    "صحي (مستشفى خاص)": dict(
        size_label="عدد الأسرّة", size=100.0, Nc=3, No=30, cont=7, wc=8, land=LAND_BUY,
        note="مستشفى خاص. الإيراد لكل سرير سنوياً (إشغال 70% بعد 3 سنوات). الأجهزة الطبية تُستبدل كل 8 سنوات.",
        capex=[("مباني وأعمال مدنية", 120_000_000, 30), ("ميكانيكية وكهربائية وغازات طبية", 60_000_000, 15),
               ("أجهزة ومعدات طبية", 150_000_000, 8), ("تصميم وإشراف", 15_000_000, 30), ("تراخيص واعتماد", 5_000_000, 5)],
        revenue=[("إيراد خدمات علاجية لكل سرير", 1.0, 220_000_000, 70, 3, 4)],
        opex=[("رواتب الكوادر", FX, 55_000_000, 4), ("مستلزمات طبية وأدوية", PCT, 25, 0),
              ("صيانة وطاقة وخدمات", FX, 12_000_000, 3), ("إدارة وتأمين", PCT, 4, 0)],
        repl=[("استبدال أجهزة طبية", 8, 100_000_000), ("استبدال أجهزة طبية", 16, 100_000_000)], benefits=[]),

    "تعليمي (مدرسة/كلية خاصة)": dict(
        size_label="عدد الطلاب (الطاقة)", size=800.0, Nc=2, No=30, cont=5, wc=3, land=LAND_BUY,
        note="مدرسة خاصة. الإيراد أقساط دراسية لكل طالب، والرواتب أكبر بند تشغيلي.",
        capex=[("مباني وأعمال مدنية", 5_000_000, 30), ("ميكانيكية وكهربائية", 1_000_000, 15),
               ("أثاث ومختبرات وتجهيزات", 1_000_000, 8), ("تصميم وإشراف", 600_000, 30), ("تراخيص وتأسيس", 200_000, 5)],
        revenue=[("أقساط دراسية", 1.0, 3_200_000, 85, 4, 4)],
        opex=[("رواتب الكادر", FX, 1_300_000, 4), ("تشغيل وصيانة وخدمات", FX, 300_000, 3),
              ("إدارة وتسويق", PCT, 5, 0)],
        repl=[("تجديد أثاث ومختبرات", 10, 800_000)], benefits=[]),

    "بنية تحتية بإيراد (مياه/صرف)": dict(
        size_label="الطاقة التصميمية (م³/يوم)", size=20000.0, Nc=3, No=35, cont=10, wc=0, land=LAND_FREE,
        note="محطة معالجة بتعرفة. مالياً غالباً غير مجدية (تعرفة مدعومة). قيّمها اقتصادياً في تبويب 5 بالمنافع الاجتماعية.",
        capex=[("أعمال مدنية", 450_000, 40), ("معدات ميكانيكية وكهربائية", 550_000, 20),
               ("شبكات وخطوط ناقلة", 300_000, 40), ("تصميم وإشراف", 80_000, 40), ("تراخيص ودراسات", 20_000, 5)],
        revenue=[("تعرفة مياه (م³/سنة)", 365.0, 350, 70, 4, 3)],
        opex=[("طاقة وكيماويات", FX, 30_000, 3), ("رواتب وصيانة", FX, 25_000, 3), ("إدارة", PCT, 3, 0)],
        repl=[("استبدال مضخات ومعدات", 15, 150_000)],
        benefits=[("وفر كلف الأمراض المنقولة بالمياه", 150_000, 2), ("منافع بيئية وتقليل التلوث", 60_000, 2)]),

    "طرق وجسور (منافع اجتماعية)": dict(
        size_label="الطول (كم)", size=10.0, Nc=2, No=25, cont=10, wc=0, land=LAND_FREE,
        note="لا إيراد مباشر. المؤشرات المالية غير ذات معنى؛ استخدم تبويب 5 (EIRR وB/C اجتماعي).",
        capex=[("أعمال ترابية وتبليط وجسور", 3_200_000_000, 25), ("إنارة وعلامات وسلامة", 300_000_000, 15),
               ("تعويضات واستملاك", 250_000_000, 25), ("تصميم وإشراف", 150_000_000, 25)],
        revenue=[("لا إيراد مباشر", 0.0, 0, 100, 1, 0)],
        opex=[("صيانة دورية", FX, 40_000_000, 3)],
        repl=[("إعادة تبليط", 10, 500_000_000), ("إعادة تبليط", 20, 500_000_000)],
        benefits=[("وفر كلف تشغيل المركبات", 250_000_000, 3), ("وفر زمن الرحلات", 150_000_000, 3),
                  ("تقليل الحوادث", 60_000_000, 2)]),

    "مخصص (فارغ)": dict(
        size_label="معامل القياس (اتركه 1)", size=1.0, Nc=2, No=30, cont=5, wc=5, land=LAND_BUY,
        note="قالب عام: الكلف المدخلة مبالغ مطلقة (الحجم = 1).",
        capex=[("أعمال إنشائية", 5_000_000_000, 30), ("معدات وتجهيزات", 1_000_000_000, 10),
               ("تصميم وإشراف", 400_000_000, 30), ("تراخيص وتأسيس", 150_000_000, 5)],
        revenue=[("مصدر إيراد 1", 1.0, 1_000_000_000, 85, 2, 3)],
        opex=[("صيانة وتشغيل", FX, 150_000_000, 3), ("إدارة", PCT, 5, 0)],
        repl=[("إحلال", 15, 300_000_000)], benefits=[]),
}

def build_template(name, size):
    D, s = TEMPLATES[name], float(size)
    cap = pd.DataFrame([(n, r * s, l) for n, r, l in D["capex"]], columns=["البند", "المبلغ (د.ع)", "عمر الاندثار (سنة)"])
    rev = pd.DataFrame([(n, f * s, p, o, rm, g) for n, f, p, o, rm, g in D["revenue"]],
                       columns=["مصدر الإيراد", "الوحدات (عدد/م²)", "سعر الوحدة سنوياً (د.ع)",
                                "الإشغال/الاستغلال عند الاستقرار %", "سنوات الوصول للاستقرار", "نمو سنوي للسعر %"])
    ox = pd.DataFrame([(n, k, v * s if k == FX else v, g) for n, k, v, g in D["opex"]],
                      columns=["البند", "النوع", "القيمة (د.ع أو %)", "تصاعد سنوي %"])
    rp = pd.DataFrame([(n, y, r * s) for n, y, r in D["repl"]], columns=["بند الإحلال", "سنة التشغيل", "المبلغ (د.ع)"])
    ben = pd.DataFrame([(n, r * s, g) for n, r, g in D["benefits"]] or [("منفعة 1", 0.0, 2.0)],
                       columns=["المنفعة", "القيمة السنوية (د.ع)", "نمو %"])
    return dict(capex=cap, revenue=rev, opex=ox, repl=rp, benefits=ben)

# =====================================================
# محرك دراسة الجدوى الاقتصادية المتقدم (FCFF/FCFE)
# =====================================================
def _num(s):
    return pd.to_numeric(pd.Series(s), errors="coerce").fillna(0.0).to_numpy(float)

def _irr(cf):
    try:
        v = npf.irr(cf)
        return float(v) if np.isfinite(v) else np.nan
    except Exception:
        return np.nan

def _tax(base, rate, hol_start, hol_len):
    tax, nol = np.zeros(len(base)), 0.0
    for t, b in enumerate(base):
        if b < 0:
            nol += -b
            continue
        if hol_start <= t < hol_start + hol_len:
            continue
        use = min(nol, b)
        nol -= use
        tax[t] = (b - use) * rate
    return tax

def _payback(cf, Nc):
    cum = np.cumsum(cf)
    idx = np.where((cum >= 0) & (np.arange(len(cf)) >= Nc))[0]
    if len(idx) == 0 or cf[idx[0]] == 0:
        return np.nan
    i = idx[0]
    return (i - 1) + (-cum[i - 1]) / cf[i] - (Nc - 1)

def prep(i):
    a = dict(i["scalars"])
    Nc = int(a["Nc"])
    cx, rv, ox, rp = i["capex"], i["revenue"], i["opex"], i["repl"]
    a["cx_amt"], a["cx_life"] = _num(cx.iloc[:, 1]), np.maximum(_num(cx.iloc[:, 2]), 1)
    ph = _num(i["phase"].iloc[:, 1])
    ph = ph / ph.sum() if len(ph) == Nc and ph.sum() > 0 else np.full(Nc, 1 / Nc)
    a["phase"] = ph
    a["units"], a["price"] = _num(rv.iloc[:, 1]), _num(rv.iloc[:, 2])
    a["occ"], a["ramp"] = _num(rv.iloc[:, 3]) / 100, np.maximum(_num(rv.iloc[:, 4]), 1)
    a["rg"] = _num(rv.iloc[:, 5]) / 100
    pct = ox.iloc[:, 1].astype(str).str.startswith("%").to_numpy()
    v = _num(ox.iloc[:, 2])
    a["ox_pct"], a["ox_val"], a["og"] = pct, np.where(pct, v / 100, v), _num(ox.iloc[:, 3]) / 100
    a["rp_yr"], a["rp_amt"] = _num(rp.iloc[:, 1]).astype(int), _num(rp.iloc[:, 2])
    return a

def run(a, rev=1.0, opex=1.0, capex=1.0, r=None):
    Nc, No = int(a["Nc"]), int(a["No"])
    T = Nc + No
    r = a["r"] if r is None else r
    t = np.arange(T)
    op = t >= Nc
    k = np.where(op, t - Nc + 1, 0)
    kk = k[:, None]
    kp = np.maximum(kk - 1, 0)

    ramp = np.minimum(1.0, kk / a["ramp"][None, :])
    R = (a["units"] * a["price"] * a["occ"] * ramp * (1 + a["rg"]) ** kp * (kk >= 1)).sum(1) * rev
    fx = (a["ox_val"] * (~a["ox_pct"]) * (1 + a["og"]) ** kp * (kk >= 1)).sum(1)
    var = R * a["ox_val"][a["ox_pct"]].sum()
    rent = a["land_rent"] * (1 + a["rent_g"]) ** kp[:, 0] * op if a["land_mode"] == LAND_RENT else 0.0
    O = (fx + var + rent) * opex
    E = R - O
    hard = a["cx_amt"].sum() * (1 + a["cont"]) * capex
    cap = np.zeros(T)
    cap[:Nc] = hard * a["phase"]
    buy = a["land_mode"] == LAND_BUY
    if buy:
        cap[0] += a["land_value"]
    dep = (((kk >= 1) & (kk <= a["cx_life"][None, :])) *
           (a["cx_amt"] * (1 + a["cont"]) * capex / a["cx_life"])[None, :]).sum(1)
    repl = np.array([a["rp_amt"][a["rp_yr"] == kv].sum() if kv > 0 else 0.0 for kv in k]) * capex
    term = np.zeros(T)
    term[-1] = a["salvage"] + (a["land_value"] * (1 + a["land_g"]) ** No if buy else 0.0)
    wc = a["wc"] * R
    dwc = np.diff(np.r_[0.0, wc])
    wc_rel = np.zeros(T)
    wc_rel[-1] = wc[-1]
    ebit = E - dep - repl
    tax_u = _tax(ebit, a["tax"], Nc, a["holiday"])
    fcff = E - tax_u - repl - dwc - cap + term + wc_rel

    draw = cap * a["debt"]
    tot, n, rs = draw.sum(), max(int(a["repay"]), 1), Nc + int(a["grace"])
    intr, prin, bal = np.zeros(T), np.zeros(T), 0.0
    for s in range(T):
        intr[s] = bal * a["ir"]
        bal += draw[s]
        if rs <= s < rs + n:
            prin[s] = min(bal, tot / n)
            bal -= prin[s]
    prin[-1] += bal
    tax_l = _tax(ebit - intr, a["tax"], Nc, a["holiday"])
    fcfe = E - tax_l - repl - dwc - cap + term + wc_rel + draw - intr - prin
    cfads = E - tax_l - repl - dwc
    ds = intr + prin
    dscr = np.where((ds > 0) & op, cfads / np.where(ds > 0, ds, 1), np.nan)

    disc = (1 + r) ** t
    npv = float(npf.npv(r, fcff))
    try:
        mirr = float(npf.mirr(fcff, r, r))
    except Exception:
        mirr = np.nan
    pv = lambda x: float((x / disc).sum())
    cost_pv = pv(cap + O + repl + tax_u + np.maximum(dwc, 0))
    m = dict(npv=npv, irr=_irr(fcff), mirr=mirr,
             bcr=pv(R + term + wc_rel) / cost_pv if cost_pv else np.nan,
             pi=1 + npv / pv(cap) if pv(cap) else np.nan,
             payback=_payback(fcff, Nc), dpayback=_payback(fcff / disc, Nc),
             invest=float(cap.sum()), roi=float((E - tax_u)[op].mean() / cap.sum()) if cap.sum() else np.nan,
             irr_e=_irr(fcfe), npv_e=float(npf.npv(a["ke"], fcfe)),
             dscr_min=float(np.nanmin(dscr)) if np.isfinite(dscr).any() else np.nan,
             dscr_avg=float(np.nanmean(dscr)) if np.isfinite(dscr).any() else np.nan,
             debt=float(tot))
    m.update(t=t, rev=R, opex=O, ebitda=E, dep=dep, tax=tax_u, capex=cap, repl=repl, dwc=dwc,
             term=term + wc_rel, fcff=fcff, fcfe=fcfe, interest=intr, principal=prin, draw=draw, dscr=dscr)
    return m

def breakeven_revenue(a):
    f = lambda x: run(a, rev=x)["npv"]
    lo, hi = 0.0, 5.0
    if f(hi) < 0:
        return np.nan
    for _ in range(40):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if f(mid) < 0 else (lo, mid)
    return (lo + hi) / 2

def sensitivity(a, deltas=(-0.3, -0.2, -0.1, 0, 0.1, 0.2, 0.3)):
    out = {"الإيراد": [run(a, rev=1 + d)["npv"] for d in deltas],
           "التشغيل": [run(a, opex=1 + d)["npv"] for d in deltas],
           "الكلفة الرأسمالية": [run(a, capex=1 + d)["npv"] for d in deltas],
           "معدل الخصم": [run(a, r=a["r"] * (1 + d))["npv"] for d in deltas]}
    return pd.DataFrame(out, index=[f"{d:+.0%}" for d in deltas])

def monte_carlo(a, n, rev, opex, capex, r, seed=42):
    g = np.random.default_rng(seed)
    S = [g.triangular(*p, n) for p in (rev, opex, capex, r)]
    res = [run(a, rev=S[0][j], opex=S[1][j], capex=S[2][j], r=S[3][j]) for j in range(n)]
    return np.array([x["npv"] for x in res]), np.array([x["irr"] for x in res])

def economic(i, benefits, scf_capex, scf_opex, rate):
    j = copy.deepcopy(i)
    j["scalars"].update(tax=0.0, debt=0.0, holiday=0, r=rate)
    b = pd.DataFrame({0: benefits.iloc[:, 0].values, 1: 1.0, 2: _num(benefits.iloc[:, 1]),
                      3: 100.0, 4: 1.0, 5: _num(benefits.iloc[:, 2])})
    j["revenue"] = pd.concat([j["revenue"].set_axis(range(6), axis=1), b], ignore_index=True)
    return run(prep(j), capex=scf_capex, opex=scf_opex)

# =====================================================
# واجهة دراسة الجدوى الاقتصادية (render_feasibility)
# =====================================================
SEL = st.column_config.SelectboxColumn
fmt = lambda x: "—" if x is None or not np.isfinite(x) else f"{x:,.0f}"
pc = lambda x: "—" if x is None or not np.isfinite(x) else f"{x:.2%}"
yr = lambda x: "لا يُسترد" if x is None or not np.isfinite(x) else f"{x:.1f} سنة"

def table(df, key, cfg=None):
    return st.data_editor(df, num_rows="dynamic", use_container_width=True, key=key, column_config=cfg or {})

def render_feasibility():
    st.header("📈 دراسة الجدوى الاقتصادية والمالية")
    T_in, T_res, T_sen, T_mc, T_eco, T_cf = st.tabs(
        ["1) المدخلات", "2) المؤشرات", "3) الحساسية والتعادل", "4) المخاطر (مونت كارلو)",
         "5) التحليل الاقتصادي/الاجتماعي", "6) جدول التدفقات"])

    with T_in:
        with st.expander("A. القالب القطاعي وتعريف المشروع", expanded=True):
            c = st.columns([2, 1, 1])
            tpl = c[0].selectbox("القالب القطاعي", list(TEMPLATES), key="tpl")
            D = TEMPLATES[tpl]
            size = c[1].number_input(D["size_label"], 1.0, value=float(D["size"]), step=1.0, key=f"size_{tpl}")
            owner = c[2].selectbox("جهة التنفيذ", ["قطاع خاص", "قطاع عام/بلدية", "شراكة PPP", "استثمار مرخص (هيئة الاستثمار)"])
            name = st.text_input("اسم المشروع")
            sector = tpl
            tb = build_template(tpl, size)
            k = f"{tpl}_{size:.0f}"
            st.info(D["note"] + "  |  الأرقام إرشادية، عايِرها بالـ BOQ وأسعار السوق المحلية.")
            c = st.columns(2)
            Nc = c[0].number_input("مدة الإنشاء (سنة)", 1, 10, int(D["Nc"]), key=f"nc_{tpl}")
            No = c[1].number_input("عمر التشغيل (سنة)", 1, 80, int(D["No"]), key=f"no_{tpl}")

        with st.expander("B. الكلفة الرأسمالية (CAPEX)", expanded=True):
            cap = table(tb["capex"], f"cap_{k}")
            c = st.columns(3)
            cont = c[0].number_input("احتياطي طوارئ على الكلفة %", 0.0, 50.0, float(D["cont"]), key=f"cont_{tpl}") / 100
            modes = [LAND_BUY, LAND_RENT, LAND_FREE]
            land_mode = c[1].selectbox("الأرض", modes, index=modes.index(D["land"]), key=f"lm_{tpl}")
            land_value = c[2].number_input("قيمة الأرض (د.ع)", 0.0, step=1e7, format="%.0f", key=f"lv_{tpl}") if land_mode == LAND_BUY else 0.0
            c = st.columns(3)
            land_rent = c[0].number_input("إيجار الأرض السنوي (د.ع)", 0.0, step=1e6, format="%.0f", key=f"lr_{tpl}") if land_mode == LAND_RENT else 0.0
            rent_g = c[1].number_input("تصاعد الإيجار سنوياً %", 0.0, 30.0, 3.0) / 100
            land_g = c[2].number_input("نمو قيمة الأرض سنوياً %", 0.0, 30.0, 0.0) / 100
            st.caption("توزيع الصرف على سنوات الإنشاء (يُطبَّع إلى 100%)")
            ph_df = pd.DataFrame({"سنة الإنشاء": range(1, int(Nc) + 1), "نسبة الصرف %": [100 / Nc] * int(Nc)})
            phase = st.data_editor(ph_df, key=f"ph{Nc}", use_container_width=True)

        with st.expander("C. مصادر الإيراد", expanded=True):
            rev = table(tb["revenue"], f"rev_{k}")

        with st.expander("D. المصروفات التشغيلية والإحلال", expanded=True):
            ox = table(tb["opex"], f"ox_{k}", {"النوع": SEL(options=["ثابت سنوي", "% من الإيراد"])})
            rp = table(tb["repl"], f"rp_{k}")
            c = st.columns(2)
            wc = c[0].number_input("رأس المال العامل % من الإيراد", 0.0, 50.0, float(D["wc"]), key=f"wc_{tpl}") / 100
            salvage = c[1].number_input("قيمة الخردة/التصفية في نهاية العمر (د.ع)", 0.0, step=1e7, format="%.0f")

        with st.expander("E. الضريبة ومعدلات الخصم", expanded=True):
            c = st.columns(4)
            tax = c[0].number_input("ضريبة الدخل %", 0.0, 50.0, 15.0) / 100
            hol = c[1].number_input("إعفاء ضريبي (سنوات من بدء التشغيل)", 0, 30, 0)
            r = c[2].number_input("معدل الخصم (WACC) %", 0.0, 60.0, 12.0, 0.5) / 100
            ke = c[3].number_input("كلفة حقوق الملكية %", 0.0, 80.0, 18.0, 0.5) / 100
            st.caption("تحقق من نسبة الضريبة ومدة الإعفاء الممنوحة بموجب إجازة الاستثمار قبل الاعتماد.")

        with st.expander("F. هيكل التمويل"):
            c = st.columns(4)
            debt = c[0].number_input("نسبة القرض من CAPEX %", 0.0, 90.0, 0.0) / 100
            ir = c[1].number_input("فائدة القرض %", 0.0, 40.0, 8.0) / 100
            grace = c[2].number_input("فترة سماح بعد التشغيل (سنة)", 0, 15, 1)
            repay = c[3].number_input("سنوات السداد", 1, 30, 8)

    inp = dict(capex=cap, phase=phase, revenue=rev, opex=ox, repl=rp,
               scalars=dict(Nc=Nc, No=No, cont=cont, land_mode=land_mode, land_value=land_value, land_g=land_g,
                            land_rent=land_rent, rent_g=rent_g, wc=wc, tax=tax, holiday=hol, salvage=salvage,
                            debt=debt, ir=ir, grace=grace, repay=repay, r=r, ke=ke))
    a = prep(inp)
    m = run(a)

    with T_res:
        st.caption(f"{name} | {sector} | {owner}")
        c = st.columns(4)
        c[0].metric("إجمالي الاستثمار", fmt(m["invest"]))
        c[1].metric("NPV (FCFF)", fmt(m["npv"]))
        c[2].metric("IRR", pc(m["irr"]))
        c[3].metric("MIRR", pc(m["mirr"]))
        c = st.columns(4)
        c[0].metric("BCR", f"{m['bcr']:.2f}")
        c[1].metric("مؤشر الربحية PI", f"{m['pi']:.2f}")
        c[2].metric("الاسترداد البسيط (من بدء التشغيل)", yr(m["payback"]))
        c[3].metric("الاسترداد المخصوم", yr(m["dpayback"]))
        if debt > 0:
            c = st.columns(4)
            c[0].metric("IRR لحقوق الملكية", pc(m["irr_e"]))
            c[1].metric("NPV لحقوق الملكية", fmt(m["npv_e"]))
            c[2].metric("DSCR الأدنى", f"{m['dscr_min']:.2f}")
            c[3].metric("DSCR المتوسط", f"{m['dscr_avg']:.2f}")
        checks = {"NPV > 0": m["npv"] > 0, "IRR > معدل الخصم": m["irr"] > r if np.isfinite(m["irr"]) else False,
                  "BCR > 1": m["bcr"] > 1, "الاسترداد < عمر المشروع": np.isfinite(m["payback"]) and m["payback"] < No}
        if debt > 0:
            checks["DSCR الأدنى ≥ 1.25"] = np.isfinite(m["dscr_min"]) and m["dscr_min"] >= 1.25
        st.dataframe(pd.DataFrame({"المعيار": checks.keys(), "النتيجة": ["✅" if v else "❌" for v in checks.values()]}),
                     hide_index=True)
        st.line_chart(pd.Series(np.cumsum(m["fcff"]), index=m["t"], name="التدفق التراكمي"))

    with T_sen:
        be = breakeven_revenue(a)
        st.metric("الحد الأدنى للإيراد لتحقيق NPV = 0 (نسبة من المتوقع)", pc(be))
        sdf = sensitivity(a)
        st.line_chart(sdf)
        tor = pd.DataFrame({"NPV عند -20%": sdf.loc["-20%"], "NPV عند +20%": sdf.loc["+20%"]})
        tor["التأرجح"] = (tor.iloc[:, 0] - tor.iloc[:, 1]).abs()
        st.dataframe(tor.sort_values("التأرجح", ascending=False).style.format("{:,.0f}"))
        st.caption("جدول Tornado: المتغير الأعلى تأرجحاً هو الأخطر على الجدوى.")
        st.subheader("السيناريوهات")
        sc = table(pd.DataFrame({"السيناريو": ["متشائم", "أساس", "متفائل"], "الإيراد ×": [0.8, 1.0, 1.1],
                                 "التشغيل ×": [1.15, 1.0, 0.95], "CAPEX ×": [1.2, 1.0, 0.95],
                                 "معدل الخصم %": [r * 100 + 3, r * 100, r * 100 - 1]}), "sc")
        rows = []
        for _, x in sc.iterrows():
            o = run(a, rev=x.iloc[1], opex=x.iloc[2], capex=x.iloc[3], r=x.iloc[4] / 100)
            rows.append([x.iloc[0], o["npv"], o["irr"] * 100 if np.isfinite(o["irr"]) else np.nan, o["bcr"]])
        st.dataframe(pd.DataFrame(rows, columns=["السيناريو", "NPV", "IRR %", "BCR"]), hide_index=True)

    with T_mc:
        st.caption("توزيع مثلثي (أدنى، الأرجح، أعلى) لكل وسيط")
        mc = table(pd.DataFrame({"الوسيط": ["الإيراد ×", "التشغيل ×", "CAPEX ×", "معدل الخصم"],
                                 "أدنى": [0.7, 0.9, 0.95, r - 0.02], "الأرجح": [1.0, 1.0, 1.0, r],
                                 "أعلى": [1.1, 1.3, 1.4, r + 0.04]}), "mc")
        n = st.select_slider("عدد التكرارات", [500, 1000, 2000, 5000], 1000)
        if st.button("تشغيل المحاكاة"):
            P = [tuple(mc.iloc[i, 1:4].astype(float)) for i in range(4)]
            npv, irr = monte_carlo(a, n, *P)
            p10, p50, p90 = np.nanpercentile(npv, [10, 50, 90])
            c = st.columns(4)
            c[0].metric("احتمال NPV > 0", pc((npv > 0).mean()))
            c[1].metric("P10", fmt(p10)); c[2].metric("P50", fmt(p50)); c[3].metric("P90", fmt(p90))
            h, e = np.histogram(npv, 30)
            st.bar_chart(pd.Series(h, index=[f"{x:,.0f}" for x in e[:-1]]))

    with T_eco:
        st.caption("للمشاريع العامة/البلدية: منافع اجتماعية، عوامل تحويل للأسعار الظلية، معدل خصم اجتماعي، بلا ضرائب وتمويل.")
        ben = table(tb["benefits"], f"ben_{k}")
        c = st.columns(3)
        sc_c = c[0].number_input("عامل تحويل CAPEX", 0.3, 1.5, 0.9)
        sc_o = c[1].number_input("عامل تحويل التشغيل", 0.3, 1.5, 0.9)
        sr = c[2].number_input("معدل الخصم الاجتماعي %", 1.0, 30.0, 8.0) / 100
        eco = economic(inp, ben, sc_c, sc_o, sr)
        c = st.columns(3)
        c[0].metric("ENPV", fmt(eco["npv"])); c[1].metric("EIRR", pc(eco["irr"])); c[2].metric("B/C اقتصادي", f"{eco['bcr']:.2f}")

    with T_cf:
        df = pd.DataFrame({"السنة": m["t"], "الإيراد": m["rev"], "المصروفات": m["opex"], "EBITDA": m["ebitda"],
                           "الاندثار": m["dep"], "الضريبة": m["tax"], "CAPEX": m["capex"], "إحلال": m["repl"],
                           "ΔWC": m["dwc"], "قيمة نهائية": m["term"], "FCFF": m["fcff"],
                           "قرض مسحوب": m["draw"], "فائدة": m["interest"], "أصل القرض": m["principal"],
                           "FCFE": m["fcfe"], "DSCR": m["dscr"]})
        st.dataframe(df.style.format("{:,.0f}", subset=df.columns[1:-1]).format("{:.2f}", subset=["DSCR"]), hide_index=True)
        st.download_button("تنزيل CSV", df.to_csv(index=False).encode("utf-8-sig"), "cashflow.csv", "text/csv")


# =====================================================
# 2. القائمة الجانبية (Sidebar)
# =====================================================
with st.sidebar:
    st.title("🏛️ منصة إنشاءات للاستشارات الهندسية")
    st.markdown("---")
    choice = st.radio(
        "اختر القسم المطلوب:",
        [
            "دراسة الجدوى الاقتصادية",
            "تصميم محطة رفع ومعالجة مياه صرف"
        ]
    )
    st.markdown("---")
    st.info("اعداد وتصميم المهندس الاستشاري عبد الغفور رمضان اللهيبي")


# =====================================================
# دوال المساعدة لعرض نتائج المحطة (معرفة محلياً لمنع NameError)
# =====================================================
def _f(v):
    if isinstance(v, (float, np.floating)):
        if not np.isfinite(v):
            return "—"
        return f"{v:,.3f}" if abs(v) < 10 else (f"{v:,.1f}" if abs(v) < 1000 else f"{v:,.0f}")
    return str(v)

def show(res, title):
    st.subheader(title)
    st.dataframe(pd.DataFrame([(a, _f(b), c) for a, b, c in res["rows"]], columns=["المعلمة", "القيمة", "الوحدة"]),
                 hide_index=True, use_container_width=True)
    for n, v, rng, ok in res["checks"]:
        (st.success if ok else st.warning)(f"{'✅' if ok else '⚠️'} {n}: {_f(v)}  (المدى المرجعي {rng})")


# =====================================================
# توجيه الأقسام حسب الاختيار
# =====================================================
if choice == "دراسة الجدوى الاقتصادية":
    render_feasibility()

elif choice == "تصميم محطة رفع ومعالجة مياه صرف":
    st.header("🚰 تصميم محطة رفع ومعالجة مياه الصرف الصحي")
    st.caption("تصميم مفاهيمي أولي؛ المعايير المرجعية عامة وتُستبدل بالمعيار الملزم للجهة المالكة.")
    T = st.tabs(["1) المدخلات", "2) التدفق والأحمال", "3) الرفع وخط الضخ", "4) المعالجة", "5) التحقق والتقرير"])

    with T[0]:
        p, groups = dict(we.DEFAULTS), {}
        for g, k, lab, d, mn, stp in we.PARAMS:
            groups.setdefault(g, []).append((k, lab, d, mn, stp))
        for g, items in groups.items():
            with st.expander(g, expanded=g.startswith("1")):
                cols = st.columns(3)
                for i, (k, lab, d, mn, stp) in enumerate(items):
                    p[k] = cols[i % 3].number_input(lab, min_value=mn, value=d, step=stp, key=f"ww_{k}")
        c = st.columns(2)
        p["peak_method"] = c[0].selectbox("طريقة معامل الذروة", we.PEAK_METHODS, key="ww_pm")
        p["hyd"] = c[1].selectbox("معادلة الفقد الاحتكاكي", we.HYD_METHODS, key="ww_hyd")
        st.caption("المرفقات والقطع الخاصة في خط الضخ (ΣK·v²/2g)")
        fit = st.data_editor(pd.DataFrame({"القطعة": ["صمام لا رجوع", "صمام بوابة", "كوع 90°", "مخرج"],
                                           "K": [2.0, 0.2, 0.3, 1.0], "العدد": [1, 2, 4, 1]}),
                             num_rows="dynamic", key="ww_fit", use_container_width=True)
        n_func = lambda s: pd.to_numeric(s, errors="coerce").fillna(0)
        p["K_sum"] = float((n_func(fit.iloc[:, 1]) * n_func(fit.iloc[:, 2])).sum())
        st.info(f"ΣK = {p['K_sum']:.2f}")

    R = we.run_all(p)
    with T[1]:
        show(R["flows"], "التدفق والأحمال")
    with T[2]:
        show(R["pump"], "خط الضخ والمضخات")
        cv = pd.DataFrame(R["pump"]["d"]["curve"]).set_index("Q (لتر/ث)")
        st.line_chart(cv)
        st.caption("منحنى النظام يُطابَق مع منحنى المضخة المختارة عند نقطة التشغيل؛ يوضح الغلاف C=100..140 مدى عدم اليقين.")
        show(R["well"], "بئر الرفع")
    with T[3]:
        show(R["primary"], "الترسيب الابتدائي")
        show(R["bio"], "الحمأة المنشّطة (RAS / WAS / الأكسجين)")
        show(R["secondary"], "الترسيب الثانوي")
    with T[4]:
        rows = [(u, n_, _f(v), r, "✅" if ok else "⚠️") for u, res in R.items() for n_, v, r, ok in res["checks"]]
        df = pd.DataFrame(rows, columns=["الوحدة", "الفحص", "القيمة", "المدى", "الحالة"])
        st.dataframe(df, hide_index=True, use_container_width=True)
        st.metric("عدد التحذيرات", int((df["الحالة"] == "⚠️").sum()))
        st.download_button("تنزيل نتائج الفحص CSV", df.to_csv(index=False).encode("utf-8-sig"), "wwtp_checks.csv", "text/csv")
        st.markdown("**غير مشمول (للتوسعة):** صدمة مائية، NPSHa/NPSHr، مولّدات وطاقة احتياطية، التطهير بالكلور، "
                    "نترجة/نزع نيتروجين، معالجة الحمأة، مصافي وحصى (Screening/Grit)، التحقق من حدود التصريف المحلية.")
