"""Population-certified finite lambda bank for unknown burst effect size."""
from __future__ import annotations
import json
from decimal import Decimal,localcontext,ROUND_FLOOR
from fractions import Fraction
from pathlib import Path
HERE=Path(__file__).resolve().parent
CERT=HERE/'EXACT_THREE_PARAMETER_EFACTOR_ENVELOPE.json'
BANDS=HERE/'EF ACTOR_INTERMEDIATE_BAND_EXPECTED_LOG_BOUNDS.json'
BASE=HERE/'EFACTOR_FREEDMAN_MEAN_RANGE_BOUNDS.json'
OUT=HERE/'EFACTOR_LAMBDA_BANK_FEASIBILITY.json'
ALPHA=Fraction(1,20);STARTS=(1,1000,1000000)

def frac(record):return Fraction(int(record['numerator']),int(record['denominator']))
def decfrac(x):return Decimal(x.numerator)/Decimal(x.denominator)
def compact_bound(record,lower):
    with localcontext() as c:
        c.prec=70
        d=Decimal(record['decimal_35_digits'])+ (Decimal('-1e-32') if lower else Decimal('1e-32'))
        return Fraction(d)
def log_interval(x):
    import sys
    for q in (HERE.parents[1],HERE.parents[1]/'outputs'/'phase3a_correlated_noise_preflight',HERE.parents[1]/'outputs'/'stage4_noise_adaptive_feasibility_v1'):
        if str(q) not in sys.path:sys.path.insert(0,str(q))
    import cofire_category_continuous_envelope as tools
    return tools.log_rational_interval(x,terms=24)
def endpoint_logs(m0,lam):
    f0=1-lam;f1=1+lam*(1/m0-1)
    return log_interval(f0),log_interval(f1)
def chord_mu(m0,lam,zlo,logs):
    (a0,a1),(b0,b1)=logs
    return (1-zlo)*a0+zlo*b0
def log_upper(m0,lam,zhi):return log_interval(1+lam*(zhi/m0-1))[1]
def triplet(a,b,mu,u):
    mid=(a+b)/2;cl=min(max(mid,mu),u)
    v=(b-cl)*(cl-a)+Fraction(1,10**35)
    C=max(u-a,b-mu)+Fraction(1,10**35)
    return v,C
def freedman_n(mu,v,C,alpha,w,delta=Fraction(1,10)):
    import math
    with localcontext() as c:c.prec=70
    # Decimal log threshold from exact rational component prior.
    A=decfrac(1/(alpha*w)).ln();target=decfrac(delta)
    def bound(n):
        x=Decimal(n)*decfrac(mu)-A
        if x<=0:return Decimal(1)
        return (-(x*x)/(2*(Decimal(n)*decfrac(v)+decfrac(C)*x/Decimal(3)))).exp()
    lo=hi=1
    while bound(hi)>target:hi*=2
    while lo<hi:
        m=(lo+hi)//2
        if bound(m)<=target:hi=m
        else:lo=m+1
    if bound(lo)>target or bound(lo-1)<=target:raise AssertionError('minimal n')
    return lo,bound(lo),bound(lo-1)

def main():
    cert=json.loads(CERT.read_text(encoding='utf-8-sig'));bands=json.loads(BANDS.read_text(encoding='utf-8-sig'));base=json.loads(BASE.read_text(encoding='utf-8-sig'))
    mean_bounds=cert['tensor_bernstein']; robust=cert['robust_mean_e_factor_population_analysis']
    bm={a['direction']:{tuple(r['burst_interval']):r for r in a['bands']} for a in bands['arms']}
    results=[]
    for direction in ('upward','downward_on_complement'):
        if direction=='upward':
            m0=frac(robust['upward']['exact_null_mean_upper'])
            names=['.004-.006','.006-.008','.008-.010','.010-.018']
            specs=[(bm['upward'][(.004,.006)],'band'),(bm['upward'][(.006,.008)],'band'),(bm['upward'][(.008,.01)],'band'),(None,'high')]
            highlo=frac(mean_bounds['high_box']['exact_mean_lower_bound']);highhi=frac(mean_bounds['high_box']['exact_mean_upper_bound'])
        else:
            m0=frac(robust['downward_on_complement_1_minus_X']['exact_null_mean_upper'])
            names=['.006-.008','.004-.006','.002-.004','0-.002']
            specs=[(bm['downward_on_complement'][(.006,.008)],'band'),(bm['downward_on_complement'][(.004,.006)],'band'),(bm['downward_on_complement'][(.002,.004)],'band'),(None,'low')]
            lowlo=1-frac(mean_bounds['null_box']['exact_mean_upper_bound']);lowhi=1-frac(mean_bounds['null_box']['exact_mean_lower_bound'])
        candidates=[]
        for nm,(row,kind) in zip(names,specs):
            if kind=='band':zlo=compact_bound(row['trigger_statistic_mean_exact_bounds'][0],True)
            else:zlo=highlo if direction=='upward' else lowlo
            opt=zlo-(1-zlo)/(1/m0-1)
            with localcontext() as c:
                c.prec=70; scaled=decfrac(opt)*Decimal(10**6);lam=Fraction(int(scaled.to_integral_value(rounding=ROUND_FLOOR)),10**6)
            if not 0<lam<1:raise AssertionError('invalid tuned lambda')
            candidates.append({'target_region':nm,'lambda':float(lam),'lambda_exact':f'{lam.numerator}/{lam.denominator}'})
        # For every lambda candidate, certify chord/Jensen drift on every region in the ordered bank.
        matrix=[]
        for ci,cand in enumerate(candidates):
            lam=Fraction(int(cand['lambda_exact'].split('/')[0]),int(cand['lambda_exact'].split('/')[1]));logs=endpoint_logs(m0,lam);(a0,a1),(b0,b1)=logs;a=a0;b=b1
            for nm,(row,kind) in zip(names,specs):
                if kind=='band':zlo=compact_bound(row['trigger_statistic_mean_exact_bounds'][0],True);zhi=compact_bound(row['trigger_statistic_mean_exact_bounds'][1],False)
                elif direction=='upward':zlo=highlo;zhi=highhi
                else:zlo=lowlo;zhi=lowhi
                mu=chord_mu(m0,lam,zlo,logs);u=log_upper(m0,lam,zhi)
                rec={'lambda_target_region':cand['target_region'],'lambda':cand['lambda'],'evaluated_region':nm,'log_growth_lower':float(mu),'log_growth_upper':float(u),'sign':'positive' if mu>0 else ('nonpositive' if u<=0 else 'uncertified')}
                if mu>0:
                    v,C=triplet(a,b,mu,u);rec['sufficient_postchange_shots_alpha_005_delta_010_by_start']={}
                    for s in STARTS:
                        w=Fraction(1,s*(s+1)*len(candidates));n,bd,prev=freedman_n(mu,v,C,ALPHA,w)
                        rec['sufficient_postchange_shots_alpha_005_delta_010_by_start'][str(s)]={'n':n,'bound_at_n':str(bd),'bound_at_n_minus_1':str(prev)}
                matrix.append(rec)
        results.append({'direction':direction,'m0_null_upper':float(m0),'uniform_lambda_prior_weight':f'1/{len(candidates)}','candidate_lambda_bank':candidates,'growth_and_delay_matrix':matrix})
    out={'classification':'ANALYTIC_FINITE_LAMBDA_MIXTURE_POPULATION_CERTIFICATE','mixture':'For each candidate change start, average the four fixed lambda e-factor components with equal prior weight; then mix over start times. Each factor is null-valid, so the fixed convex mixture is null-valid.','lambda_selection':'For each target region, set lambda to the six-decimal downward-rounded endpoint-chord optimum using the continuous lower mean bound for that region. The bank is fixed before any stream; no online parameter fit or labels.','false_alarm':'For a single predeclared direction and null rectangle, Ville controls the mixture ever-crossing probability at alpha. Component-specific delay thresholds include the additional log(4) lambda-bank penalty.','arms':results,'limitations':['Exact categorical circuit and declared p_m/p_g rectangles only.','Mean/chord and Jensen bounds are conservative; bank delays are sufficient quantiles, not observed or expected delays.','A positive alarm does not identify p_b or a decoder graph; no action utility is evaluated.','No streams, sampling, or decodes were generated.']}
    OUT.write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
    for arm in results:
        print(arm['direction'])
        for r in arm['growth_and_delay_matrix']:
            if r['lambda_target_region']==r['evaluated_region']:print(r['lambda_target_region'],r['lambda'],r['log_growth_lower'],r.get('sufficient_postchange_shots_alpha_005_delta_010_by_start',{}).get('1000',{}).get('n'))
if __name__=='__main__':main()
