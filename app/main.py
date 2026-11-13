
# -*- coding: utf-8 -*-

import os
import math
import pandas as pd
import streamlit as st
import numpy_financial as npf

# =====================================================
# 1. إعدادات الصفحة الأساسية
# =====================================================

st.set_page_config(
    page_title="منصة إنشاءات للاستشارات الهندسية",
    layout="wide",
    page_icon="🏗️"
)

# =====================================================
# 2. التنسيقات والألوان CSS
# =====================================================

# =====================================================
# 2. تحميل التنسيقات من ملف style.css
# =====================================================

from pathlib import Path

CSS_FILE = Path(__file__).resolve().parent / "style.css"

if CSS_FILE.exists():

    css_content = CSS_FILE.read_text(encoding="utf-8")

    st.markdown(
        f"<style>{css_content}</style>",
        unsafe_allow_html=True
    )

else:
    st.error("لم يتم العثور على ملف style.css")


# =====================================================
# 3. إعداد الاتصال بالذكاء الاصطناعي Gemini
# =====================================================

# ملاحظة أمنية:
# ضع المفتاح في Streamlit Secrets أو متغيرات البيئة.
# لا تضع مفتاح API داخل ملف Python.

API_KEY = os.getenv("GEMINI_API_KEY", "")

try:
    API_KEY = st.secrets.get("GEMINI_API_KEY", API_KEY)
except Exception:
    pass

client = None

if API_KEY:
    try:
        from google import genai
        client = genai.Client(api_key=API_KEY)
    except Exception as e:
        st.sidebar.warning(
            "تعذر تهيئة اتصال Gemini: " + str(e)
        )
else:
    st.sidebar.caption(
        "اتصال Gemini غير مهيأ حالياً."
    )


# =====================================================
# 4. الملفات المرجعية الهندسية
# =====================================================

REFERENCE_FOLDER = "reference_files"


def get_reference_content():

    all_context = ""

    if not os.path.exists(REFERENCE_FOLDER):
        return all_context

    for filename in os.listdir(REFERENCE_FOLDER):

        file_path = os.path.join(
            REFERENCE_FOLDER,
            filename
        )

        try:

            if filename.lower().endswith(".xlsx"):
                df = pd.read_excel(file_path)

            elif filename.lower().endswith(".csv"):
                df = pd.read_csv(file_path)

            else:
                continue

            all_context += (
                f"\nمحتوى ملف {filename}:\n"
                f"{df.to_string(index=False)}\n"
            )

        except Exception as e:

            all_context += (
                f"\nتعذر قراءة الملف {filename}: {e}\n"
            )

    return all_context


# =====================================================
# 5. تخزين بيانات الجلسة
# =====================================================

if "context_data" not in st.session_state:
    st.session_state.context_data = (
        "لا توجد بيانات إضافية مرفوعة حالياً."
    )


# =====================================================
# 6. القائمة الجانبية
# =====================================================

with st.sidebar:

    st.title("🏛️ منصة إنشاءات للاستشارات الهندسية")

    st.markdown("---")

    choice = st.radio(
    "اختر القسم المطلوب:",
    [
        "دراسة الجدوى الاقتصادية",
        "تصميم محطة رفع ومعالجة مياه صرف"
    ],
    key="main_section"
)
    st.markdown("---")

    st.info(
        "تصميم المهندس الاستشاري عبد الغفور رمضان اللهيبي "
    )


# =====================================================
# 7. قسم دراسة الجدوى الاقتصادية
# =====================================================

if choice == "دراسة الجدوى الاقتصادية":

    st.header("📈 دراسة الجدوى والتدفقات النقدية")

    st.info(
        "أدخل بيانات المشروع للحصول على "
        "المؤشرات المالية الأساسية."
    )

    with st.form("advanced_feasibility_form"):

        col1, col2 = st.columns(2)

        # ---------------------------------------------
        # التكاليف الرأسمالية
        # ---------------------------------------------

        with col1:

            st.subheader("🏗️ التكاليف الرأسمالية")

            land_cost = st.number_input(
                "قيمة الأرض (د.ع)",
                min_value=0.0,
                value=0.0,
                step=1000000.0
            )

            total_construction = st.number_input(
                "كلفة إنشاء المشروع (د.ع)",
                min_value=35000000.0,
                value=35000000.0,
                step=1000000.0
            )

            annual_rent_amount = st.number_input(
                "مبلغ الإيجار السنوي للأرض إن وجد (د.ع)",
                min_value=0.0,
                value=0.0,
                step=2500000.0
            )

            other_initial_costs = st.number_input(
                "تكاليف التأسيس والتراخيص (د.ع)",
                min_value=0.0,
                value=0.0,
                step=1500000.0
            )

            st.markdown("---")

            st.subheader("📊 المؤشرات المالية المطلوبة")

            discount_rate = st.number_input(
                "معدل الخصم السنوي (%)",
                min_value=0.0,
                max_value=100.0,
                value=10.0,
                step=0.5
            ) / 100

        # ---------------------------------------------
        # الإيرادات والمصروفات
        # ---------------------------------------------

        with col2:

            st.subheader("⚙️ الإيرادات والمصروفات التشغيلية")

            project_years = st.number_input(
                "عمر المشروع الافتراضي (سنوات)",
                min_value=1,
                value=30,
                step=1
            )

            annual_expenses = st.number_input(
                "المصروفات السنوية التشغيلية (صيانة، ضرائب...)",
                min_value=10000000.0,
                value=10000000.0,
                step=500000.0
            )

            annual_revenue_est = st.number_input(
                "الإيراد السنوي المتوقع (د.ع)",
                min_value=20000000.0,
                value=20000000.0,
                step=500000.0
            )

            salvage_value = st.number_input(
                "القيمة الدفترية المتوقعة في نهاية المشروع (د.ع)",
                min_value=0.0,
                value=0.0,
                step=1000000.0
            )

        calculate_btn = st.form_submit_button(
            "تحليل التدفق النقدي والجدوى الاقتصادية"
        )

    # ---------------------------------------------
    # الحسابات المالية
    # ---------------------------------------------

    if calculate_btn:

        # الإيجار السنوي لا يضاف إلى الاستثمار الأولي.
        # يعامل كمصروف تشغيلي سنوي.

        total_investment = (
            total_construction
            + land_cost
            + other_initial_costs
        )

        annual_net_cash_flow = (
            annual_revenue_est
            - annual_expenses
            - annual_rent_amount
        )

        cash_flows = [-total_investment]

        for year in range(1, int(project_years) + 1):

            if year == project_years:

                cash_flows.append(
                    annual_net_cash_flow + salvage_value
                )

            else:

                cash_flows.append(
                    annual_net_cash_flow
                )

        # صافي القيمة الحالية NPV

        try:

            npv_value = float(
                npf.npv(discount_rate, cash_flows)
            )

        except Exception:

            npv_value = float("nan")

        # معدل العائد الداخلي IRR

        try:

            irr_value = float(
                npf.irr(cash_flows)
            ) * 100

            if not math.isfinite(irr_value):
                irr_value = None

        except Exception:

            irr_value = None

        # فترة الاسترداد البسيطة

        if annual_net_cash_flow > 0:

            payback_period = (
                total_investment / annual_net_cash_flow
            )

        else:

            payback_period = None

        # ---------------------------------------------
        # عرض النتائج
        # ---------------------------------------------

        st.divider()

        st.subheader(
            "📊 النتائج المالية للمؤشرات الحيوية"
        )

        m1, m2, m3 = st.columns(3)

        m1.metric(
            "إجمالي رأس المال المستثمر",
            f"{total_investment:,.0f} د.ع"
        )

        m2.metric(
            "صافي التدفق النقدي السنوي",
            f"{annual_net_cash_flow:,.0f} د.ع"
        )

        m3.metric(
            "فترة الاسترداد المبسطة",
            (
                f"{payback_period:.2f} سنة"
                if payback_period is not None
                else "غير متاحة"
            )
        )

        st.divider()

        st.subheader(
            "🔍 تقييم الجدوى الاستثمارية للمشروع"
        )

        c1, c2 = st.columns(2)

        with c1:

            if math.isfinite(npv_value):

                if npv_value > 0:

                    st.success(
                        f"صافي القيمة الحالية (NPV): "
                        f"{npv_value:,.0f} د.ع\n\n"
                        "🟢 المشروع مجدٍ وفق الافتراضات المدخلة."
                    )

                elif npv_value < 0:

                    st.error(
                        f"صافي القيمة الحالية (NPV): "
                        f"{npv_value:,.0f} د.ع\n\n"
                        "🔴 المشروع غير مجدٍ عند معدل الخصم الحالي."
                    )

                else:

                    st.warning(
                        f"صافي القيمة الحالية (NPV): "
                        f"{npv_value:,.0f} د.ع\n\n"
                        "المشروع عند نقطة التعادل الحالية."
                    )

            else:

                st.error(
                    "تعذر حساب صافي القيمة الحالية."
                )

        with c2:

            if irr_value is not None:

                st.info(
                    f"معدل العائد الداخلي (IRR): "
                    f"{irr_value:.2f}%"
                )

            else:

                st.warning(
                    "تعذر تحديد معدل العائد الداخلي "
                    "بصورة موثوقة للتدفقات المدخلة."
                )

        # ---------------------------------------------
        # جدول التدفقات النقدية
        # ---------------------------------------------

        st.divider()

        st.subheader("📋 جدول التدفقات النقدية السنوية")

        cash_flow_df = pd.DataFrame({
            "السنة": range(len(cash_flows)),
            "التدفق النقدي (د.ع)": cash_flows
        })

        st.dataframe(
            cash_flow_df,
            use_container_width=True,
            hide_index=True
        )

        st.caption(
            "ملاحظة: الحسابات تفترض ثبات الإيرادات "
            "والمصروفات سنوياً وعدم وجود تضخم أو تمويل "
            "بالقروض أو ضرائب إضافية غير مدخلة."
        )


# =====================================================
# 8. قسم تصميم محطة رفع ومعالجة مياه الصرف
# =====================================================

elif choice == "تصميم محطة رفع ومعالجة مياه صرف":

    st.header(
        "🚰 تصميم حسابات محطات الرفع ومعالجة مياه الصرف الصحي"
    )

    st.info(
        "قم بإدخال البيانات التصميمية الأساسية "
        "لحساب السعات الهيدروليكية وأبعاد أحواض المحطة."
    )

    with st.form("wwtp_design_form"):

        col_ww1, col_ww2 = st.columns(2)

        # ---------------------------------------------
        # بيانات السكان والتدفق
        # ---------------------------------------------

        with col_ww1:

            st.subheader("👥 بيانات التدفق والسكان")

            population = st.number_input(
                "عدد السكان المستهدف (نسمة)",
                min_value=100,
                value=20000,
                step=100
            )

            water_consumption = st.number_input(
                "معدل استهلاك المياه الفردي (لتر/فرد/يوم)",
                min_value=50,
                value=200,
                step=10
            )

            peak_factor = st.number_input(
                "معامل الذروة (Peak Factor)",
                min_value=1.0,
                value=2.44,
                step=0.01
            )

            V_velocity = st.number_input(
                "السرعة التصميمية في أنبوب الضخ (م/ث)",
                min_value=0.1,
                value=1.2,
                step=0.1
            )

        # ---------------------------------------------
        # محددات الأحواض وخط الضخ
        # ---------------------------------------------

        with col_ww2:

            st.subheader(
                "📐 محددات تصميم حوض الرفع والأحواض"
            )

            retention_time = st.number_input(
                "زمن الاستبقاء الحرج (دقيقة)",
                min_value=5,
                value=30,
                step=5
            )

            well_depth = st.number_input(
                "العمق الفعال المقترح للحوض (متر)",
                min_value=1.0,
                value=5.0,
                step=0.5
            )

            H_static = st.number_input(
                "المنسوب الرأسي الساكن H_static (متر)",
                min_value=0.0,
                value=10.0,
                step=0.5
            )

            L_length = st.number_input(
                "طول خط الضخ L (متر)",
                min_value=0.0,
                value=1500.0,
                step=50.0
            )

        submit_wwtp = st.form_submit_button(
            "📐 إجراء الحسابات الهيدروليكية والتصميمية"
        )

    # =================================================
    # 9. الحسابات الهيدروليكية
    # =================================================

    if submit_wwtp:

        try:

            # -----------------------------------------
            # معدل تولد مياه الصرف
            # -----------------------------------------

            wastewater_generation = 0.80

            avg_daily_flow_m3 = (
                population
                * water_consumption
                * wastewater_generation
            ) / 1000

            # متوسط التدفق بالثانية

            avg_flow_l_s = (
                avg_daily_flow_m3 * 1000
            ) / 86400

            # التدفق الذروي

            peak_flow_l_s = (
                avg_flow_l_s * peak_factor
            )

            peak_flow_m3_s = (
                peak_flow_l_s / 1000
            )

            # -----------------------------------------
            # مساحة المقطع وقطر الأنبوب
            # -----------------------------------------

            A_area = (
                peak_flow_m3_s / V_velocity
            )

            D_calc = (
                math.sqrt(4 * A_area / math.pi)
                * 1000
            )

            # أقطار تجارية افتراضية للاختيار الأولي.
            # يجب مطابقتها مع السوق والمواصفات المعتمدة.

            commercial_diameters = [
                100, 125, 150, 200, 250,
                300, 350, 400, 450, 500,
                600, 700, 800, 900, 1000,
                1200, 1400, 1600
            ]

            D_commercial = next(
                (
                    diameter
                    for diameter in commercial_diameters
                    if diameter >= D_calc
                ),
                None
            )

            # -----------------------------------------
            # الفواقد الهيدروليكية
            # Hazen-Williams
            # -----------------------------------------

            # معامل C الافتراضي لأنبوب ضغط جديد.
            # يجب تعديله وفق مادة الأنبوب وحالته.

            C_hazen = 140.0

            if D_commercial is not None:

                D_m = D_commercial / 1000

                # السرعة الفعلية داخل القطر التجاري

                actual_area = (
                    math.pi * D_m ** 2 / 4
                )

                actual_velocity = (
                    peak_flow_m3_s / actual_area
                )

                # فاقد الاحتكاك Hazen-Williams

                if L_length > 0 and peak_flow_m3_s > 0:

                    H_friction = (
                        10.67
                        * L_length
                        * (peak_flow_m3_s ** 1.852)
                        / (
                            (C_hazen ** 1.852)
                            * (D_m ** 4.871)
                        )
                    )

                else:

                    H_friction = 0.0

                # تقدير أولي للفواقد الثانوية
                # بنسبة 10% من فاقد الاحتكاك.
                # يجب استبدالها بحساب K الفعلي لاحقاً.

                H_minor = 0.10 * H_friction

                TDH = (
                    H_static
                    + H_friction
                    + H_minor
                )

            else:

                D_m = None
                actual_velocity = None
                H_friction = None
                H_minor = None
                TDH = None

            # -----------------------------------------
            # قدرة المضخة
            # -----------------------------------------

            eta = 0.70

            if TDH is not None:

                rho = 1000.0
                gravity = 9.81

                hydraulic_power_kw = (
                    rho
                    * gravity
                    * peak_flow_m3_s
                    * TDH
                ) / 1000

                required_power_kw = (
                    hydraulic_power_kw / eta
                )

                # التحويل إلى حصان

                BHP = (
                    required_power_kw / 0.7457
                )

            else:

                hydraulic_power_kw = None
                required_power_kw = None
                BHP = None

            # -----------------------------------------
            # حجم حوض الرفع
            # -----------------------------------------

            # تقدير حجم المياه وفق زمن الاستبقاء
            # ومتوسط التدفق اليومي.

            V_wet_well = (
                avg_daily_flow_m3
                * retention_time
                / 1440
            )

            A_wet_well = (
                V_wet_well / well_depth
            )

            # -----------------------------------------
            # أحواض الترسيب الابتدائية
            # -----------------------------------------

            # حجم افتراضي مبني على زمن مكوث ساعتين.
            # لا يغني عن التصميم وفق الحمل السطحي.

            primary_retention_hours = 2.0

            V_primary = (
                avg_daily_flow_m3
                * primary_retention_hours
                / 24
            )

            # عمق افتراضي للحوض 3 متر

            primary_depth = 3.0

            Area_primary = (
                V_primary / primary_depth
            )

            # عند اعتماد حوضين متساويين

            number_of_primary_tanks = 2

            Area_single_tank = (
                Area_primary / number_of_primary_tanks
            )

            D_primary_single = math.sqrt(
                4 * Area_single_tank / math.pi
            )

            # -----------------------------------------
            # تدفقات الحمأة RAS و WAS
            # -----------------------------------------

            # RAS = 6% من متوسط التدفق اليومي
            # افتراض أولي يحتاج إلى التحقق حسب نظام المعالجة.

            ras_percentage = 0.06

            q_ras_m3_day = (
                avg_daily_flow_m3 * ras_percentage
            )

            q_ras_l_s = (
                q_ras_m3_day * 1000 / 86400
            )

            # WAS = 1.5% من متوسط التدفق اليومي
            # افتراض أولي وليس قيمة تصميمية ثابتة.

            was_percentage = 0.015

            q_was_m3_day = (
                avg_daily_flow_m3 * was_percentage
            )

            q_was_l_s = (
                q_was_m3_day * 1000 / 86400
            )

            # =================================================
            # 10. عرض النتائج
            # =================================================

            st.success(
                "🟢 تم تنفيذ الحسابات الأولية بنجاح."
            )

            st.divider()

            st.subheader(
                "📊 الحسابات التلقائية لمحطة الرفع وخط الضخ"
            )

            col_res1, col_res2, col_res3 = st.columns(3)

            with col_res1:

                st.metric(
                    "التصريف اليومي المتوسط (Q_avg)",
                    f"{avg_daily_flow_m3:,.2f} م³/يوم"
                )

                st.metric(
                    "القطر الداخلي المحسوب (D_calc)",
                    f"{D_calc:.2f} ملم"
                )

            with col_res2:

                st.metric(
                    "التصريف الذروي (Q_peak)",
                    f"{peak_flow_l_s:.3f} لتر/ثانية"
                )

                st.metric(
                    "القطر التجاري الأولي",
                    (
                        f"{D_commercial:.0f} ملم"
                        if D_commercial is not None
                        else "غير متوفر"
                    )
                )

            with col_res3:

                st.metric(
                    "الضاغط الديناميكي الكلي (TDH)",
                    (
                        f"{TDH:.2f} متر"
                        if TDH is not None
                        else "غير محسوب"
                    )
                )

                st.metric(
                    "قدرة المضخة المطلوبة",
                    (
                        f"{BHP:.2f} حصان"
                        if BHP is not None
                        else "غير محسوبة"
                    )
                )

            # -----------------------------------------
            # تفاصيل الفواقد
            # -----------------------------------------

            st.divider()

            st.subheader(
                "🔧 تفاصيل الحسابات الهيدروليكية"
            )

            h1, h2, h3 = st.columns(3)

            with h1:

                st.metric(
                    "فاقد الاحتكاك",
                    (
                        f"{H_friction:.2f} متر"
                        if H_friction is not None
                        else "غير محسوب"
                    )
                )

            with h2:

                st.metric(
                    "الفواقد الثانوية التقديرية",
                    (
                        f"{H_minor:.2f} متر"
                        if H_minor is not None
                        else "غير محسوبة"
                    )
                )

            with h3:

                st.metric(
                    "السرعة الفعلية بالأنبوب",
                    (
                        f"{actual_velocity:.2f} م/ث"
                        if actual_velocity is not None
                        else "غير محسوبة"
                    )
                )

            # -----------------------------------------
            # حسابات حوض الرفع
            # -----------------------------------------

            st.divider()

            st.subheader(
                "🏗️ الحسابات الأولية لحوض الرفع"
            )

            w1, w2, w3 = st.columns(3)

            w1.metric(
                "حجم حوض الرفع",
                f"{V_wet_well:.2f} م³"
            )

            w2.metric(
                "مساحة الحوض",
                f"{A_wet_well:.2f} م²"
            )

            w3.metric(
                "العمق الفعال",
                f"{well_depth:.2f} متر"
            )

            # -----------------------------------------
            # أحواض المعالجة
            # -----------------------------------------

            st.divider()

            st.subheader(
                "🧱 الحسابات الأولية لأحواض الترسيب الابتدائية"
            )

            col_res4, col_res5 = st.columns(2)

            with col_res4:

                st.write(
                    f"**الحجم الكلي للأحواض "
                    f"(V_primary):** {V_primary:.2f} م³"
                )

                st.write(
                    f"**المساحة السطحية الكلية:** "
                    f"{Area_primary:.2f} م²"
                )

                st.write(
                    f"**مساحة الحوض الواحد:** "
                    f"{Area_single_tank:.2f} م²"
                )

                st.write(
                    f"**قطر الحوض الواحد عند اعتماد حوضين:** "
                    f"{D_primary_single:.2f} متر"
                )

            with col_res5:

                st.subheader(
                    "🔄 منظومة ضخ وتدوير الحمأة (Sludge Pumps)"
                )

                st.write(
                    f"**تدفق الحمأة المرتجعة (RAS):** "
                    f"{q_ras_l_s:.3f} لتر/ثانية"
                )

                st.write(
                    f"**تدفق الحمأة الفائضة (WAS):** "
                    f"{q_was_l_s:.4f} لتر/ثانية"
                )

            # -----------------------------------------
            # تنبيهات التصميم
            # -----------------------------------------

            st.divider()

            st.subheader(
                "⚠️ ملاحظات هندسية مهمة"
            )

            st.warning("""
            النتائج أعلاه حسابات أولية وليست تصميماً تنفيذياً معتمداً.

            1. يجب التحقق من معامل الذروة وفق عدد السكان وطبيعة شبكة الصرف.
            2. يجب اعتماد أقطار الأنابيب التجارية المتوفرة فعلياً ومراجعة السرعة.
            3. فاقد الاحتكاك محسوب بمعادلة Hazen-Williams وبمعامل C افتراضي 140.
            4. الفواقد الثانوية مقدرة بنسبة 10%، ويجب حسابها من معاملات K الفعلية.
            5. قدرة المضخة لا تغني عن اختيار منحنى المضخة ومراجعة نقطة التشغيل.
            6. حجم حوض الرفع يحتاج إلى مراجعة عدد مرات تشغيل المضخات وزمن الدورة.
            7. أحواض الترسيب تحتاج إلى مراجعة معدل التحميل السطحي وزمن المكوث
               والحمل الهيدروليكي والحمل الصلب.
            8. نسب RAS وWAS افتراضات أولية يجب تحديدها وفق عملية المعالجة
               وتركيز المواد الصلبة وعمر الحمأة.
            """)

        except Exception as e:

            st.error(
                f"حدث خطأ أثناء إجراء الحسابات: {str(e)}"
            )
