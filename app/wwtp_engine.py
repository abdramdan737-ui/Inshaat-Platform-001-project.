# -*- coding: utf-8 -*-
"""محرك تصميم محطة رفع ومعالجة مياه الصرف (أولي/مفاهيمي).
التوسعة: أضف وسيطاً إلى PARAMS، أو وحدة جديدة كدالة (p, ctx) -> dict(d=, rows=, checks=) وسجّلها في UNITS."""
import math
import numpy as np

G, NU = 9.81, 1.0e-6
DN = [100, 150, 200, 250, 300, 350, 400, 450, 500, 600, 700, 800, 900, 1000, 1200, 1400]
MOTORS = [1.5, 2.2, 3, 4, 5.5, 7.5, 11, 15, 18.5, 22, 30, 37, 45, 55, 75, 90, 110, 132, 160, 200, 250, 315, 355, 400, 450, 500]
PEAK_METHODS = ["Harmon", "Babbitt", "يدوي"]
HYD_METHODS = ["Hazen-Williams", "Darcy-Weisbach"]

# (المجموعة, المفتاح, الوصف, الافتراضي, الحد الأدنى, الخطوة)
PARAMS = [
    ("1) السكان والتدفق", "pop", "السكان في سنة التصميم (نسمة)", 23000.0, 100.0, 100.0),
    ("1) السكان والتدفق", "lpcd", "استهلاك المياه (لتر/فرد/يوم)", 200.0, 50.0, 10.0),
    ("1) السكان والتدفق", "ret_frac", "نسبة تحويل الاستهلاك إلى صرف", 0.80, 0.30, 0.05),
    ("1) السكان والتدفق", "infil", "تسرب/دخيل % من Q_avg", 0.0, 0.0, 5.0),
    ("1) السكان والتدفق", "pf_manual", "معامل الذروة اليدوي", 2.44, 1.0, 0.01),
    ("1) السكان والتدفق", "qmin_ratio", "Q_min/Q_avg (0 = بالمعادلة)", 0.0, 0.0, 0.05),
    ("2) الأحمال الملوِّثة", "bod_pc", "BOD5 (غم/فرد/يوم)", 60.0, 20.0, 5.0),
    ("2) الأحمال الملوِّثة", "tss_pc", "TSS (غم/فرد/يوم)", 70.0, 20.0, 5.0),
    ("3) خط الضخ والمضخات", "v_des", "السرعة التصميمية (م/ث)", 1.2, 0.1, 0.1),
    ("3) خط الضخ والمضخات", "v_min", "أدنى سرعة مقبولة (م/ث)", 0.6, 0.1, 0.1),
    ("3) خط الضخ والمضخات", "v_max", "أعلى سرعة مقبولة (م/ث)", 2.5, 0.5, 0.1),
    ("3) خط الضخ والمضخات", "L", "طول خط الضخ L (م)", 1500.0, 1.0, 50.0),
    ("3) خط الضخ والمضخات", "H_static", "الضاغط الساكن (م)", 10.0, 0.0, 0.5),
    ("3) خط الضخ والمضخات", "h_res", "ضاغط متبقٍ عند التفريغ (م)", 0.0, 0.0, 0.5),
    ("3) خط الضخ والمضخات", "C", "معامل Hazen-Williams", 120.0, 60.0, 5.0),
    ("3) خط الضخ والمضخات", "eps_mm", "خشونة Darcy ε (ملم)", 0.1, 0.001, 0.01),
    ("3) خط الضخ والمضخات", "dn_override", "DN مفروض (0 = تلقائي)", 0.0, 0.0, 50.0),
    ("3) خط الضخ والمضخات", "n_duty", "عدد المضخات العاملة", 1.0, 1.0, 1.0),
    ("3) خط الضخ والمضخات", "n_standby", "عدد المضخات الاحتياطية", 1.0, 0.0, 1.0),
    ("3) خط الضخ والمضخات", "eta_p", "كفاءة المضخة", 0.70, 0.30, 0.05),
    ("3) خط الضخ والمضخات", "eta_m", "كفاءة المحرك", 0.92, 0.50, 0.01),
    ("3) خط الضخ والمضخات", "sf", "معامل خدمة المحرك", 1.15, 1.0, 0.05),
    ("4) بئر الرفع", "t_cycle", "أدنى زمن دورة تشغيل (دقيقة)", 10.0, 2.0, 1.0),
    ("4) بئر الرفع", "h_eff", "فرق منسوبي التشغيل والإيقاف (م)", 1.2, 0.3, 0.1),
    ("4) بئر الرفع", "ret_max", "أقصى زمن استبقاء عند Q_min (دقيقة)", 30.0, 5.0, 5.0),
    ("4) بئر الرفع", "starts_max", "أقصى عدد بدايات/ساعة/مضخة", 6.0, 1.0, 1.0),
    ("5) الترسيب الابتدائي", "hrt_p", "زمن الاستبقاء عند Q_avg (ساعة)", 2.0, 0.5, 0.25),
    ("5) الترسيب الابتدائي", "depth_p", "العمق الجانبي (م)", 3.0, 1.5, 0.5),
    ("5) الترسيب الابتدائي", "n_p", "عدد الأحواض", 2.0, 1.0, 1.0),
    ("5) الترسيب الابتدائي", "bod_rem_p", "إزالة BOD ابتدائياً %", 30.0, 0.0, 5.0),
    ("5) الترسيب الابتدائي", "tss_rem_p", "إزالة TSS ابتدائياً %", 60.0, 0.0, 5.0),
    ("6) الحمأة المنشّطة والترسيب الثانوي", "theta_c", "عمر الحمأة SRT (يوم)", 8.0, 2.0, 1.0),
    ("6) الحمأة المنشّطة والترسيب الثانوي", "Y", "معامل الإنتاج Y (kgVSS/kgBOD)", 0.6, 0.2, 0.05),
    ("6) الحمأة المنشّطة والترسيب الثانوي", "kd", "معامل التحلل الذاتي kd (1/يوم)", 0.06, 0.01, 0.01),
    ("6) الحمأة المنشّطة والترسيب الثانوي", "mlss", "MLSS (ملغم/لتر)", 3000.0, 1000.0, 250.0),
    ("6) الحمأة المنشّطة والترسيب الثانوي", "vss_ratio", "نسبة VSS/MLSS", 0.75, 0.5, 0.05),
    ("6) الحمأة المنشّطة والترسيب الثانوي", "svi", "SVI (مل/غم)", 120.0, 50.0, 10.0),
    ("6) الحمأة المنشّطة والترسيب الثانوي", "xr_f", "Xr كنسبة من 10⁶/SVI", 0.8, 0.5, 0.05),
    ("6) الحمأة المنشّطة والترسيب الثانوي", "s_eff", "BOD5 الذائب في المخرج (ملغم/لتر)", 20.0, 1.0, 1.0),
    ("6) الحمأة المنشّطة والترسيب الثانوي", "bod_bodu", "نسبة BOD5/BODu", 0.68, 0.5, 0.01),
    ("6) الحمأة المنشّطة والترسيب الثانوي", "sor_s", "SOR تصميمي للثانوي عند Q_avg (م/يوم)", 20.0, 5.0, 1.0),
    ("6) الحمأة المنشّطة والترسيب الثانوي", "depth_s", "عمق الثانوي (م)", 4.0, 2.5, 0.5),
    ("6) الحمأة المنشّطة والترسيب الثانوي", "n_s", "عدد أحواض الثانوي", 2.0, 1.0, 1.0),
]
DEFAULTS = {k: d for _, k, _, d, _, _ in PARAMS}
DEFAULTS.update(peak_method="Harmon", hyd="Hazen-Williams", K_sum=4.6)


def chk(name, val, lo=None, hi=None, unit=""):
    ok = bool(np.isfinite(val)) and (lo is None or val >= lo) and (hi is None or val <= hi)
    rng = f"{lo:g}–{hi:g}" if lo is not None and hi is not None else (f"≤ {hi:g}" if hi is not None else f"≥ {lo:g}")
    return (name, val, f"{rng} {unit}".strip(), ok)


def head_loss(p, Q, D):
    """فقد احتكاكي (م) لتدفق Q (م³/ث) وقطر داخلي D (م)."""
    if Q <= 0:
        return 0.0
    if p["hyd"] == "Hazen-Williams":
        return 10.67 * p["L"] * Q ** 1.852 / (p["C"] ** 1.852 * D ** 4.87)
    v = Q / (math.pi * D * D / 4)
    f = 0.25 / math.log10(p["eps_mm"] / 1000 / (3.7 * D) + 5.74 / (v * D / NU) ** 0.9) ** 2   # Swamee-Jain
    return f * p["L"] / D * v * v / (2 * G)


def system_head(p, Q, D):
    v = Q / (math.pi * D * D / 4)
    return p["H_static"] + head_loss(p, Q, D) + p["K_sum"] * v * v / (2 * G) + p["h_res"]


# ---------------------------------------------------------------- الوحدات
def u_flows(p, ctx):
    P = p["pop"]; Pk = P / 1000
    q_avg = P * p["lpcd"] * p["ret_frac"] / 1000 * (1 + p["infil"] / 100)
    pf = {"Harmon": 1 + 14 / (4 + math.sqrt(Pk)), "Babbitt": 5 / Pk ** 0.2, "يدوي": p["pf_manual"]}[p["peak_method"]]
    qr = p["qmin_ratio"] if p["qmin_ratio"] > 0 else 0.2 * Pk ** (1 / 6)
    bod_kg, tss_kg = P * p["bod_pc"] / 1000, P * p["tss_pc"] / 1000
    d = dict(q_avg=q_avg, pf=pf, q_peak=q_avg * pf, q_min=q_avg * qr, qr=qr, bod_kg=bod_kg, tss_kg=tss_kg,
             bod_mg=bod_kg / q_avg * 1000, tss_mg=tss_kg / q_avg * 1000)
    rows = [("Q_avg", q_avg, "م³/يوم"), ("Q_avg", q_avg / 86.4, "لتر/ث"), ("معامل الذروة", pf, "-"),
            ("Q_peak", d["q_peak"] / 86.4, "لتر/ث"), ("Q_min/Q_avg", qr, "-"), ("Q_min", d["q_min"] / 86.4, "لتر/ث"),
            ("حمل BOD5", bod_kg, "كغم/يوم"), ("تركيز BOD5 الداخل", d["bod_mg"], "ملغم/لتر"),
            ("حمل TSS", tss_kg, "كغم/يوم"), ("تركيز TSS الداخل", d["tss_mg"], "ملغم/لتر")]
    return dict(d=d, rows=rows, checks=[chk("معامل الذروة", pf, 1.5, 4.5)])


def u_pump(p, ctx):
    f = ctx["flows"]["d"]; Qp = f["q_peak"] / 86400
    n, ns = max(int(p["n_duty"]), 1), int(p["n_standby"])
    Dc = math.sqrt(4 * Qp / (math.pi * p["v_des"])) * 1000
    dn = int(p["dn_override"]) if p["dn_override"] > 0 else next((x for x in DN if x >= Dc), DN[-1])
    D = dn / 1000; A = math.pi * D * D / 4; v = Qp / A
    hf, hm = head_loss(p, Qp, D), p["K_sum"] * v * v / (2 * G)
    H = p["H_static"] + hf + hm + p["h_res"]
    Ph = G * Qp * H                      # kW (ρ = 1000 كغم/م³)
    Ps = Ph / p["eta_p"]; Pi = Ps / n    # لكل مضخة عاملة
    req = Pi * p["sf"]; motor = next((m for m in MOTORS if m >= req), None)
    qs = np.linspace(0, 1.25 * Qp, 26)
    curve = {"Q (لتر/ث)": qs * 1000, "منحنى النظام": [system_head(p, q, D) for q in qs]}
    if p["hyd"] == "Hazen-Williams":
        for c in (100, 140):
            curve[f"C={c}"] = [system_head(dict(p, C=c), q, D) for q in qs]
    d = dict(Qp=Qp, dn=dn, D_calc=Dc, v=v, H=H, hf=hf, hm=hm, Ps=Ps, Pi=Pi, motor=motor, curve=curve, n=n, ns=ns)
    rows = [("Q_peak (التصميم)", Qp * 1000, "لتر/ث"), ("D محسوب", Dc, "ملم"), ("DN المعتمد", dn, "ملم"),
            ("السرعة عند Q_peak", v, "م/ث"), ("الفقد الاحتكاكي", hf, "م"), ("الفقد الموضعي", hm, "م"),
            ("TDH", H, "م"), ("تدفق المضخة الواحدة", Qp * 1000 / n, "لتر/ث"), ("القدرة الهيدروليكية", Ph, "kW"),
            ("قدرة العمود الكلية", Ps, "kW"), ("قدرة العمود/مضخة", Pi, "kW"),
            ("قدرة المحرك المطلوبة (×SF)", req, "kW"), ("المحرك القياسي", motor if motor else "> 500", "kW"),
            ("المضخات المركبة (عاملة+احتياطية)", f"{n}+{ns}", "-")]
    checks = [chk("سرعة خط الضخ عند Q_peak", v, p["v_min"], p["v_max"], "م/ث")]
    if n > 1:
        checks.append(chk("السرعة بمضخة واحدة", Qp / n / A, p["v_min"], None, "م/ث"))
    return dict(d=d, rows=rows, checks=checks)


def u_well(p, ctx):
    f, pm = ctx["flows"]["d"], ctx["pump"]["d"]
    Qi = pm["Qp"] / pm["n"]                      # م³/ث لمضخة
    V = Qi * 60 * p["t_cycle"] / 4               # م³ (V = Q·T/4)
    Aw = V / p["h_eff"]; Dw = math.sqrt(4 * Aw / math.pi)
    qmin = f["q_min"] / 86400
    ret_min, ret_avg = V / (f["q_min"] / 1440), V / (f["q_avg"] / 1440)
    cyc = V / (Qi - qmin) + V / qmin if Qi > qmin else float("nan")
    cyc = cyc / 60
    starts = 60 / p["t_cycle"] / max(pm["n"] + pm["ns"], 1)
    rows = [("الحجم الفعال بين التشغيل والإيقاف", V, "م³"), ("المساحة السطحية", Aw, "م²"),
            ("القطر الدائري المكافئ", Dw, "م"), ("زمن الاستبقاء عند Q_avg", ret_avg, "دقيقة"),
            ("زمن الاستبقاء عند Q_min", ret_min, "دقيقة"), ("زمن الدورة عند Q_min", cyc, "دقيقة"),
            ("بدايات/ساعة/مضخة (أسوأ حالة)", starts, "-")]
    checks = [chk("زمن الاستبقاء عند Q_min", ret_min, None, p["ret_max"], "دقيقة"),
              chk("بدايات/ساعة/مضخة", starts, None, p["starts_max"])]
    return dict(d=dict(V=V, A=Aw, D=Dw), rows=rows, checks=checks)


def u_primary(p, ctx):
    f = ctx["flows"]["d"]; Q, Qp, n = f["q_avg"], f["q_peak"], max(int(p["n_p"]), 1)
    V = Q * p["hrt_p"] / 24; A = V / p["depth_p"]; D1 = math.sqrt(4 * A / n / math.pi)
    sor, sorp, weir = Q / A, Qp / A, Q / n / (math.pi * D1)
    sl = f["tss_kg"] * p["tss_rem_p"] / 100
    d = dict(V=V, A=A, D1=D1, bod_mg=f["bod_mg"] * (1 - p["bod_rem_p"] / 100), sludge_kg=sl)
    rows = [("الحجم الكلي", V, "م³"), ("المساحة السطحية الكلية", A, "م²"), ("قطر الحوض الواحد", D1, "م"),
            ("SOR عند Q_avg", sor, "م³/م²·يوم"), ("SOR عند Q_peak", sorp, "م³/م²·يوم"),
            ("حمل الهدّار", weir, "م³/م·يوم"), ("BOD5 بعد الترسيب", d["bod_mg"], "ملغم/لتر"),
            ("حمأة ابتدائية جافة", sl, "كغم/يوم"), ("حجم الحمأة (4% جاف)", sl / 41.2, "م³/يوم")]
    checks = [chk("SOR عند Q_avg", sor, 30, 50), chk("SOR عند Q_peak", sorp, None, 120), chk("زمن الاستبقاء", p["hrt_p"], 1.5, 2.5, "ساعة"),
              chk("العمق الجانبي", p["depth_p"], 3, 4.9, "م"), chk("حمل الهدّار", weir, 125, 500)]
    return dict(d=d, rows=rows, checks=checks)


def u_bio(p, ctx):
    f, S0 = ctx["flows"]["d"], ctx["primary"]["d"]["bod_mg"]
    Q, th, X = f["q_avg"], p["theta_c"], p["mlss"] * p["vss_ratio"]
    dS = S0 - p["s_eff"]
    V = p["Y"] * Q * th * dS / (X * (1 + p["kd"] * th))
    Px = p["Y"] / (1 + p["kd"] * th) * Q * dS / 1000            # كغم VSS/يوم
    Xr = p["xr_f"] * 1e6 / p["svi"]
    R = p["mlss"] / (Xr - p["mlss"]) if Xr > p["mlss"] else float("nan")
    q_ras, q_was = R * Q, V * p["mlss"] / (th * Xr)
    O2 = Q * dS / 1000 / p["bod_bodu"] - 1.42 * Px
    d = dict(V=V, R=R, q_ras=q_ras, q_was=q_was, Xr=Xr, Px=Px, O2=O2)
    rows = [("BOD5 الداخل للهوائي", S0, "ملغم/لتر"), ("حجم حوض التهوية", V, "م³"), ("HRT", V / Q * 24, "ساعة"),
            ("F/M", Q * S0 / (V * p["mlss"]), "1/يوم"), ("الحمل الحجمي", Q * S0 / 1000 / V, "كغم BOD/م³·يوم"),
            ("Xr", Xr, "ملغم/لتر"), ("نسبة الإرجاع R", R, "-"), ("RAS", q_ras, "م³/يوم"), ("RAS", q_ras / 86.4, "لتر/ث"),
            ("WAS", q_was, "م³/يوم"), ("WAS", q_was / 86.4, "لتر/ث"), ("إنتاج الكتلة الحيوية VSS", Px, "كغم/يوم"),
            ("الأكسجين الكربوني المطلوب (دون نترجة)", O2, "كغم O₂/يوم")]
    checks = [chk("F/M", Q * S0 / (V * p["mlss"]), 0.2, 0.6, "1/يوم"), chk("HRT", V / Q * 24, 4, 8.5, "ساعة"),
              chk("الحمل الحجمي", Q * S0 / 1000 / V, 0.3, 1.0), chk("R", R, 0.25, 1.0)]
    return dict(d=d, rows=rows, checks=checks)


def u_secondary(p, ctx):
    f, b = ctx["flows"]["d"], ctx["bio"]["d"]; n = max(int(p["n_s"]), 1)
    Qa, Qp, Qr, M = f["q_avg"], f["q_peak"], b["q_ras"], p["mlss"]
    crit = {"SOR عند Q_avg": Qa / p["sor_s"], "SOR عند Q_peak (≤40)": Qp / 40,
            "تحميل الجوامد عند Q_avg (≤4)": (Qa + Qr) * M / 1000 / 24 / 4,
            "تحميل الجوامد عند Q_peak (≤8)": (Qp + Qr) * M / 1000 / 24 / 8}
    gov = max(crit, key=crit.get); A = crit[gov]; D1 = math.sqrt(4 * A / n / math.pi)
    rows = [("المساحة المطلوبة", A, "م²"), ("المعيار الحاكم", gov, "-"), ("قطر الحوض الواحد", D1, "م"),
            ("الحجم الفعال", A * p["depth_s"], "م³"), ("SOR الفعلي عند Q_avg", Qa / A, "م/يوم"),
            ("SOR الفعلي عند Q_peak", Qp / A, "م/يوم")]
    return dict(d=dict(A=A, D1=D1), rows=rows, checks=[chk("عمق الحوض", p["depth_s"], 3.5, 6, "م")])


UNITS = [("flows", u_flows), ("pump", u_pump), ("well", u_well), ("primary", u_primary), ("bio", u_bio), ("secondary", u_secondary)]


def run_all(p):
    ctx = {}
    for key, fn in UNITS:
        ctx[key] = fn(p, ctx)
    return ctx
