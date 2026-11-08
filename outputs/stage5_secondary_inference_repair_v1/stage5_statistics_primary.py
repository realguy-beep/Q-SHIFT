"""Candidate v3 Stage 5 statistics; root-level only, no sampling side effects."""
from __future__ import annotations
import numpy as np
from scipy.stats import t as student_t

NONZERO=(.004,.008,.012,.016)

def holm(p_values):
    p=np.asarray(p_values,dtype=float); order=np.argsort(p,kind='stable'); out=np.empty_like(p); running=0.0
    for rank,i in enumerate(order):
        running=max(running,(len(p)-rank)*p[i]); out[i]=min(1.0,running)
    return out.tolist()

def one_sample_summary(x):
    x=np.asarray(x,dtype=float)
    if x.ndim!=1 or len(x)<2 or not np.isfinite(x).all(): raise ValueError('root differences must be a finite vector')
    mean=float(x.mean()); s2=float(x.var(ddof=1)); se=float(np.sqrt(s2/len(x)))
    df=float(len(x)-1)
    return mean,se,df

def analyze(groups,cfg,roots):
    g={float(p):np.asarray(v,dtype=float) for p,v in groups.items()}
    if sorted(g)!=[0.0,.004,.008,.012,.016] or any(x.shape!=(roots,) for x in g.values()):
        raise ValueError('candidate v3 requires five conditions and frozen root count')
    means=[]; vars_=[]; condition={}; p_raw=[]
    for p in NONZERO:
        x=g[p]; m,se,df=one_sample_summary(x); means.append(m); vars_.append(float(x.var(ddof=1)))
        t0=m/se if se else (float('-inf') if m<0 else float('inf') if m>0 else 0.0)
        p0=float(student_t.cdf(t0,df)) if se else (0.0 if m<0 else 1.0)
        p_raw.append(p0)
        condition[str(p)]={'root_count':roots,'mean_difference':m,'sample_sd':float(np.sqrt(vars_[-1])),
                           'standard_error':se,'welch_t_reference_p_one_sided_vs_zero':p0,
                           'status':'descriptive secondary; not validated by the primary envelope simulation'}
    delta=float(np.mean(means))
    se=float(np.sqrt(sum(v/roots for v in vars_)/16.0))
    df_denom=sum((v/(16.0*roots))**2/(roots-1) for v in vars_)
    df=float((se*se)**2/df_denom) if df_denom else float('inf')
    boundary=float(cfg['primary_inference']['null_boundary'])
    tstat=(delta-boundary)/se if se else (float('-inf') if delta<boundary else float('inf') if delta>boundary else 0.0)
    ci=cfg['primary_inference']
    upper=delta+float(ci['studentized_cutoff'])*se
    interval=[delta-float(ci['central_lower_cutoff'])*se,delta+float(ci['central_upper_cutoff'])*se]
    # p=0 is a separately required safety endpoint.
    p0m,p0se,_=one_sample_summary(g[0.0])
    p0upper=p0m+float(ci['p0_one_sided_cutoff'])*p0se
    p0bound=float(ci['p0_no_harm_boundary'])
    secondary_holm=holm(p_raw)
    condition_means=list(means)
    result={
      'estimand':'equal-weight mean of four nonzero-condition root-paired adaptive-minus-fixed LER differences',
      'primary_delta':delta,'primary_standard_error':se,'primary_df_reference':df,'primary_t_statistic_at_boundary':tstat,
      'primary_boundary':boundary,'primary_calibrated_critical':float(ci['studentized_cutoff']),
      'primary_one_sided_upper_bound':upper,'primary_central_interval_candidate':interval,
      'primary_calibrated_reject':bool(upper<boundary),'p0_mean_difference':p0m,'p0_standard_error':p0se,
      'p0_upper_bound':p0upper,'p0_no_harm_boundary':p0bound,'p0_no_harm_pass':bool(p0upper<=p0bound),
      'nonzero_condition_means':{str(p):m for p,m in zip(NONZERO,condition_means)},
      'secondary_welch_p_raw_vs_zero_descriptive':p_raw,'secondary_welch_p_holm_descriptive':secondary_holm,
      'secondary_condition_details':condition,
      'overall_candidate_gate':bool(upper<boundary and p0upper<=p0bound and all(m<0 for m in condition_means) and max(condition_means)<=0.0002),
      'inference_scope':'primary calibrated cutoffs are supported only for the finite prespecified root-effect simulation envelope; secondary Welch p-values are descriptive until separately validated',
      'resampling_unit':'independent root; paired shot errors reduced to a root-level difference before inference'}
    return result
