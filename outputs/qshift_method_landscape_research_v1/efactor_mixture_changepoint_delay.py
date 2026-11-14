"""Deterministic delay screen for an anytime mixture over one change point.
The mixture uses the previously certified one-sided exact-circuit e-factors.
No streams, histories, or decoder outcomes are generated.
"""
from __future__ import annotations
import json
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path

HERE=Path(__file__).resolve().parent
INPUT=HERE/'EFACTOR_FREEDMAN_MEAN_RANGE_BOUNDS.json'
OUTPUT=HERE/'EFACTOR_MIXTURE_CHANGEPOINT_DELAY.json'
STARTS=(1,100,1000,10000,100000,1000000)
ALPHAS=(Fraction(1,20),Fraction(1,100))
DELTAS=(Fraction(1,10),Fraction(1,20))


def log_fraction(q:Fraction)->Decimal:
    with localcontext() as c:
        c.prec=70
        return (Decimal(q.numerator)/Decimal(q.denominator)).ln()


def bound(n,alpha,w,mu,v,c):
    A=log_fraction(1/(alpha*w))
    x=Decimal(n)*mu-A
    if x<=0:return Decimal(1)
    return (-(x*x)/(2*(Decimal(n)*v+c*x/Decimal(3)))).exp()


def first_n(alpha,w,delta,mu,v,c):
    lo=hi=1
    d=Decimal(delta.numerator)/Decimal(delta.denominator)
    while bound(hi,alpha,w,mu,v,c)>d:hi*=2
    while lo<hi:
        mid=(lo+hi)//2
        if bound(mid,alpha,w,mu,v,c)<=d:hi=mid
        else:lo=mid+1
    n=lo
    if bound(n,alpha,w,mu,v,c)>d or (n>1 and bound(n-1,alpha,w,mu,v,c)<=d):
        raise AssertionError('minimal crossing n validation failed')
    return n


def main():
    base=json.loads(INPUT.read_text(encoding='utf-8-sig'))
    analyses=[]
    for arm in base['arms']:
        mu=Decimal(arm['alternative_mean_lower_log_mu']);v=Decimal(arm['conditional_variance_upper_v']);c=Decimal(arm['centered_increment_absolute_bound_c'])
        out=[]
        for s in STARTS:
            w=Fraction(1,s*(s+1))
            for alpha in ALPHAS:
                for delta in DELTAS:
                    n=first_n(alpha,w,delta,mu,v,c)
                    val=bound(n,alpha,w,mu,v,c);prev=bound(n-1,alpha,w,mu,v,c) if n>1 else Decimal(1)
                    out.append({'candidate_change_start_shot':s,'prior_weight_exact':f'{w.numerator}/{w.denominator}','alpha':float(alpha),'delta':float(delta),'sufficient_postchange_shots':n,'freedman_bound_at_n':str(val),'bound_at_n_minus_1':str(prev)})
        analyses.append({'direction':arm['direction'],'conditional_log_drift_mu':str(mu),'variance_upper_v':str(v),'centered_increment_bound_c':str(c),'rows':out})
    # Exact telescoping check for the prior.
    partial=sum((Fraction(1,s*(s+1)) for s in range(1,10001)),Fraction(0))
    assert partial==Fraction(10000,10001)
    result={'classification':'ANALYTIC_ANYTIME_ONE_CHANGE_E_MIXTURE_WITH_FREEDMAN_DELAY_BOUNDS','prior':'w_s=1/(s(s+1)), s=1,2,...; exact sum equals one by telescoping','mixture_definition':'At time t, E_t=sum_{s>=1} w_s M_t^(s), where M_t^(s)=1 before candidate start s and product of one-step null-valid factors from s through t afterward.','constant_memory_recurrence':'A_0=0; A_t=L_t*(A_(t-1)+1/(t*(t+1))); E_t=A_t+1/(t+1). This equals the infinite component mixture exactly because future prior mass sums to 1/(t+1).','null_guarantee':'If the single sustained no-change null rectangle holds conditionally each shot, every component is a nonnegative supermartingale; their fixed convex mixture is a nonnegative supermartingale. Ville gives P(sup_t E_t>=1/alpha)<=alpha.','change_guarantee':'If an abrupt transition occurs at candidate start s and the alternative rectangle holds conditionally thereafter, E_t>=w_s*M_t^(s). Thus the single-process Freedman quantile applies with threshold A_s=log(1/(alpha*w_s)); it is a sufficient post-change detection-delay bound.','inheritance':'The exact-circuit conditional mean/log bounds and Freedman parameters are inherited unchanged from EFACTOR_FREEDMAN_MEAN_RANGE_BOUNDS.json.','prior_normalization_partial_sum_10000':str(partial),'arms':analyses,'assumptions':['One direction is selected in advance from a trusted initial-regime designation; the corresponding single null rectangle must hold when no change occurs.','No automatic reverse transition, reset, or restarted process after a switch.','The change is abrupt and the true change shot is represented by a prior component.','The exact categorical circuit and conditional parameter rectangles remain valid.'],'limitations':['This is a regime detector only; it does not estimate p_b or select the matching graph.','No repeated-change or bidirectional state-machine guarantee is established.','Running multiple directions is not justified merely by splitting alpha; each arm needs a valid null premise or a common-null construction.','Prior weights trade later change times for larger thresholds.','Delay bounds are sufficient analytic quantiles, not expected/observed delays or decoder utility.','No simulations or detector histories were generated.']}
    OUTPUT.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps([{ 'direction':a['direction'],'rows':[r for r in a['rows'] if r['alpha']==.05 and r['delta']==.1]} for a in analyses],indent=2))
    print('WROTE',OUTPUT.name)

if __name__=='__main__':main()
