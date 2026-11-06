# -*- coding: utf-8 -*-

import math
import os
import urllib.parse
from google import genai
import numpy_financial as npf
import pandas as pd
import streamlit as st

# إنشاء مجلدات الأمان والملفات الهندسية تلقائياً
os.makedirs(".streamlit", exist_ok=True)
os.makedirs("reference_files", exist_ok=True)

# ضبط مفتاح الـ API تلقائياً إذا لم يكن موجوداً
if not os.path.exists(".streamlit/secrets.toml"):
    with open(".streamlit/secrets.toml", "w", encoding="utf-8") as f:
        f.write(
            'GEMINI_API_KEY = "AQ.Ab8RN6Kfxk7xx1UDiZRuTshX9WhXsv9JInkFlyQJQp0LOn14gg"\n'
        )

# تعريف مجلد الملفات المرجعية
REFERENCE_FOLDER = "reference_files"


def get_reference_content():
    all_context = ""
    if os.path.exists(REFERENCE_FOLDER):
        for filename in os.listdir(REFERENCE_FOLDER):
            file_path = os.path.join(REFERENCE_FOLDER, filename)
            if filename.endswith(".xlsx"):
                df = pd.read_excel(file_path)
                all_context += f"\nمحتوى ملف إكسل {filename}:\n{df.to_string()}\n"
            elif filename.endswith(".csv"):
                df = pd.read_csv(file_path)
                all_context += f"\nمحتوى ملف CSV {filename}:\n{df.to_string()}\n"
    return all_context


# =====================================================
# 1. إعدادات الصفحة
# =====================================================
st.set_page_config(
    page_title="منصة إنشاءات للاستشارات الهندسية", layout="wide", page_icon="🏗️"
)

# إعداد الـ API
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
except Exception:
    st.warning("")

if "context_data" not in st.session_state:
    st.session_state.context_data = get_reference_content()
    if not st.session_state.context_data:
        st.session_state.context_data = (
            "لا توجد ملفات مرفوعة حالياً في مجلد reference_files."
        )

# =====================================================
# 2. القائمة الجانبية (Sidebar)
# =====================================================
with st.sidebar:
    st.title("🏛️  منصة إنشاءات للاستشارات الهندسية")
    st.markdown("---")
    choice = st.radio(
        "اختر القسم المطلوب:",
        [
            "دراسة الجدوى الاقتصادية",
            "تصميم محطة رفع ومعالجة مياه صرف",
        ],
    )
    st.markdown("---")
    st.info("تصميم المهندس الاستشاري عبد الغفور رمضان اللهيبي")

# =====================================================
# 3. قسم دراسة الجدوى الاقتصادية (المحرك الحسابي العام)
# =====================================================
if choice == "دراسة الجدوى الاقتصادية":
    st.header(
        "📈 محرك دراسة الجدوى الاقتصادية والتحليل المالي "
    )
    st.info(
        "قم بإدخال بيانات التكاليف والإيرادات أدناه لتطبيق المعادلات الحسابية واحتساب المؤشرات المالية بشكل تلقائي."
    )

    # حقل عرض المعادلات الرياضية والمالية لكل مرحلة
    with st.expander("📐 دليل المعادلات الرياضية والمالية المستخدمة في المراحل", expanded=False):
        st.markdown("""
        * **المرحلة 1: إجمالي التكاليف الاستثمارية (Total Investment)**  
          $$\\text{Total Investment} = \\text{Total Construction} + \\text{Land/Rent Cost} + \\text{Working Capital}$$
        * **المرحلة 2: صافي التدفق النقدي السنوي (Net Cash Flow - NCF)**  
          $$\\text{Annual NCF} = \\text{Annual Revenue} - \\text{Annual Expenses}$$
        * **المرحلة 3: فترة الاسترداد (Payback Period)**  
          $$\\text{Payback Period} = \\frac{\\text{Total Investment}}{\\text{Annual NCF}}$$
        * **المرحلة 4: نسبة العائد على الاستثمار (ROI)**  
          $$\\text{ROI} = \\left( \\frac{\\text{Annual NCF}}{\\text{Total Investment}} \\right) \\times 100$$
        * **المرحلة 5: صافي القيمة الحالية (Net Present Value - NPV)**  
          $$\\text{NPV} = \\sum_{t=1}^{n} \\frac{\\text{NCF}_t}{(1 + i)^t} - \\text{Total Investment}$$
        * **المرحلة 6: معدل العائد الداخلي (Internal Rate of Return - IRR)**  
          $$\\sum_{t=0}^{n} \\frac{\\text{NCF}_t}{(1 + \\text{IRR})^t} = 0$$
        """)

    with st.form("general_feasibility_form"):
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("🏗️ التكاليف الاستثمارية والرأسمالية")
            total_construction = st.number_input(
                "تكلفة إنشاء المشروع والاستثمار الأولي (د.ع)",
                min_value=0.0,
                value=100000000.0,
                step=1000000.0,
            )
            land_or_rent_cost = st.number_input(
                "تكلفة الأرض / الإيجار السنوي المتراكم (د.ع)",
                min_value=0.0,
                value=5000000.0,
                step=1000000.0,
            )
            working_capital = st.number_input(
                "رأس المال التشغيلي وتكاليف التأسيس (د.ع)",
                min_value=0.0,
                value=10000000.0,
                step=1000000.0,
            )

            st.markdown("---")
            st.subheader("📊 المعايير الزمنية والمالية")
            discount_rate = (
                st.number_input(
                    "معدل الخصم السنوي (%)",
                    min_value=0.0,
                    max_value=100.0,
                    value=10.0,
                    step=0.5,
                )
                / 100
            )
            project_years = st.number_input(
                "عمر المشروع الافتراضي (سنوات)", min_value=1, value=15
            )

        with col2:
            st.subheader("⚙️ الإيرادات والمصروفات التشغيلية السنوية")
            annual_revenue = st.number_input(
                "إجمالي الإيرادات السنوية المتوقعة (د.ع)",
                min_value=0.0,
                value=45000000.0,
                step=1000000.0,
            )
            annual_expenses = st.number_input(
                "إجمالي المصروفات التشغيلية السنوية (د.ع)",
                min_value=0.0,
                value=15000000.0,
                step=1000000.0,
            )
            salvage_value = st.number_input(
                "القيمة التخلصية/الدفترية نهاية المشروع (د.ع)",
                min_value=0.0,
                value=0.0,
                step=1000000.0,
            )

        calculate_btn = st.form_submit_button(
            "إجراء التحليل المالي وحساب المؤشرات"
        )

    if calculate_btn:
        # مرحلة 1: إجمالي الاستثمار الأولي
        total_investment = (
            total_construction + land_or_rent_cost + working_capital
        )

        # مرحلة 2: صافي التدفق النقدي السنوي
        annual_net_cash_flow = annual_revenue - annual_expenses

        # مصفوفة التدفقات النقدية عبر السنوات
        cash_flows = [-total_investment]
        for year in range(1, project_years + 1):
            if year == project_years:
                cash_flows.append(annual_net_cash_flow + salvage_value)
            else:
                cash_flows.append(annual_net_cash_flow)

        # مرحلة 5 & 6: NPV & IRR
        npv_value = npf.npv(discount_rate, cash_flows)
        try:
            irr_value = npf.irr(cash_flows) * 100
        except Exception:
            irr_value = 0.0

        # مرحلة 3 & 4: فترة الاسترداد و ROI
        payback_period = (
            total_investment / annual_net_cash_flow
            if annual_net_cash_flow > 0
            else 0
        )
        roi_value = (
            (annual_net_cash_flow / total_investment) * 100
            if total_investment > 0
            else 0
        )

        st.divider()
        st.subheader("📊 نتائج المؤشرات المالية والاستثمارية القياسية")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("إجمالي رأس المال الاستثماري", f"{total_investment:,.0f} د.ع")
        m2.metric(
            "صافي التدفق السنوي (NCF)", f"{annual_net_cash_flow:,.0f} د.ع"
        )
        m3.metric("فترة الاسترداد المبسطة", f"{payback_period:.2f} سنة")
        m4.metric("نسبة العائد على الاستثمار (ROI)", f"{roi_value:.2f}%")

        st.divider()
        st.subheader("🔍 التقييم الاقتصادي النهائي للمشروع")
        c1, c2 = st.columns(2)

        if npv_value > 0:
            c1.success(
                f"**صافي القيمة الحالية (NPV):** {npv_value:,.0f} د.ع  \n🟢 المشروع مربح ومجدٍ اقتصادياً بناءً على معدل الخصم المحدد."
            )
        else:
            c1.error(
                f"**صافي القيمة الحالية (NPV):** {npv_value:,.0f} د.ع  \n🔴 المشروع غير مجدٍ اقتصادياً عند معدل الخصم الحالي."
            )

        c2.info(f"**معدل العائد الداخلي (IRR):** {irr_value:.2f}%")

# =====================================================
# 4. قسم تصميم محطة رفع ومعالجة مياه صرف
# =====================================================
elif choice == "تصميم محطة رفع ومعالجة مياه صرف":
    st.header("🚰 تصميم حسابات محطات الرفع ومعالجة مياه الصرف الصحي")
    st.info(
        "قم بإدخال البيانات التصميمية الأساسية لحساب السعات الهيدروليكية وأبعاد أحواض المحطة."
    )

    with st.form("wwtp_design_form"):
        col_ww1, col_ww2 = st.columns(2)

        with col_ww1:
            st.subheader("👥 بيانات التدفق والسكان")
            population = st.number_input(
                "عدد السكان المستهدف (نسمة)",
                min_value=100,
                value=20000,
                step=100,
            )
            water_consumption = st.number_input(
                "معدل استهلاك المياه الفردي (لتر/فرد/يوم)",
                min_value=50,
                value=200,
                step=10,
            )
            peak_factor = st.number_input(
                "معامل الذروة (Peak Factor)",
                min_value=1.0,
                value=2.44,
                step=0.01,
            )
            V_velocity = st.number_input(
                "السرعة التصميمية في أنبوب الضخ (م/ث)",
                min_value=0.1,
                value=1.2,
                step=0.1,
            )

        with col_ww2:
            st.subheader("📐 محددات تصميم حوض الرفع والأحواض")
            retention_time = st.number_input(
                "زمن الاستبقاء الحرج (دقيقة)", min_value=5, value=30, step=5
            )
            well_depth = st.number_input(
                "العمق الفعال المقترح للحوض (متر)",
                min_value=1.0,
                value=5.0,
                step=0.5,
            )
            H_static = st.number_input(
                "المنسوب الرأسي الساكن H_static (متر)",
                min_value=0.0,
                value=10.0,
                step=0.5,
            )
            L_length = st.number_input(
                "طول خط الضخ L (متر)", min_value=0.0, value=1500.0, step=50.0
            )

        submit_wwtp = st.form_submit_button(
            "📐 إجراء الحسابات الهيدروليكية والتصميمية"
        )

    if submit_wwtp:
        wastewater_generation = 0.80
        avg_daily_flow_m3 = (
            population * water_consumption * wastewater_generation
        ) / 1000
        peak_flow_l_s = (
            (avg_daily_flow_m3) / 86400
        ) * peak_factor * 1000

        A_area = (peak_flow_l_s / 1000) / V_velocity
        D_calc = math.sqrt((4 * A_area) / math.pi) * 1000
        D_commercial = (
            450.0 if D_calc <= 450 else math.ceil(D_calc / 50) * 50
        )

        H_f = 2.78
        TDH = H_static + H_f

        eta = 0.70
        BHP = (peak_flow_l_s * TDH) / (75 * eta)

        V_primary = avg_daily_flow_m3 * 0.0833
        Area_primary = V_primary / 3.0
        D_primary_single = math.sqrt((4 * (Area_primary / 2)) / math.pi)

        q_ras = avg_daily_flow_m3 * 0.06 / 1000
        q_was = (avg_daily_flow_m3 * 0.015) / 86400

        st.success("🟢 تم احتساب المؤشرات الهيدروليكية والإنشائية للمحطة بنجاح:")
        st.divider()
        st.subheader("📊 الحسابات التلقائية لمحطة الرفع وخط الضخ")
        col_res1, col_res2, col_res3 = st.columns(3)

        with col_res1:
            st.metric(
                "التصريف اليومي المتوسط (Q_avg)",
                f"{avg_daily_flow_m3:,.2f} م3/يوم",
            )
            st.metric(
                "القطر الداخلي المحسوب (D_calc)", f"{D_calc:.2f} ملم"
            )

        with col_res2:
            st.metric(
                "التصريف الذروي اللحظي (Q_peak)",
                f"{peak_flow_l_s:.3f} لتر/ثانية",
            )
            st.metric(
                "القطر التجاري المعتمد (D_commercial)",
                f"{D_commercial:.0f} ملم",
            )

        with col_res3:
            st.metric(
                "الضاغط الديناميكي الكلي (TDH)", f"{TDH:.2f} متر"
            )
            st.metric(
                "القدرة المطلوبة للمضخة (BHP)", f"{BHP:.2f} حصان"
            )

        st.divider()
        st.subheader("🧱 الحسابات الإنشائية لأحواض المعالجة")
        col_res4, col_res5 = st.columns(2)

        with col_res4:
            st.markdown(
                f"**الحجم الكلي لأحواض الترسيب الابتدائية (V_primary):** {V_primary:.2f} م3"
            )
            st.markdown(
                f"**المساحة السطحية الكلية للترسيب:** {Area_primary:.2f} م2"
            )
            st.markdown(
                f"**قطر الحوض الواحد:** {D_primary_single:.2f} متر"
            )

        with col_res5:
            st.subheader("🔄 منظومة ضخ وتدوير الحمأة")
            st.write(
                f"**تدفق مضخات الحمأة المرتجعة ($RAS$):** {q_ras * 1000:.2f} لتر/ثانية"
            )
            st.write(
                f"**تدفق مضخات الحمأة الفائضة ($WAS$):** {q_was * 1000:.4f} لتر/ثانية"
            )