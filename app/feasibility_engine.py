# -*- coding: utf-8 -*-
"""محرك دراسة الجدوى (FCFF/FCFE) - يعتمد numpy فقط في الحلقات الداخلية."""
import copy
import numpy as np
import pandas as pd
import numpy_financial as npf

LAND_BUY, LAND_RENT, LAND_FREE = "شراء", "إيجار سنوي", "مقدَّمة بلا كلفة"


def _num(s):
    return pd.to_numeric(pd.Series(s), errors="coerce").fillna(0.0).to_numpy(float)


def _irr(cf):
    try:
        v = npf.irr(cf)
        return float(v) if np.isfinite(v) else np.nan
    except Exception:
        return np.nan


def _tax(base, rate, hol_start, hol_len):
    """ضريبة دخل مع ترحيل الخسائر وإعفاء ضريبي (hol_len سنة من بدء التشغيل)."""
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
    return (i - 1) + (-cum[i - 1]) / cf[i] - (Nc - 1)   # سنوات من بدء التشغيل


def prep(i):
    """تحويل جداول الواجهة إلى مصفوفات. المدخلات النسبية في scalars كسور عشرية."""
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

    # --- الإيرادات
    ramp = np.minimum(1.0, kk / a["ramp"][None, :])
    R = (a["units"] * a["price"] * a["occ"] * ramp * (1 + a["rg"]) ** kp * (kk >= 1)).sum(1) * rev
    # --- التشغيل
    fx = (a["ox_val"] * (~a["ox_pct"]) * (1 + a["og"]) ** kp * (kk >= 1)).sum(1)
    var = R * a["ox_val"][a["ox_pct"]].sum()
    rent = a["land_rent"] * (1 + a["rent_g"]) ** kp[:, 0] * op if a["land_mode"] == LAND_RENT else 0.0
    O = (fx + var + rent) * opex
    E = R - O                                              # EBITDA
    # --- الرأسمالية
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

    # --- التمويل
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
    """كل وسيط ثلاثية (min, mode, max) - توزيع مثلثي."""
    g = np.random.default_rng(seed)
    S = [g.triangular(*p, n) for p in (rev, opex, capex, r)]
    res = [run(a, rev=S[0][j], opex=S[1][j], capex=S[2][j], r=S[3][j]) for j in range(n)]
    return np.array([x["npv"] for x in res]), np.array([x["irr"] for x in res])


def economic(i, benefits, scf_capex, scf_opex, rate):
    """تحليل اقتصادي/اجتماعي: بلا ضريبة وتمويل، عوامل تحويل للكلف، ومنافع اجتماعية تُضاف للإيراد."""
    j = copy.deepcopy(i)
    j["scalars"].update(tax=0.0, debt=0.0, holiday=0, r=rate)
    b = pd.DataFrame({0: benefits.iloc[:, 0].values, 1: 1.0, 2: _num(benefits.iloc[:, 1]),
                      3: 100.0, 4: 1.0, 5: _num(benefits.iloc[:, 2])})
    j["revenue"] = pd.concat([j["revenue"].set_axis(range(6), axis=1), b], ignore_index=True)
    return run(prep(j), capex=scf_capex, opex=scf_opex)
