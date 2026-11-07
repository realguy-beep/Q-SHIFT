"""Runner-side Stage 5 inference. Independent audit reimplements these functions."""
import numpy as np

def holm_adjust(p_values):
    p=np.asarray(p_values,float); order=np.argsort(p,kind='stable'); out=np.empty_like(p); running=0.0
    for rank,i in enumerate(order):
        running=max(running,(len(p)-rank)*p[i]); out[i]=min(1.0,running)
    return out.tolist()

def _signflip(x,rng,n):
    x=np.asarray(x,float); obs=abs(float(x.mean())); extreme=0
    for start in range(0,n,5000):
        m=min(5000,n-start); signs=rng.integers(0,2,size=(m,len(x)),dtype=np.int8)*2-1
        extreme+=int(np.count_nonzero(np.abs(signs@x/len(x))>=obs-1e-15))
    return (extreme+1)/(n+1)

def _boot_primary(groups,rng,n):
    condition_means=[]
    for p in sorted(groups):
        x=np.asarray(groups[p],float); ix=rng.integers(0,len(x),size=(n,len(x)))
        condition_means.append(x[ix].mean(axis=1))
    draws=np.mean(condition_means,axis=0)
    return [float(np.quantile(draws,.025)),float(np.quantile(draws,.975))]

def analyze(groups,bootstrap_seed=4240001001,signflip_seed=4240001002,bootstrap_n=20000,signflip_n=100000):
    g={float(p):np.asarray(v,float) for p,v in groups.items()}
    if sorted(g)!=[0.,.004,.008,.012,.016] or any(x.shape!=(100,) or not np.isfinite(x).all() for x in g.values()):
        raise ValueError('expected five frozen conditions and 100 finite root effects per condition')
    ps=[.004,.008,.012,.016]; delta=float(np.mean([g[p].mean() for p in ps]))
    brng=np.random.Generator(np.random.PCG64(bootstrap_seed)); ci=_boot_primary({p:g[p] for p in ps},brng,bootstrap_n)
    ix=brng.integers(0,100,size=(bootstrap_n,100)); zero_upper=float(np.quantile(g[0.][ix].mean(axis=1),.95))
    srng=np.random.Generator(np.random.PCG64(signflip_seed))
    primary=_signflip(np.concatenate([g[p] for p in ps]),srng,signflip_n)
    raw=[_signflip(g[p],srng,signflip_n) for p in ps]
    return {'primary_delta':delta,'primary_bootstrap_95ci':ci,'primary_signflip_p':primary,
      'secondary_signflip_p_raw':raw,'secondary_signflip_p_holm':holm_adjust(raw),
      'zero_burst_one_sided_bootstrap_95_upper':zero_upper,
      'condition_mean_differences':{str(p):float(g[p].mean()) for p in sorted(g)},
      'resampling_unit':'independent root; no shot-level resampling'}
