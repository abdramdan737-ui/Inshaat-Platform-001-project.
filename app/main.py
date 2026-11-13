

# -*- coding: utf-8 -*-

import streamlit as st
import os
import pandas as pd
from google import genai
import numpy_financial as npf
import urllib.parse
import math

# 1. إعدادات الصفحة الأساسية
st.set_page_config(
    page_title="منصة إنشاءات للاستشارات الهندسية",
    layout="wide",
    page_icon="🏗️"
)

# =====================================================
# 🎨 ضع كود الألوان والتنسيقات (CSS) هنا مباشرة
# =====================================================
st.markdown("""
<style>
    /* 1. تغيير لون خلفية الصفحة بالكامل إلى أزرق فاتح خفيف */
    .stApp {
        background-color: #F0F4F8;
    }
    
    /* 2. تخصيص لون العناوين والنصوص والبيانات باللون الأزرق الداكن الواضح */
    h1, h2, h3, h4, h5, h6, p, span, label {
        color: #1E3A8A !important;
    }

    /* 3. تخصيص مظهر الأزرار لتكون بارزة وملونة باللون الأزرق المتناسق */
    .stButton>button {
        background-color: #1E3A8A;
        color: white;
        border-radius: 12px;
        border: 2px
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# =====================================================
# 2. بقية إعدادات الاتصال والـ API...
# إنشاء مجلد secrets تلقائياً إذا لم يكن موجوداً
os.makedirs(".streamlit", exist_ok=True)
if not os.path.exists(".streamlit/secrets.toml"):
    with open(".streamlit/secrets.toml", "w", encoding="utf-8") as f:
        f.write('GEMINI_API_KEY = "AQ.Ab8RN6Kfxk7xx1UDiZRuTshX9WhXsv9JInkFlyQJQp0LOn14gg"\n')

# =====================================================
# 1. إعدادات الصفحة والذكاء الاصطناعي
# =====================================================
st.set_page_config(
    page_title="منصة إنشاءات للاستشارات الهندسية",
    layout="wide",
    page_icon="🏗️"
)

# إعداد الـ API بأمان من خلال Streamlit Secrets أو القيمة الافتراضية
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    API_KEY = "AQ.Ab8RN6Kfxk7xx1UDiZRuTshX9WhXsv9JInkFlyQJQp0LOn14gg"

# تهيئة عميل جوجل الذكي بالطريقة الحديثة
client = genai.Client(api_key=API_KEY)

# تعريف المجلد الذي يحتوي على الملفات الهندسية
REFERENCE_FOLDER = "reference_files"

def get_reference_content():
    all_context = ""
    if os.path.exists(REFERENCE_FOLDER):
        for filename in os.listdir(REFERENCE_FOLDER):
            if filename.endswith(".xlsx") or filename.endswith(".csv"):
                file_path = os.path.join(REFERENCE_FOLDER, filename)
                df = pd.read_excel(file_path) if filename.endswith(".xlsx") else pd.read_csv(file_path)
                all_context += f"\nمحتوى ملف {filename}:\n{df.to_string()}\n"
    return all_context

# تخزين البيانات في الجلسة
if 'context_data' not in st.session_state:
    st.session_state.context_data = "لا توجد بيانات إضافية مرفوعة حالياً."

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
    st.info("تصميم المهندس الاستشاري عبد الغفور رمضان اللهيبي")

# =====================================================
# 2. قسم دراسة الجدوى الاقتصادية
# =====================================================
if choice == "دراسة الجدوى الاقتصادية":
    st.header("📈 دراسة الجدوى والتدفقات النقدية ")
    
    with st.form("advanced_feasibility_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🏗️ التكاليف الرأسمالية ")
            land_cost = st.number_input("قيمة الأرض (د.ع)", min_value=0.0, step=1000000.0)
            total_construction = st.number_input("كلفة إنشاء المشروع (د.ع)", min_value=35000000.0, step=1000000.0)
            annual_rent_amount = st.number_input("مبلغ الإيجار السنوي للأرض إن وجد (د.ع)", min_value=0.0, step=2500000.0)
            other_initial_costs = st.number_input("تكاليف التأسيس والتراخيص (د.ع)", min_value=0.0, step=1500000.0)
            
            st.markdown("---")
            st.subheader("📊 المؤشرات المالية المطلوبة")
            discount_rate = st.number_input("معدل الخصم السنوي (%)", min_value=0.0, max_value=100.0, value=10.0, step=0.5) / 100

        with col2:
            st.subheader("⚙️ الإيرادات والمصروفات التشغيلية")
            project_years = st.number_input("عمر المشروع الافتراضي (سنوات)", min_value=1, value=30)
            annual_expenses = st.number_input("المصروفات السنوية التشغيلية (صيانة، ضرائب...)", min_value=10000000.0, step=500000.0)
            annual_revenue_est = st.number_input("الإيراد السنوي المتوقع (د.ع)", min_value=20000000.0, step=500000.0)
            salvage_value = st.number_input("القيمة الدفترية المتوقعة في نهاية المشروع (د.ع)", min_value=0.0, step=1000000.0)

        calculate_btn = st.form_submit_button("تحليل التدفق النقدي والجدوى الاقتصادية")

    if calculate_btn:
        total_investment = total_construction + annual_rent_amount + land_cost + other_initial_costs
        annual_net_cash_flow = annual_revenue_est - annual_expenses
        cash_flows = [-total_investment] 
        
        for year in range(1, project_years + 1):
            if year == project_years:
                cash_flows.append(annual_net_cash_flow + salvage_value)
            else:
                cash_flows.append(annual_net_cash_flow)
        
        npv_value = npf.npv(discount_rate, cash_flows)
        
        try:
            irr_value = npf.irr(cash_flows) * 100
        except:
            irr_value = 0.0
            
        payback_period = total_investment / annual_net_cash_flow if annual_net_cash_flow > 0 else 0

        st.divider()
        st.subheader("📊 النتائج المالية للمؤشرات الحيوية")
        
        m1, m2, m3 = st.columns(3)
        m1.metric("إجمالي رأس المال المستثمر", f"{total_investment:,.0f} د.ع")
        m2.metric("صافي الربح السنوي التشغيلي", f"{annual_net_cash_flow:,.0f} د.ع")
        m3.metric("فترة الاسترداد المبسطة", f"{payback_period:.1f} سنة")
        
        st.divider()
        st.subheader("🔍 تقييم الجدوى الاستثمارية للمشروع")
        c1, c2 = st.columns(2)
        
        if npv_value > 0:
            c1.success(f"**صافي القيمة الحالية (NPV):** {npv_value:,.0f} د.ع  \n🟢 المشروع مجدٍ اقتصادياً.")
        else:
            c1.error(f"**صافي القيمة الحالية (NPV):** {npv_value:,.0f} د.ع  \n🔴 المشروع غير مجدٍ عند سعر الخصم الحالي.")
            
        c2.info(f"**معدل العائد الداخلي (IRR):** {irr_value:.2f}%")

# =====================================================
# 3. قسم تصميم محطة رفع ومعالجة مياه صرف
# =====================================================
elif choice == "تصميم محطة رفع ومعالجة مياه صرف":
    st.header("🚰 تصميم حسابات محطات الرفع ومعالجة مياه الصرف الصحي")
    st.info("قم بإدخال البيانات التصميمية الأساسية لحساب السعات الهيدروليكية وأبعاد أحواض المحطة.")
    
    with st.form("wwtp_design_form"):
        col_ww1, col_ww2 = st.columns(2)
        
        with col_ww1:
            st.subheader("👥 بيانات التدفق والسكان")
            population = st.number_input("عدد السكان المستهدف (نسمة)", min_value=100, value=20000, step=100)
            water_consumption = st.number_input("معدل استهلاك المياه الفردي (لتر/فرد/يوم)", min_value=50, value=200, step=10)
            peak_factor = st.number_input("معامل الذروة (Peak Factor)", min_value=1.0, value=2.44, step=0.01)
            V_velocity = st.number_input("السرعة التصميمية في أنبوب الضخ (م/ث)", min_value=0.1, value=1.2, step=0.1)
            
        with col_ww2:
            st.subheader("📐 محددات تصميم حوض الرفع والأحواض")
            retention_time = st.number_input("زمن الاستبقاء الحرج (دقيقة)", min_value=5, value=30, step=5)
            well_depth = st.number_input("العمق الفعال المقترح للحوض (متر)", min_value=1.0, value=5.0, step=0.5)
            H_static = st.number_input("المنسوب الرأسي الساكن H_static (متر)", min_value=0.0, value=10.0, step=0.5)
            L_length = st.number_input("طول خط الضخ L (متر)", min_value=0.0, value=1500.0, step=50.0)
            
        submit_wwtp = st.form_submit_button("📐 إجراء الحسابات الهيدروليكية والتصميمية")
        
    if submit_wwtp:
        wastewater_generation = 0.80 
        avg_daily_flow_m3 = (population * water_consumption * wastewater_generation) / 1000
        peak_flow_l_s = ((avg_daily_flow_m3) / 86400) * peak_factor * 1000
        
        A_area = (peak_flow_l_s / 1000) / V_velocity
        D_calc = math.sqrt((4 * A_area) / math.pi) * 1000
        D_commercial = 450.0 if D_calc <= 450 else math.ceil(D_calc / 50) * 50
        
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
            st.metric("التصريف اليومي المتوسط المستقبلي (Q_avg)", f"{avg_daily_flow_m3:,.2f} م3/يوم")
            st.metric("القطر الداخلي المحسوب (D_calc)", f"{D_calc:.2f} ملم")
            
        with col_res2:
            st.metric("التصريف الذروي اللحظي (Q_peak)", f"{peak_flow_l_s:.3f} لتر/ثانية")
            st.metric("القطر التجاري المعتمد (D_commercial)", f"{D_commercial:.0f} ملم")
            
        with col_res3:
            st.metric("الضاغط الديناميكي الكلي (TDH)", f"{TDH:.2f} متر")
            st.metric("القدرة المطلوبة للمضخة (BHP)", f"{BHP:.2f} حصان")

        st.divider()
        st.subheader("🧱 الحسابات الإنشائية التلقائية لأحواض المعالجة")
        col_res4, col_res5 = st.columns(2)
        
        with col_res4:
            st.markdown(f"**الحجم الكلي لأحواض الترسيب الابتدائية (V_primary):** {V_primary:.2f} م3")
            st.markdown(f"**المساحة السطحية الكلية للترسيب:** {Area_primary:.2f} م2")
            st.markdown(f"**قطر الحوض الواحد (عند اختيار حوضين):** {D_primary_single:.2f} متر")
            
        with col_res5:
            st.subheader("🔄 منظومة ضخ وتدوير الحمأة (Sludge Pumps)")
            st.write(f"**تدفق مضخات الحمأة المرتجعة (RAS):** {q_ras * 1000:.2f} لتر/ثانية")
            st.write(f"**تدفق مضخات الحمأة الفائضة (WAS):** {q_was * 1000:.4f} لتر/ثانية")
