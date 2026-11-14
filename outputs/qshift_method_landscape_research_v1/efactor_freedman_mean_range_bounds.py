"""Continuous Freedman delay bounds from certified exact-circuit mean envelopes.
No trajectories, sampling, or decoder calls are used.
"""
from __future__ import annotations
import json
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path

HERE=Path(__file__).resolve().parent
SOURCE=HERE/'EXACT_THREE_PARAMETER_EFACTOR_ENVELOPE.json'
OUTPUT=HERE/'EFACTOR_FREEDMAN_MEAN_RANGE_BOUNDS.json'
SLACK=Decimal('1e-30')


def fraction(record):
    return Fraction(int(record['numerator']),int(record['denominator']))


def dec_fraction(x:Fraction)->Decimal:
    return Decimal(x.numerator)/Decimal(x.denominator)


def ln_fraction(x:Fraction)->Decimal:
    if x<=0:raise ValueError('log input must be positive')
    return dec_fraction(x).ln()


def freedman_bound(n:int,alpha:Fraction,delta:Fraction,mu:Decimal,v:Decimal,c:Decimal)->Decimal:
    with localcontext() as ctx:
        ctx.prec=70
        A=ln_fraction(1/alpha)
        x=Decimal(n)*mu-A
        if x<=0:return Decimal(1)
        denom=2*(Decimal(n)*v+c*x/Decimal(3))
        return (-(x*x)/denom).exp()


def first_n(alpha,delta,mu,v,c):
    lo,hi=1,1
    while freedman_bound(hi,alpha,delta,mu,v,c)>dec_fraction(delta):hi*=2
    while lo<hi:
        mid=(lo+hi)//2
        if freedman_bound(mid,alpha,delta,mu,v,c)<=dec_fraction(delta):hi=mid
        else:lo=mid+1
    return lo


def main():
    src=json.loads(SOURCE.read_text(encoding='utf-8-sig'))
    tensor=src['tensor_bernstein']; optimum=src['robust_mean_e_factor_population_analysis']['endpoint_chord_optimum']
    rows=[]
    for direction in ('upward','downward_on_complement'):
        cfg=optimum[direction]
        lam=fraction(cfg['exact_optimal_lambda'])
        mean_log_lower=Decimal(cfg['exact_uniform_expected_log_lower_bound']['decimal_35_digits'])-SLACK
        log0lo=Decimal(cfg['exact_log_interval_zero'][0]['decimal_35_digits'])-SLACK
        log1hi=Decimal(cfg['exact_log_interval_one'][1]['decimal_35_digits'])+SLACK
        a=log0lo;b=log1hi
        if direction=='upward':
            m0=fraction(src['robust_mean_e_factor_population_analysis']['upward']['exact_null_mean_upper'])
            m1_upper=fraction(tensor['high_box']['exact_mean_upper_bound'])
            alt='burst p in [.010,.018], measurement p in [.001,.005], gate p in [.002,.004]'
        else:
            m0=fraction(src['robust_mean_e_factor_population_analysis']['downward_on_complement_1_minus_X']['exact_null_mean_upper'])
            # For Y=1-X in the low-burst alternative, sup E[Y] = 1-inf E[X].
            m1_upper=1-fraction(tensor['null_box']['exact_mean_lower_bound'])
            alt='burst p in [0,.002], measurement p in [.001,.005], gate p in [.002,.004]'
        with localcontext() as ctx:
            ctx.prec=70
            factor_upper=1+lam*(m1_upper/m0-1)
            log_mean_upper=ln_fraction(factor_upper)+SLACK
            if not (a < mean_log_lower <= log_mean_upper < b):
                raise AssertionError('log-mean interval not inside support interval')
            midpoint=(a+b)/2
            clipped=min(max(midpoint,mean_log_lower),log_mean_upper)
            # Bhatia-Davis: Var(W|past) <= (b-EW)(EW-a).
            variance_upper=(b-clipped)*(clipped-a)+SLACK
            # Centered W-E[W|past] has absolute value at most this C.
            centered_abs_upper=max(log_mean_upper-a,b-mean_log_lower)+SLACK
        arm={'direction':direction,'lambda':float(lam),'null_mean_upper_m0':float(m0),'alternative_mean_lower_log_mu':str(mean_log_lower),'alternative_mean_upper_log_by_jensen':str(log_mean_upper),'log_increment_support':[str(a),str(b)],'conditional_variance_upper_v':str(variance_upper),'centered_increment_absolute_bound_c':str(centered_abs_upper),'variance_argument':'Bhatia-Davis with conditional mean in [mu,u], where u follows Jensen and the continuous alternative mean upper bound.','alternative_rectangle':alt,'rows':[]}
        for alpha in (Fraction(1,20),Fraction(1,100)):
            for delta in (Fraction(1,10),Fraction(1,20)):
                n=first_n(alpha,delta,mean_log_lower,variance_upper,centered_abs_upper)
                at=freedman_bound(n,alpha,delta,mean_log_lower,variance_upper,centered_abs_upper)
                prev=freedman_bound(n-1,alpha,delta,mean_log_lower,variance_upper,centered_abs_upper) if n>1 else Decimal(1)
                if at>dec_fraction(delta) or prev<=dec_fraction(delta):raise AssertionError('integer threshold check failed')
                arm['rows'].append({'alpha':float(alpha),'delta':float(delta),'sufficient_n':n,'freedman_bound_at_n':str(at),'bound_at_n_minus_1':str(prev)})
        rows.append(arm)
    result={'classification':'CONTINUOUS_EXACT_CIRCUIT_ONE_SIDED_FREEDMAN_CROSSING_BOUNDS_ANALYTIC_NOT_SIMULATED','input_certificate':SOURCE.name,'method':'For W=log L in [a,b], use certified E[W|past]>=mu and Jensen upper E[W|past]<=u. Bhatia-Davis bounds conditional variance by max over m in [mu,u] of (b-m)(m-a); |W-E[W|past]|<=C=max(u-a,b-mu). Freedman lower tail gives P(T>n)<=exp(-(n*mu-A)^2/(2*(n*v+C*(n*mu-A)/3))) for A=log(1/alpha) and n*mu>A.','rounding_slack_decimal':str(SLACK),'arms':rows,'assumptions':['Exact categorical circuit data law and same continuous burst/measurement/gate rectangles as source certificate.','Every sustained-alternative shot has conditional detector law in the declared rectangle given the full previous history.','The process is one fixed directional e-process, with no reset, reversal, state switching, or alpha recycling.','The same m0 and fixed lambda are used throughout; deployment arithmetic must maintain outward-safe probability and log bounds.'],'limitations':['The n values are sufficient distribution-free quantiles, not means or observed delays.','Ville false-alarm control is only for one fixed one-sided process under its certified null.','No repeated-switch control, indifference-band action, approximate-DEM source-law transfer, or decoder benefit is established.','No trajectories, stochastic detector histories, alarms, or decoder evaluations were generated.']}
    OUTPUT.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps([{ 'direction':r['direction'],'variance_upper':r['conditional_variance_upper_v'],'centered_bound':r['centered_increment_absolute_bound_c'],'rows':r['rows']} for r in rows],indent=2))
    print('WROTE',OUTPUT.name)

if __name__=='__main__':main()
