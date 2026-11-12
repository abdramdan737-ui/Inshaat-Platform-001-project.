# -*- coding: utf-8 -*-
"""واجهة Streamlit لدراسة الجدوى. الاستدعاء داخل التطبيق:
    from feasibility_ui import render_feasibility
    if choice == "دراسة الجدوى الاقتصادية": render_feasibility()
"""
import numpy as np
import pandas as pd
import streamlit as st
import feasibility_engine as fe
import feasibility_templates as tp

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

    # ================= المدخلات =================
    with T_in:
        with st.expander("A. القالب القطاعي وتعريف المشروع", expanded=True):
            c = st.columns([2, 1, 1])
            tpl = c[0].selectbox("القالب القطاعي", list(tp.TEMPLATES), key="tpl")
            D = tp.TEMPLATES[tpl]
            size = c[1].number_input(D["size_label"], 1.0, value=float(D["size"]), step=1.0, key=f"size_{tpl}")
            owner = c[2].selectbox("جهة التنفيذ", ["قطاع خاص", "قطاع عام/بلدية", "شراكة PPP", "استثمار مرخص (هيئة الاستثمار)"])
            name = st.text_input("اسم المشروع")
            sector = tpl
            tb = tp.build(tpl, size)
            k = f"{tpl}_{size:.0f}"
            st.info(D["note"] + "  |  الأرقام إرشادية، عايِرها بالـ BOQ وأسعار السوق المحلية.")
            c = st.columns(2)
            Nc = c[0].number_input("مدة الإنشاء (سنة)", 1, 10, int(D["Nc"]), key=f"nc_{tpl}")
            No = c[1].number_input("عمر التشغيل (سنة)", 1, 80, int(D["No"]), key=f"no_{tpl}")

        with st.expander("B. الكلفة الرأسمالية (CAPEX)", expanded=True):
            cap = table(tb["capex"], f"cap_{k}")
            c = st.columns(3)
            cont = c[0].number_input("احتياطي طوارئ على الكلفة %", 0.0, 50.0, float(D["cont"]), key=f"cont_{tpl}") / 100
            modes = [fe.LAND_BUY, fe.LAND_RENT, fe.LAND_FREE]
            land_mode = c[1].selectbox("الأرض", modes, index=modes.index(D["land"]), key=f"lm_{tpl}")
            land_value = c[2].number_input("قيمة الأرض (د.ع)", 0.0, step=1e7, format="%.0f", key=f"lv_{tpl}") if land_mode == fe.LAND_BUY else 0.0
            c = st.columns(3)
            land_rent = c[0].number_input("إيجار الأرض السنوي (د.ع)", 0.0, step=1e6, format="%.0f", key=f"lr_{tpl}") if land_mode == fe.LAND_RENT else 0.0
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
            st.caption("تحقق من نسبة الضريبة ومدة الإعفاء الممنوحة بموجب إجازة الاستثمار (قانون الاستثمار 13 لسنة 2006 وتعديلاته) قبل الاعتماد.")

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
    a = fe.prep(inp)
    m = fe.run(a)

    # ================= المؤشرات =================
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

    # ================= الحساسية =================
    with T_sen:
        be = fe.breakeven_revenue(a)
        st.metric("الحد الأدنى للإيراد لتحقيق NPV = 0 (نسبة من المتوقع)", pc(be))
        sdf = fe.sensitivity(a)
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
            o = fe.run(a, rev=x.iloc[1], opex=x.iloc[2], capex=x.iloc[3], r=x.iloc[4] / 100)
            rows.append([x.iloc[0], o["npv"], o["irr"] * 100 if np.isfinite(o["irr"]) else np.nan, o["bcr"]])
        st.dataframe(pd.DataFrame(rows, columns=["السيناريو", "NPV", "IRR %", "BCR"]), hide_index=True)

    # ================= مونت كارلو =================
    with T_mc:
        st.caption("توزيع مثلثي (أدنى، الأرجح، أعلى) لكل وسيط")
        mc = table(pd.DataFrame({"الوسيط": ["الإيراد ×", "التشغيل ×", "CAPEX ×", "معدل الخصم"],
                                 "أدنى": [0.7, 0.9, 0.95, r - 0.02], "الأرجح": [1.0, 1.0, 1.0, r],
                                 "أعلى": [1.1, 1.3, 1.4, r + 0.04]}), "mc")
        n = st.select_slider("عدد التكرارات", [500, 1000, 2000, 5000], 1000)
        if st.button("تشغيل المحاكاة"):
            P = [tuple(mc.iloc[i, 1:4].astype(float)) for i in range(4)]
            npv, irr = fe.monte_carlo(a, n, *P)
            p10, p50, p90 = np.nanpercentile(npv, [10, 50, 90])
            c = st.columns(4)
            c[0].metric("احتمال NPV > 0", pc((npv > 0).mean()))
            c[1].metric("P10", fmt(p10)); c[2].metric("P50", fmt(p50)); c[3].metric("P90", fmt(p90))
            h, e = np.histogram(npv, 30)
            st.bar_chart(pd.Series(h, index=[f"{x:,.0f}" for x in e[:-1]]))

    # ================= اقتصادي/اجتماعي =================
    with T_eco:
        st.caption("للمشاريع العامة/البلدية: منافع اجتماعية، عوامل تحويل للأسعار الظلية، معدل خصم اجتماعي، بلا ضرائب وتمويل.")
        ben = table(tb["benefits"], f"ben_{k}")
        c = st.columns(3)
        sc_c = c[0].number_input("عامل تحويل CAPEX", 0.3, 1.5, 0.9)
        sc_o = c[1].number_input("عامل تحويل التشغيل", 0.3, 1.5, 0.9)
        sr = c[2].number_input("معدل الخصم الاجتماعي %", 1.0, 30.0, 8.0) / 100
        eco = fe.economic(inp, ben, sc_c, sc_o, sr)
        c = st.columns(3)
        c[0].metric("ENPV", fmt(eco["npv"])); c[1].metric("EIRR", pc(eco["irr"])); c[2].metric("B/C اقتصادي", f"{eco['bcr']:.2f}")

    # ================= التدفقات =================
    with T_cf:
        df = pd.DataFrame({"السنة": m["t"], "الإيراد": m["rev"], "المصروفات": m["opex"], "EBITDA": m["ebitda"],
                           "الاندثار": m["dep"], "الضريبة": m["tax"], "CAPEX": m["capex"], "إحلال": m["repl"],
                           "ΔWC": m["dwc"], "قيمة نهائية": m["term"], "FCFF": m["fcff"],
                           "قرض مسحوب": m["draw"], "فائدة": m["interest"], "أصل القرض": m["principal"],
                           "FCFE": m["fcfe"], "DSCR": m["dscr"]})
        st.dataframe(df.style.format("{:,.0f}", subset=df.columns[1:-1]).format("{:.2f}", subset=["DSCR"]), hide_index=True)
        st.download_button("تنزيل CSV", df.to_csv(index=False).encode("utf-8-sig"), "cashflow.csv", "text/csv")
