# -*- coding: utf-8 -*-
"""الاستخدام في main.py:
    from wwtp_ui import render_wwtp
    elif choice == "تصميم محطة رفع ومعالجة مياه صرف":
        render_wwtp()
"""
import numpy as np
import pandas as pd
import streamlit as st
import wwtp_engine as we


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


def render_wwtp():
    st.header("🚰 تصميم محطة رفع ومعالجة مياه الصرف الصحي")
    st.caption("تصميم مفاهيمي أولي؛ المعايير المرجعية عامة (Metcalf & Eddy / Ten States) وتُستبدل بالمعيار الملزم للجهة المالكة.")
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
        n = lambda s: pd.to_numeric(s, errors="coerce").fillna(0)
        p["K_sum"] = float((n(fit.iloc[:, 1]) * n(fit.iloc[:, 2])).sum())
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
