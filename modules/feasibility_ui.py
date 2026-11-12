import numpy as np
import pandas as pd
import streamlit as st
from modules.feasibility_templates import TEMPLATES, build_template, LAND_BUY, LAND_RENT, LAND_FREE, FX
from modules.feasibility_engine import prep, run, sensitivity, breakeven_revenue, monte_carlo, economic

SEL=st.column_config.SelectboxColumn
def fmt(x):
    return "—" if x is None or not np.isfinite(x) else f"{x:,.0f}"
def pct(x):
    return "—" if x is None or not np.isfinite(x) else f"{x:.2%}"
def years(x):
    return "لا يُسترد" if x is None or not np.isfinite(x) else f"{x:.1f} سنة"
def editor(df,key,cfg=None):
    return st.data_editor(df,num_rows="dynamic",use_container_width=True,key=key,column_config=cfg or {})

def render_feasibility():
    st.title("دراسة الجدوى الاقتصادية والمالية")
    st.caption("نموذج تحليلي مرن للمشاريع الاستثمارية والخدمية — جميع القيم قابلة للتعديل.")
    tabs=st.tabs(["المدخلات","المؤشرات","الحساسية والتعادل","مخاطر مونت كارلو","التحليل الاقتصادي","التدفقات النقدية"])
    with tabs[0]:
        with st.expander("A · تعريف المشروع والقالب القطاعي",expanded=True):
            c=st.columns([2,1,1])
            tpl=c[0].selectbox("القالب القطاعي",list(TEMPLATES),key="tpl")
            D=TEMPLATES[tpl]
            size=c[1].number_input(D["size_label"],min_value=1.,value=float(D["size"]),step=1.,key=f"size_{tpl}")
            owner=c[2].selectbox("جهة التنفيذ",["قطاع خاص","قطاع عام/بلدية","شراكة","استثمار مرخص"])
            name=st.text_input("اسم المشروع",key="project_name")
            c=st.columns(2)
            Nc=c[0].number_input("مدة الإنشاء (سنة)",1,10,int(D["Nc"]),key=f"nc_{tpl}")
            No=c[1].number_input("عمر التشغيل (سنة)",1,80,int(D["No"]),key=f"no_{tpl}")
            st.info(D["note"]+" الأرقام الافتراضية إرشادية وليست أسعاراً سوقية معتمدة.")
        tb=build_template(tpl,size); key=f"{tpl}_{size:.3f}"
        with st.expander("B · الكلفة الرأسمالية والأرض",expanded=True):
            cap=editor(tb["capex"],f"cap_{key}")
            c=st.columns(3)
            cont=c[0].number_input("احتياطي طوارئ (%)",0.,50.,float(D["cont"]),key=f"cont_{tpl}")/100
            land_mode=c[1].selectbox("الأرض",[LAND_BUY,LAND_RENT,LAND_FREE],index=[LAND_BUY,LAND_RENT,LAND_FREE].index(D["land"]),key=f"land_{tpl}")
            land_value=c[2].number_input("قيمة الأرض (د.ع)",min_value=0.,step=10000000.,key=f"lv_{tpl}") if land_mode==LAND_BUY else 0.
            c=st.columns(2)
            land_rent=c[0].number_input("إيجار الأرض السنوي (د.ع)",min_value=0.,step=1000000.,key=f"lr_{tpl}") if land_mode==LAND_RENT else 0.
            rent_g=c[1].number_input("تصاعد الإيجار سنوياً (%)",0.,30.,3.)/100
            land_g=st.number_input("نمو قيمة الأرض سنوياً (%)",0.,30.,0.)/100
            st.caption("توزيع الصرف على سنوات الإنشاء")
            phase_df=pd.DataFrame({"سنة الإنشاء":range(1,int(Nc)+1),"نسبة الصرف %":[100/Nc]*int(Nc)})
            phase=st.data_editor(phase_df,key=f"phase_{Nc}",use_container_width=True)
        with st.expander("C · مصادر الإيراد",expanded=True):
            rev=editor(tb["revenue"],f"rev_{key}")
        with st.expander("D · المصروفات والإحلال"):
            ox=editor(tb["opex"],f"ox_{key}",{"النوع":SEL(options=[FX,"% من الإيراد"])})
            rp=editor(tb["repl"],f"rp_{key}")
            c=st.columns(2)
            wc=c[0].number_input("رأس المال العامل (% من الإيراد)",0.,50.,float(D["wc"]),key=f"wc_{tpl}")/100
            salvage=c[1].number_input("قيمة الخردة/التصفية (د.ع)",min_value=0.,step=10000000.)
        with st.expander("E · الضرائب ومعدلات الخصم"):
            c=st.columns(4)
            tax=c[0].number_input("ضريبة الدخل (%)",0.,50.,15.)/100
            hol=c[1].number_input("الإعفاء الضريبي (سنوات تشغيل)",0,30,0)
            r=c[2].number_input("معدل الخصم WACC (%)",0.,60.,12.,.5)/100
            ke=c[3].number_input("كلفة حقوق الملكية (%)",0.,80.,18.,.5)/100
            st.caption("تحقق من المعاملة الضريبية الفعلية والإعفاءات القانونية قبل اعتماد الدراسة.")
        with st.expander("F · التمويل"):
            c=st.columns(4)
            debt=c[0].number_input("نسبة القرض من CAPEX (%)",0.,90.,0.)/100
            ir=c[1].number_input("فائدة القرض (%)",0.,40.,8.)/100
            grace=c[2].number_input("فترة السماح بعد التشغيل (سنة)",0,15,1)
            repay=c[3].number_input("سنوات السداد",1,30,8)

    inp=dict(capex=cap,phase=phase,revenue=rev,opex=ox,repl=rp,scalars=dict(
        Nc=Nc,No=No,cont=cont,land_mode=land_mode,land_value=land_value,land_g=land_g,
        land_rent=land_rent,rent_g=rent_g,wc=wc,tax=tax,holiday=hol,salvage=salvage,
        debt=debt,ir=ir,grace=grace,repay=repay,r=r,ke=ke))
    try:
        a=prep(inp); m=run(a)
    except Exception as exc:
        st.error(f"تعذر حساب النتائج بسبب مدخلات غير صالحة: {exc}")
        return

    with tabs[1]:
        st.caption(f"{name or 'مشروع دون اسم'} · {tpl} · {owner}")
        c=st.columns(4)
        c[0].metric("إجمالي الاستثمار",fmt(m["invest"]))
        c[1].metric("NPV — FCFF",fmt(m["npv"]))
        c[2].metric("IRR",pct(m["irr"]))
        c[3].metric("MIRR",pct(m["mirr"]))
        c=st.columns(4)
        c[0].metric("BCR",fmt(m["bcr"]))
        c[1].metric("مؤشر الربحية PI",fmt(m["pi"]))
        c[2].metric("الاسترداد البسيط",years(m["payback"]))
        c[3].metric("الاسترداد المخصوم",years(m["dpayback"]))
        if debt>0:
            c=st.columns(4)
            c[0].metric("IRR حقوق الملكية",pct(m["irr_e"]))
            c[1].metric("NPV حقوق الملكية",fmt(m["npv_e"]))
            c[2].metric("DSCR الأدنى",fmt(m["dscr_min"]))
            c[3].metric("DSCR المتوسط",fmt(m["dscr_avg"]))
        checks={"NPV موجب":m["npv"]>0,"IRR أعلى من معدل الخصم":np.isfinite(m["irr"]) and m["irr"]>r,
                "BCR أكبر من 1":np.isfinite(m["bcr"]) and m["bcr"]>1,
                "الاسترداد ضمن عمر التشغيل":np.isfinite(m["payback"]) and m["payback"]<No}
        if debt>0: checks["DSCR الأدنى ≥ 1.25"]=np.isfinite(m["dscr_min"]) and m["dscr_min"]>=1.25
        st.dataframe(pd.DataFrame({"المعيار":list(checks),"النتيجة":["متحقق" if v else "غير متحقق" for v in checks.values()]}),hide_index=True,use_container_width=True)
        st.line_chart(pd.Series(np.cumsum(m["fcff"]),index=m["t"],name="التدفق النقدي التراكمي"))
    with tabs[2]:
        be=breakeven_revenue(a)
        st.metric("معامل الإيراد اللازم لتحقيق NPV = 0",pct(be))
        sdf=sensitivity(a); st.line_chart(sdf)
        tor=pd.DataFrame({"NPV عند -20%":sdf.loc["-20%"],"NPV عند +20%":sdf.loc["+20%"]})
        tor["التأرجح"]=(tor.iloc[:,0]-tor.iloc[:,1]).abs()
        st.dataframe(tor.sort_values("التأرجح",ascending=False).style.format("{:,.0f}"))
        st.subheader("تحليل السيناريوهات")
        sc=editor(pd.DataFrame({"السيناريو":["متشائم","أساس","متفائل"],"الإيراد ×":[.8,1.,1.1],
            "التشغيل ×":[1.15,1.,.95],"CAPEX ×":[1.2,1.,.95],"معدل الخصم %":[r*100+3,r*100,r*100-1]}),"scenarios")
        rows=[]
        for _,x in sc.iterrows():
            z=run(a,rev=float(x.iloc[1]),opex=float(x.iloc[2]),capex=float(x.iloc[3]),r=float(x.iloc[4])/100)
            rows.append([x.iloc[0],z["npv"],z["irr"],z["bcr"]])
        st.dataframe(pd.DataFrame(rows,columns=["السيناريو","NPV","IRR","BCR"]),hide_index=True)
    with tabs[3]:
        st.caption("توزيع مثلثي: أدنى، أرجح، أعلى. أدخل القيم بمعاملات الضرب، ومعدل الخصم كنسبة عشرية.")
        mc=editor(pd.DataFrame({"الوسيط":["الإيراد ×","التشغيل ×","CAPEX ×","معدل الخصم"],
            "أدنى":[.7,.9,.95,max(0.,r-.02)],"الأرجح":[1.,1.,1.,r],"أعلى":[1.1,1.3,1.4,r+.04]}),"mc_inputs")
        n=st.select_slider("عدد التكرارات",[500,1000,2000,5000],value=1000)
        if st.button("تشغيل المحاكاة",key="run_mc"):
            try:
                params=[tuple(mc.iloc[i,1:4].astype(float)) for i in range(4)]
                if any(not (x[0]<=x[1]<=x[2]) for x in params): raise ValueError("يجب أن يكون الأدنى ≤ الأرجح ≤ الأعلى.")
                npvs,irrs=monte_carlo(a,n,*params)
                c=st.columns(4)
                c[0].metric("احتمال NPV موجب",pct((npvs>0).mean()))
                c[1].metric("P10",fmt(np.nanpercentile(npvs,10)))
                c[2].metric("P50",fmt(np.nanpercentile(npvs,50)))
                c[3].metric("P90",fmt(np.nanpercentile(npvs,90)))
                st.bar_chart(pd.Series(np.histogram(npvs,30)[0]))
            except Exception as exc: st.error(str(exc))
    with tabs[4]:
        st.caption("للمشاريع العامة: منافع اجتماعية وأسعار ظلّية، دون ضرائب أو تمويل.")
        ben=editor(tb["benefits"],f"benefits_{key}")
        c=st.columns(3)
        sc_c=c[0].number_input("عامل تحويل CAPEX",.3,1.5,.9)
        sc_o=c[1].number_input("عامل تحويل التشغيل",.3,1.5,.9)
        sr=c[2].number_input("معدل الخصم الاجتماعي (%)",1.,30.,8.)/100
        try:
            eco=economic(inp,ben,sc_c,sc_o,sr)
            c=st.columns(3)
            c[0].metric("ENPV",fmt(eco["npv"]))
            c[1].metric("EIRR",pct(eco["irr"]))
            c[2].metric("B/C اقتصادي",fmt(eco["bcr"]))
        except Exception as exc: st.error(f"تعذر تنفيذ التحليل الاقتصادي: {exc}")
    with tabs[5]:
        df=pd.DataFrame({"السنة":m["t"],"الإيراد":m["rev"],"المصروفات":m["opex"],"EBITDA":m["ebitda"],
            "الاندثار":m["dep"],"الضريبة":m["tax"],"CAPEX":m["capex"],"الإحلال":m["repl"],
            "ΔWC":m["dwc"],"القيمة النهائية":m["term"],"FCFF":m["fcff"],"القرض المسحوب":m["draw"],
            "الفائدة":m["interest"],"أصل القرض":m["principal"],"FCFE":m["fcfe"],"DSCR":m["dscr"]})
        st.dataframe(df.style.format("{:,.0f}",subset=df.columns[1:-1]).format("{:.2f}",subset=["DSCR"]),hide_index=True,use_container_width=True)
        st.download_button("تنزيل جدول التدفقات CSV",df.to_csv(index=False).encode("utf-8-sig"),"cashflow.csv","text/csv")
