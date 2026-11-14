"""Exact-circuit continuous second-moment envelope for scalar e-factor logs.
Uses rational parity polynomials and tensor Bernstein bounds; no histories or draws.
"""
from __future__ import annotations
import json, math, sys, time
from fractions import Fraction
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
for directory in (ROOT,ROOT/'outputs'/'phase3a_correlated_noise_preflight',ROOT/'outputs'/'stage4_noise_adaptive_feasibility_v1'):
    if str(directory) not in sys.path: sys.path.insert(0,str(directory))
import categorical_circuit_feature_expectations as features
import cofire_category_continuous_envelope as logs
from simulator import build_spatial_burst_circuit

PAIRS=((8,10),(16,18),(24,26),(32,34),(36,38))
DETECTORS=tuple(sorted({x for pair in PAIRS for x in pair}))
DIMS=('burst_p','measurement_p','gate_p')
SOURCE_CERT=HERE/'EXACT_THREE_PARAMETER_EFACTOR_ENVELOPE.json'
OUT=HERE/'EFACTOR_LOG_SECOND_MOMENT_ENVELOPES.json'


def circuit(params):
    pb,pm,pg=params
    return build_spatial_burst_circuit(memory_basis='z',regime='balanced',distance=3,rounds=5,gate_p=pg,measurement_p=pm,bias_ratio=10.0,burst_probability=pb,burst_pair=(8,10))


def poly_mul(a,b):
    out=[Fraction(0)]*(len(a)+len(b)-1)
    for i,x in enumerate(a):
        for j,y in enumerate(b): out[i+j]+=x*y
    while len(out)>1 and not out[-1]: out.pop()
    return out


def poly_add(a,b,scale=Fraction(1)):
    out=[Fraction(0)]*max(len(a),len(b))
    for i,x in enumerate(a):out[i]+=x
    for i,x in enumerate(b):out[i]+=scale*x
    while len(out)>1 and not out[-1]:out.pop()
    return out


def tri_add(a,b,scale=Fraction(1)):
    out=dict(a)
    for key,v in b.items():
        out[key]=out.get(key,Fraction(0))+scale*v
        if not out[key]:del out[key]
    return out


def tri_mul_dim(poly,dim,factor):
    out={}
    for idx,c in poly.items():
        idx=list(idx)
        for power,v in enumerate(factor):
            if v:
                key=idx.copy();key[dim]+=power;key=tuple(key)
                out[key]=out.get(key,Fraction(0))+c*v
    return {k:v for k,v in out.items() if v}


def support_mask(support):
    return sum(1<<DETECTORS.index(d) for d in support if d in DETECTORS)


def build_characters_and_categories():
    c=circuit((.010,.003,.003)); names=[inst.name for inst in c]
    raw=features.extract_sites(c); mapped,meta=features.categorical_sites(c)
    if len(raw)!=len(mapped):raise RuntimeError('raw/mapped site counts differ')
    # One-variable factors per detector-parity character, with exact intended balanced probabilities.
    chars=[]
    for selected in range(1<<len(DETECTORS)):
        factors=[[Fraction(1)],[Fraction(1)],[Fraction(1)]]
        for raw_site,mapped_site in zip(raw,mapped):
            channel=names[raw_site[0]]
            odd=[]
            for _prob,support,_obs,_pauli in mapped_site[1]:
                sm=support_mask(support)
                if ((sm&selected).bit_count()&1):odd.append(1)
            count=sum(odd)
            if not count:continue
            if channel=='E':dim,denom=0,1
            elif channel in ('X_ERROR','Z_ERROR'):dim,denom=1,1
            elif channel=='PAULI_CHANNEL_1':dim,denom=2,3
            elif channel=='PAULI_CHANNEL_2':dim,denom=2,15
            else:raise RuntimeError(f'unhandled noisy categorical channel {channel}')
            factors[dim]=poly_mul(factors[dim],[Fraction(1),Fraction(-2*count,denom)])
        chars.append(tuple(factors))
    # Moment M[S]=P(all pair-cofire bits in S equal one), by detector parity inversion.
    moments=[]
    for pairmask in range(1<<len(PAIRS)):
        detbits=[]
        for j,pair in enumerate(PAIRS):
            if pairmask>>j&1:
                detbits.extend(DETECTORS.index(d) for d in pair)
        total={}
        for sub in range(1<<len(detbits)):
            charmask=0
            for b,detidx in enumerate(detbits):
                if sub>>b&1:charmask|=1<<detidx
            cpoly={ (i,j,k):a*b*c0 for i,a in enumerate(chars[charmask][0]) for j,b in enumerate(chars[charmask][1]) for k,c0 in enumerate(chars[charmask][2]) if a*b*c0 }
            total=tri_add(total,cpoly,Fraction(-1 if sub.bit_count()&1 else 1))
        moments.append({k:v/Fraction(1<<len(detbits)) for k,v in total.items() if v})
    # Möbius inversion gives exact joint law for the five pair-cofire bits.
    exact_masks=[]
    for mask in range(1<<len(PAIRS)):
        law={}
        for sup in range(1<<len(PAIRS)):
            if (sup&mask)==mask:
                law=tri_add(law,moments[sup],Fraction(-1 if (sup.bit_count()-mask.bit_count())&1 else 1))
        exact_masks.append(law)
    categories=[{} for _ in range(len(PAIRS)+1)]
    for mask,law in enumerate(exact_masks):
        categories[mask.bit_count()]=tri_add(categories[mask.bit_count()],law)
    total={}
    for p in categories:total=tri_add(total,p)
    if total!={(0,0,0):Fraction(1)}:raise RuntimeError('category probabilities fail exact normalization')
    return categories,raw,mapped,names


def bernstein_matrix(n,lo,hi):
    width=hi-lo; mat=[]
    for i in range(n+1):
        row=[]
        for j in range(n+1):
            value=Fraction(0)
            for k in range(min(i,j)+1):
                value += Fraction(math.comb(j,k)*math.comb(i,k),math.comb(n,k))*lo**(j-k)*width**k
            row.append(value)
        mat.append(row)
    return mat


def transform_axis(arr,axis,matrix):
    moved=np.moveaxis(arr,axis,-1); n=moved.shape[-1]-1
    out=np.empty_like(moved)
    for idx in np.ndindex(moved.shape[:-1]):
        for i in range(n+1):
            out[idx+(i,)]=sum((matrix[i][j]*moved[idx+(j,)] for j in range(n+1)),Fraction(0))
    return np.moveaxis(out,-1,axis)


def tensor_bernstein_extrema(poly,box,degrees=(1,8,25),splits=(1,1,1)):
    lo=[Fraction(a) for a,b in box]; hi=[Fraction(b) for a,b in box]
    mins=[]; maxs=[]; cell_extrema=[]
    for i in range(splits[0]):
      for j in range(splits[1]):
       for k in range(splits[2]):
        ix=(i,j,k); cell=[]
        for dim in range(3):
            cell.append((lo[dim]+(hi[dim]-lo[dim])*Fraction(ix[dim],splits[dim]),lo[dim]+(hi[dim]-lo[dim])*Fraction(ix[dim]+1,splits[dim])))
        arr=np.empty(tuple(d+1 for d in degrees),dtype=object);arr.fill(Fraction(0))
        for exp,c in poly.items():arr[exp]+=c
        for axis in range(3):arr=transform_axis(arr,axis,bernstein_matrix(degrees[axis],*cell[axis]))
        vals=list(arr.flat); mn=min(vals);mx=max(vals);mins.append(mn);maxs.append(mx)
        cell_extrema.append({'cell':ix,'min':float(mn),'max':float(mx)})
    return min(mins),max(maxs),cell_extrema


def eval_tri(poly,params):
    return sum((coef*params[0]**i*params[1]**j*params[2]**k for (i,j,k),coef in poly.items()),Fraction(0))


def direct_xor_category(raw,mapped,names,params):
    # Independent deterministic probability-state recursion over 2^10 syndromes.
    dist=np.zeros(1<<len(DETECTORS));dist[0]=1.0
    for r,m in zip(raw,mapped):
        channel=names[r[0]]
        if channel=='E':dim,den=0,1
        elif channel in ('X_ERROR','Z_ERROR'):dim,den=1,1
        elif channel=='PAULI_CHANNEL_1':dim,den=2,3
        elif channel=='PAULI_CHANNEL_2':dim,den=2,15
        else:continue
        p=params[dim];alts=[]
        for _prob,support,_obs,_pauli in m[1]:alts.append((p/den,support_mask(support)))
        identity=1-sum(q for q,_ in alts)
        if identity < -1e-15:raise RuntimeError('invalid categorical identity probability')
        nxt=dist*identity
        states=np.arange(len(dist))
        for q,mask in alts:
            if q:nxt[states^mask]+=dist*q
        dist=nxt
    out=[0.0]*6
    for syndrome,p in enumerate(dist):
        count=0
        for j,(a,b) in enumerate(PAIRS):
            if (syndrome>>DETECTORS.index(a)&1) and (syndrome>>DETECTORS.index(b)&1):count+=1
        out[count]+=p
    return out


def log_square_upper(factor):
    lo,hi=logs.log_rational_interval(factor,terms=28)
    return max(lo*lo,hi*hi)


def make_second_moment_poly(categories,lam,m0,direction):
    poly={}
    for k,cat in enumerate(categories):
        z=Fraction(k,5) if direction=='upward' else Fraction(5-k,5)
        factor=1+lam*(z/m0-1)
        if factor<=0:raise RuntimeError('nonpositive factor endpoint')
        upper=log_square_upper(factor)
        poly=tri_add(poly,cat,upper)
    return poly


def main():
    start=time.perf_counter();cert=json.loads(SOURCE_CERT.read_text(encoding='utf-8-sig'))
    categories,raw,mapped,names=build_characters_and_categories()
    print('CATEGORY_POLYNOMIALS_BUILT', flush=True)
    # Independent 1024-state XOR recursion validation at nominal and two rectangle probes.
    probes=[(Fraction(10,1000),Fraction(3,1000),Fraction(3,1000)),(Fraction(18,1000),Fraction(1,1000),Fraction(2,1000)),(Fraction(0),Fraction(5,1000),Fraction(4,1000))]
    validations=[]
    for point in probes:
        p=[float(x) for x in point];rec=direct_xor_category(raw,mapped,names,p)
        formula=[float(eval_tri(poly,point)) for poly in categories]
        err=max(abs(a-b) for a,b in zip(rec,formula))
        if err>2e-12:raise AssertionError(f'XOR state recursion mismatch {err}')
        validations.append({'parameters':p,'max_abs_category_probability_difference':err})
    print('INDEPENDENT_XOR_VALIDATION_PASSED', flush=True)
    analyses=[]
    opt=cert['robust_mean_e_factor_population_analysis']['endpoint_chord_optimum']
    for direction,boxname in [('upward','high_box'),('downward_on_complement','null_box')]:
        cfg=opt[direction]
        lamrec=cfg['exact_optimal_lambda'];lam=Fraction(int(lamrec['numerator']),int(lamrec['denominator']))
        nullkey='null_box' if direction=='upward' else 'high_box'
        mrec=cert['tensor_bernstein'][nullkey]['exact_mean_upper_bound'];m0=Fraction(int(mrec['numerator']),int(mrec['denominator']))
        poly=make_second_moment_poly(categories,lam,m0,'upward' if direction=='upward' else 'downward')
        if boxname=='high_box':box=((Fraction(10,1000),Fraction(18,1000)),(Fraction(1,1000),Fraction(5,1000)),(Fraction(2,1000),Fraction(4,1000)))
        else:box=((Fraction(0),Fraction(2,1000)),(Fraction(1,1000),Fraction(5,1000)),(Fraction(2,1000),Fraction(4,1000)))
        vlo,vhi,cells=tensor_bernstein_extrema(poly,box,splits=(1,1,1))
        print(f'BERNSTEIN_BOUND_READY {direction}', flush=True)
        # Parse certified drift lower bound as a safely truncated decimal.
        mu=float(cfg['uniform_expected_log_lower_bound_nats_per_shot'])-1e-18
        a=math.log(float(1-lam)); b=math.log(float(1+lam*(1/m0-1)))
        # Downward complement has its own m0; endpoint formulas remain z in [0,1].
        R=(b-a)+1e-12
        v=float(vhi)+1e-14
        analyses.append({'direction':direction,'lambda':float(lam),'m0_null_mean_upper':float(m0),'alternative_rectangle':[[float(a),float(b)] for a,b in box],'certified_mean_log_increment_lower_mu':mu,'uniform_E_log_increment_squared_upper_v':v,'bernstein_degrees':[1,8,25],'bernstein_subdivisions':[2,2,2],'bernstein_log_square_upper_min':float(vlo),'bernstein_log_square_upper_max':float(vhi),'log_increment_interval':[a,b],'absolute_centered_increment_bound_R':R,'cells':cells,'freedman_rows':[]})
        for alpha in (.05,.01):
            for delta in (.10,.05):
                A=math.log(1/alpha);L=math.log(1/delta)
                def bound(n):
                    x=n*mu-A
                    if x<=0:return 1.0
                    return math.exp(-(x*x)/(2*(n*v+R*x/3)))
                lo=1;hi=1
                while bound(hi)>delta:hi*=2
                while lo<hi:
                    mid=(lo+hi)//2
                    if bound(mid)<=delta:hi=mid
                    else:lo=mid+1
                n=lo
                analyses[-1]['freedman_rows'].append({'alpha':alpha,'delta':delta,'sufficient_n':n,'bound_at_n':bound(n),'bound_at_n_minus_1':bound(n-1)})
    result={'classification':'EXACT_CATEGORICAL_CONTINUOUS_BERNSTEIN_SECOND_MOMENT_AND_FREEDMAN_SCREEN','source_certificate':SOURCE_CERT.name,'feature_statistic':'X=number of five designated cofires / 5; downward uses 1-X','exact_category_polynomial_degrees':[1,8,25],'category_count':6,'subsets_in_joint_cofire_law':32,'exact_normalization_verified':True,'independent_validation':'direct 1024-state Bernoulli-XOR probability recursion at 3 deterministic parameter points','validation_probes':validations,'analyses':analyses,'elapsed_wall_seconds':time.perf_counter()-start,'assumptions':['Exact balanced categorical circuit law and full declared three-parameter rectangles.','Conditional shot law at every alternative step remains in the certified rectangle, so conditional mean log drift and second moment bounds apply.','Freedman bound is applied to centered log increments with |D_t| bounded by the log-range width and conditional variance bounded by E[(log L_t)^2].','One fixed directional process only; no repeated switching or reset guarantee.'],'limitations':['Bernstein upper bounds on E[(log L)^2] are deterministic and continuous but may be conservative.','The resulting Freedman timing is a distribution-free sufficient bound, not an expected delay or actual alarm result.','No approximate DEM source-law transfer, detector history, sampling, alarm path, or decoder utility is evaluated.']}
    OUT.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'validations':validations,'arms':[{k:a[k] for k in ('direction','uniform_E_log_increment_squared_upper_v','absolute_centered_increment_bound_R','freedman_rows')} for a in analyses],'elapsed':result['elapsed_wall_seconds']},indent=2))

if __name__=='__main__':main()
