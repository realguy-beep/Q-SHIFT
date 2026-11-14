"""Delay sensitivity for finite-horizon uniform change-point e-mixtures."""
from __future__ import annotations
import json
from decimal import Decimal,localcontext
from fractions import Fraction
from pathlib import Path
HERE=Path(__file__).resolve().parent
INPUT=HERE/'EFACTOR_FREEDMAN_MEAN_RANGE_BOUNDS.json'
OUTPUT=HERE/'EFACTOR_FINITE_HORIZON_PRIOR_SENSITIVITY.json'
HORIZONS=(1000,10000,100000,1000000)
ALPHAS=(Fraction(1,20),Fraction(1,100))
DELTAS=(Fraction(1,10),Fraction(1,20))

def ln_fraction(q):
    with localcontext() as c:
        c.prec=70
        return (Decimal(q.numerator)/Decimal(q.denominator)).ln()

def bound(n,alpha,H,mu,v,C):
    A=ln_fraction(Fraction(H,1)/alpha);x=Decimal(n)*mu-A
    if x<=0:return Decimal(1)
    return (-(x*x)/(2*(Decimal(n)*v+C*x/Decimal(3)))).exp()

def first_n(alpha,H,delta,mu,v,C):
    target=Decimal(delta.numerator)/Decimal(delta.denominator);lo=hi=1
    while bound(hi,alpha,H,mu,v,C)>target:hi*=2
    while lo<hi:
        mid=(lo+hi)//2
        if bound(mid,alpha,H,mu,v,C)<=target:hi=mid
        else:lo=mid+1
    if bound(lo,alpha,H,mu,v,C)>target or bound(lo-1,alpha,H,mu,v,C)<=target:raise AssertionError('minimal n')
    return lo

def main():
    inp=json.loads(INPUT.read_text(encoding='utf-8-sig'));arms=[]
    for arm in inp['arms']:
        mu=Decimal(arm['alternative_mean_lower_log_mu']);v=Decimal(arm['conditional_variance_upper_v']);C=Decimal(arm['centered_increment_absolute_bound_c']);rows=[]
        for H in HORIZONS:
          for alpha in ALPHAS:
           for delta in DELTAS:
            n=first_n(alpha,H,delta,mu,v,C);b=bound(n,alpha,H,mu,v,C);prev=bound(n-1,alpha,H,mu,v,C)
            rows.append({'horizon_shots_H':H,'uniform_start_prior_exact':f'1/{H}','alpha':float(alpha),'delta':float(delta),'sufficient_postchange_shots_any_start_within_H':n,'freedman_bound_at_n':str(b),'bound_at_n_minus_1':str(prev)})
        arms.append({'direction':arm['direction'],'rows':rows})
    result={'classification':'ANALYTIC_FINITE_HORIZON_UNIFORM_CHANGEPOINT_PRIOR_SENSITIVITY','prior':'For selected horizon H, w_s=1/H for s=1,...,H; no component is added after H.','constant_memory_recurrence':'A_0=0; for t<=H, A_t=L_t*(A_(t-1)+1/H), E_t=A_t+(H-t)/H. For t>H, A_t=L_t*A_(t-1), E_t=A_t.','null_guarantee':'For one fixed directional null, the finite mixture is a nonnegative supermartingale and Ville controls the ever-crossing probability over all t, including t>H.','change_guarantee':'A transition beginning at any s<=H has prior component weight 1/H; use component threshold log(H/alpha) and the continuous Freedman postchange bound. Changes starting after H receive no guaranteed prior component.','horizons':list(HORIZONS),'arms':arms,'owner_decision':'Choose a justified deployment horizon; the infinite prior remains available if no finite horizon is prespecified.','limitations':['One change and one preselected direction only.','No resets, reverse transitions, repeated-change guarantees, or decoder utility.','The horizon is an index range for candidate change starts, not a learned or observed time.','No detector sequences or sampling were generated.']}
    OUTPUT.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps([{ 'direction':a['direction'],'rows':[r for r in a['rows'] if r['alpha']==.05 and r['delta']==.1]} for a in arms],indent=2))
if __name__=='__main__':main()
