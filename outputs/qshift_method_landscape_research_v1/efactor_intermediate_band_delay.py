"""Freedman delay bounds for sign-certified intermediate burst plateaus."""
from __future__ import annotations
import json
from decimal import Decimal,localcontext
from fractions import Fraction
from pathlib import Path
HERE=Path(__file__).resolve().parent
BANDS=HERE/'EF ACTOR_INTERMEDIATE_BAND_EXPECTED_LOG_BOUNDS.json'
BASE=HERE/'EFACTOR_FREEDMAN_MEAN_RANGE_BOUNDS.json'
OUT=HERE/'EFACTOR_INTERMEDIATE_BAND_DELAY_BOUNDS.json'
STARTS=(1,1000,1000000)
SLACK=Decimal('1e-32')

def bound(n,alpha,w,mu,v,c):
    with localcontext() as ctx:
        ctx.prec=70
        A=(Decimal(1)/(Decimal(alpha.numerator)/Decimal(alpha.denominator)*Decimal(w.numerator)/Decimal(w.denominator))).ln()
        x=Decimal(n)*mu-A
        if x<=0:return Decimal(1)
        return (-(x*x)/(2*(Decimal(n)*v+c*x/Decimal(3)))).exp()

def first_n(alpha,w,delta,mu,v,c):
    target=Decimal(delta.numerator)/Decimal(delta.denominator);lo=hi=1
    while bound(hi,alpha,w,mu,v,c)>target:hi*=2
    while lo<hi:
        mid=(lo+hi)//2
        if bound(mid,alpha,w,mu,v,c)<=target:hi=mid
        else:lo=mid+1
    n=lo
    if bound(n,alpha,w,mu,v,c)>target or bound(n-1,alpha,w,mu,v,c)<=target:raise AssertionError('minimal n')
    return n

def main():
    bands=json.loads(BANDS.read_text(encoding='utf-8-sig'));base=json.loads(BASE.read_text(encoding='utf-8-sig'));baseby={a['direction']:a for a in base['arms']};results=[]
    for arm in bands['arms']:
        support=baseby[arm['direction']]['log_increment_support'];a=Decimal(support[0])-SLACK;b=Decimal(support[1])+SLACK;rows=[]
        for band in arm['bands']:
            if band['sign_classification']!='uniform_positive':continue
            mu=Decimal(band['expected_log_lower_exact']['decimal_35_digits'])-SLACK
            u=Decimal(band['expected_log_upper_exact']['decimal_35_digits'])+SLACK
            midpoint=(a+b)/2;clip=min(max(midpoint,mu),u)
            v=(b-clip)*(clip-a)+SLACK;c=max(u-a,b-mu)+SLACK
            for s in STARTS:
                w=Fraction(1,s*(s+1));n=first_n(Fraction(1,20),w,Fraction(1,10),mu,v,c)
                rows.append({'burst_interval':band['burst_interval'],'candidate_start_shot':s,'prior_weight':f'{w.numerator}/{w.denominator}','alpha':.05,'delta':.10,'sufficient_postchange_shots':n,'freedman_bound_at_n':str(bound(n,Fraction(1,20),w,mu,v,c)),'bound_at_n_minus_1':str(bound(n-1,Fraction(1,20),w,mu,v,c)),'mu_log_lower':str(mu),'u_log_upper':str(u),'variance_upper_v':str(v),'centered_increment_bound_c':str(c)})
        results.append({'direction':arm['direction'],'rows':rows})
    result={'classification':'CONTINUOUS_EXACT_CIRCUIT_INTERMEDIATE_BAND_FREEDMAN_QUANTILES','inputs':[BANDS.name,BASE.name],'assumption':'A sustained conditional law stays in one sign-certified burst band and the preselected one-sided null-valid process uses its fixed prior mixture component for that change start.','rows_by_direction':results,'limitations':['Only bands with positive continuous expected-log lower certificates are included.','A smooth trajectory crossing multiple bands is not covered by a per-band sustained-alternative delay bound; negative drift accrued before the positive band is not erased except by the candidate-start component, which starts at the chosen band entry.','These are sufficient distribution-free quantiles, not observed or expected delays.','No graph action, decoder outcome, or stochastic trajectory was evaluated.']}
    OUT.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    for a in results:
        print(a['direction'])
        for r in a['rows']:print(r['burst_interval'],r['candidate_start_shot'],r['sufficient_postchange_shots'])
if __name__=='__main__':main()
