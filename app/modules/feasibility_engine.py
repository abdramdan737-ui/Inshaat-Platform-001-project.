import copy
import numpy as np
import pandas as pd
import numpy_financial as npf
from modules.feasibility_templates import LAND_BUY, LAND_RENT, FX

def _num(values):
    return pd.to_numeric(pd.Series(values), errors="coerce").fillna(0.).to_numpy(float)

def _irr(cf):
    try:
        v=npf.irr(cf)
        return float(v) if np.isfinite(v) else np.nan
    except Exception:
        return np.nan

def _tax(base, rate, hol_start, hol_len):
    tax=np.zeros(len(base)); nol=0.
    for t,b in enumerate(base):
        if b<0:
            nol += -b
        elif hol_start <= t < hol_start+hol_len:
            continue
        else:
            use=min(nol,b); nol-=use; tax[t]=(b-use)*rate
    return tax

def _payback(cf, construction_years):
    # النتيجة سنوات من بداية التشغيل، مع استيفاء خطي داخل سنة الاسترداد.
    cum=np.cumsum(cf)
    candidates=np.where((cum>=0)&(np.arange(len(cf))>=construction_years))[0]
    if not len(candidates): return np.nan
    i=int(candidates[0])
    previous=cum[i-1] if i>0 else 0.
    if cf[i] <= 0: return np.nan
    return max(0., (i-construction_years) + (-previous/cf[i]))

def prep(i):
    a=dict(i["scalars"]); nc=int(a["Nc"])
    cx,rv,ox,rp=i["capex"],i["revenue"],i["opex"],i["repl"]
    a["cx_amt"]=_num(cx.iloc[:,1]); a["cx_life"]=np.maximum(_num(cx.iloc[:,2]),1)
    phases=_num(i["phase"].iloc[:,1])
    a["phase"]=phases/phases.sum() if len(phases)==nc and phases.sum()>0 else np.full(nc,1/nc)
    a["units"],a["price"]=_num(rv.iloc[:,1]),_num(rv.iloc[:,2])
    a["occ"],a["ramp"]=_num(rv.iloc[:,3])/100,np.maximum(_num(rv.iloc[:,4]),1)
    a["rg"]=_num(rv.iloc[:,5])/100
    pct=ox.iloc[:,1].astype(str).str.startswith("%").to_numpy()
    vals=_num(ox.iloc[:,2])
    a["ox_pct"],a["ox_val"],a["og"]=pct,np.where(pct,vals/100,vals),_num(ox.iloc[:,3])/100
    a["rp_yr"],a["rp_amt"]=_num(rp.iloc[:,1]).astype(int),_num(rp.iloc[:,2])
    return a

def run(a, rev=1., opex=1., capex=1., r=None):
    nc,no=int(a["Nc"]),int(a["No"]); total=nc+no
    r=a["r"] if r is None else float(r)
    if total<1: raise ValueError("مدة المشروع غير صحيحة.")
    t=np.arange(total); operating=t>=nc
    k=np.where(operating,t-nc+1,0); kk=k[:,None]; kp=np.maximum(kk-1,0)
    ramp=np.minimum(1.,kk/a["ramp"][None,:])
    R=(a["units"]*a["price"]*a["occ"]*ramp*(1+a["rg"])**kp*(kk>=1)).sum(1)*rev
    fixed=(a["ox_val"]*(~a["ox_pct"])*(1+a["og"])**kp*(kk>=1)).sum(1)
    variable=R*a["ox_val"][a["ox_pct"]].sum()
    rent=(a["land_rent"]*(1+a["rent_g"])**np.maximum(k-1,0)*operating) if a["land_mode"]==LAND_RENT else np.zeros(total)
    O=(fixed+variable+rent)*opex
    E=R-O
    hard=a["cx_amt"].sum()*(1+a["cont"])*capex
    capital=np.zeros(total); capital[:nc]=hard*a["phase"]
    buy=a["land_mode"]==LAND_BUY
    if buy: capital[0]+=a["land_value"]
    dep=(((kk>=1)&(kk<=a["cx_life"][None,:]))*(a["cx_amt"]*(1+a["cont"])*capex/a["cx_life"])[None,:]).sum(1)
    repl=np.array([a["rp_amt"][a["rp_yr"]==v].sum() if v>0 else 0. for v in k])*capex
    terminal=np.zeros(total); terminal[-1]=a["salvage"]+(a["land_value"]*(1+a["land_g"])**no if buy else 0.)
    wc=a["wc"]*R; dwc=np.diff(np.r_[0.,wc]); wc_release=np.zeros(total); wc_release[-1]=wc[-1]
    ebit=E-dep-repl
    tax_unlevered=_tax(ebit,a["tax"],nc,a["holiday"])
    fcff=E-tax_unlevered-repl-dwc-capital+terminal+wc_release

    draw=capital*a["debt"]; total_debt=draw.sum()
    n=max(int(a["repay"]),1); repay_start=nc+int(a["grace"])
    interest=np.zeros(total); principal=np.zeros(total); balance=0.
    for year in range(total):
        interest[year]=balance*a["ir"]
        balance+=draw[year]
        if repay_start<=year<repay_start+n:
            principal[year]=min(balance,total_debt/n); balance-=principal[year]
    principal[-1]+=balance
    tax_levered=_tax(ebit-interest,a["tax"],nc,a["holiday"])
    fcfe=E-tax_levered-repl-dwc-capital+terminal+wc_release+draw-interest-principal
    cfads=E-tax_levered-repl-dwc
    debt_service=interest+principal
    dscr=np.where((debt_service>0)&operating,cfads/np.where(debt_service>0,debt_service,1),np.nan)

    discount=(1+r)**t
    npv=float(npf.npv(r,fcff))
    try: mirr=float(npf.mirr(fcff,r,r))
    except Exception: mirr=np.nan
    pv=lambda x:float(np.sum(np.asarray(x)/discount))
    cost_pv=pv(capital+O+repl+tax_unlevered+np.maximum(dwc,0))
    positive_pv=pv(np.maximum(R+terminal+wc_release,0))
    bcr=positive_pv/cost_pv if cost_pv>0 else np.nan
    pv_cap=pv(capital)
    result=dict(npv=npv,irr=_irr(fcff),mirr=mirr,bcr=bcr,
      pi=1+npv/pv_cap if pv_cap else np.nan,payback=_payback(fcff,nc),
      dpayback=_payback(fcff/discount,nc),invest=float(capital.sum()),
      roi=float(np.mean((E-tax_unlevered)[operating])/capital.sum()) if capital.sum() else np.nan,
      irr_e=_irr(fcfe),npv_e=float(npf.npv(a["ke"],fcfe)),
      dscr_min=float(np.nanmin(dscr)) if np.isfinite(dscr).any() else np.nan,
      dscr_avg=float(np.nanmean(dscr)) if np.isfinite(dscr).any() else np.nan,debt=float(total_debt))
    result.update(t=t,rev=R,opex=O,ebitda=E,dep=dep,tax=tax_unlevered,capex=capital,repl=repl,dwc=dwc,
      term=terminal+wc_release,fcff=fcff,fcfe=fcfe,interest=interest,principal=principal,draw=draw,dscr=dscr)
    return result

def breakeven_revenue(a):
    f=lambda x:run(a,rev=x)["npv"]
    lo,hi=0.,5.
    if f(hi)<0:return np.nan
    for _ in range(60):
        mid=(lo+hi)/2
        if f(mid)<0:lo=mid
        else:hi=mid
    return (lo+hi)/2

def sensitivity(a,deltas=(-.3,-.2,-.1,0,.1,.2,.3)):
    return pd.DataFrame({
      "الإيراد":[run(a,rev=1+d)["npv"] for d in deltas],
      "التشغيل":[run(a,opex=1+d)["npv"] for d in deltas],
      "الكلفة الرأسمالية":[run(a,capex=1+d)["npv"] for d in deltas],
      "معدل الخصم":[run(a,r=max(-.99,a["r"]*(1+d)))["npv"] for d in deltas]
    },index=[f"{d:+.0%}" for d in deltas])

def monte_carlo(a,n,rev,opex,capex,r,seed=42):
    rng=np.random.default_rng(seed)
    samples=[rng.triangular(*p,n) for p in (rev,opex,capex,r)]
    outcomes=[run(a,rev=samples[0][j],opex=samples[1][j],capex=samples[2][j],r=samples[3][j]) for j in range(n)]
    return np.array([x["npv"] for x in outcomes]),np.array([x["irr"] for x in outcomes])

def economic(i,benefits,scf_capex,scf_opex,rate):
    j=copy.deepcopy(i); j["scalars"].update(tax=0.,debt=0.,holiday=0,r=rate,ke=rate)
    b=pd.DataFrame({0:benefits.iloc[:,0].values,1:1.,2:_num(benefits.iloc[:,1]),3:100.,4:1.,5:_num(benefits.iloc[:,2])})
    j["revenue"]=pd.concat([j["revenue"].set_axis(range(6),axis=1),b],ignore_index=True)
    return run(prep(j),capex=scf_capex,opex=scf_opex)
