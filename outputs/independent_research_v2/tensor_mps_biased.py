"""Exact qecsim planar MPS vs MWPM under matched biased code-capacity noise."""
from __future__ import annotations
import json,math,time,platform,resource,hashlib
from pathlib import Path
import numpy as np,qecsim,qecsim.paulitools as pt
from scipy.stats import binomtest,t
from qecsim.models.generic import BiasedDepolarizingErrorModel
from qecsim.models.planar import PlanarCode,PlanarMPSDecoder,PlanarMWPMDecoder
HERE=Path(__file__).resolve().parent;P=.05;BIAS=10.;AXES=('X','Z');PRE=(2026122701,2026122702);MAIN=(2026122711,2026122712);PRE_N=100;SHOTS=20_000;CAP=300.
def wilson(k,n):
 z=1.959963984540054;p=k/n;d=1+z*z/n;c=(p+z*z/(2*n))/d;h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d;return [c-h,c+h]
def run(axis,n,seed):
 code=PlanarCode(3,3);noise=BiasedDepolarizingErrorModel(BIAS,axis=axis);rng=np.random.default_rng(seed)
 dec={'mwpm':PlanarMWPMDecoder(),'mps_exact':PlanarMPSDecoder(chi=None,mode='c')};fails={k:0 for k in dec};only={'mwpm':0,'mps_exact':0};diff=np.empty(n,np.int8);times={k:0. for k in dec}
 for i in range(n):
  err=noise.generate(code,P,rng);syn=pt.bsp(err,code.stabilizers.T);out={}
  for name,d in dec.items():
   t0=time.perf_counter();rec=d.decode(code,syn,error_model=noise,error_probability=P);times[name]+=time.perf_counter()-t0
   residual=np.bitwise_xor(err,rec)
   if np.any(pt.bsp(residual,code.stabilizers.T)):raise RuntimeError(f'{name} invalid syndrome recovery on {axis} shot {i}')
   out[name]=bool(np.any(pt.bsp(residual,code.logicals.T)));fails[name]+=out[name]
  only['mwpm']+=out['mwpm'] and not out['mps_exact'];only['mps_exact']+=out['mps_exact'] and not out['mwpm'];diff[i]=int(out['mps_exact'])-int(out['mwpm'])
 delta=float(diff.mean());se=float(diff.std(ddof=1)/math.sqrt(n));crit=float(t.ppf(.975,n-1))
 discord=only['mwpm']+only['mps_exact']
 return {'axis':axis,'distance':3,'shots':n,'seed':seed,'code_shape':code.n_k_d,'noise_model':str(noise),'p':P,'bias':BIAS,'failures':fails,'ler':{k:fails[k]/n for k in fails},'wilson_95':{k:wilson(fails[k],n) for k in fails},'paired_mps_minus_mwpm':delta,'paired_normal_95':[delta-crit*se,delta+crit*se],'mwpm_only':int(only['mwpm']),'mps_only':int(only['mps_exact']),'mcnemar_exact_two_sided':float(binomtest(only['mwpm'],discord,.5).pvalue) if discord else 1.,'decode_seconds':times,'seconds_per_decode':{k:v/n for k,v in times.items()}}
def main():
 start=time.perf_counter();pre=[]
 for a,s in zip(AXES,PRE,strict=True):pre.append(run(a,PRE_N,s))
 projected=sum((r['decode_seconds']['mwpm']+r['decode_seconds']['mps_exact'])*SHOTS/PRE_N for r in pre)
 if projected>CAP:raise RuntimeError(f'projected main decoding {projected:.1f}s exceeds cap')
 rows=[run(a,SHOTS,s) for a,s in zip(AXES,MAIN,strict=True)]
 base=float(np.mean([r['ler']['mwpm'] for r in rows]));cand=float(np.mean([r['ler']['mps_exact'] for r in rows]));red=1-cand/base;per=[1-r['ler']['mps_exact']/r['ler']['mwpm'] for r in rows];elapsed=time.perf_counter()-start;runtime=sum(sum(r['decode_seconds'].values()) for r in rows)
 out={'status':'completed','qecsim_version':qecsim.__version__,'preflight':pre,'conditions':rows,'macro_ler':{'mwpm':base,'exact_mps':cand},'macro_relative_reduction':red,'per_axis_relative_reductions':per,'mean_decode_seconds_per_shot':{k:float(np.mean([r['seconds_per_decode'][k] for r in rows])) for k in ('mwpm','mps_exact')},'total_main_decode_seconds':runtime,'projected_main_decode_seconds':projected,'advancement_gate_passed':red>=.10 and min(per)>=-.05 and runtime<300,'preflight_samples_per_axis':PRE_N,'main_samples_per_axis':SHOTS,'qshift_circuit_samples':0,'elapsed_seconds':elapsed,'peak_rss_kib':int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),'software_versions':{'python':platform.python_version(),'numpy':np.__version__},'scope':'d3 ideal-syndrome code-capacity IID biased depolarizing noise; not Q-SHIFT circuit-level'}
 (HERE/'tensor_mps_biased_results.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'macro_ler':out['macro_ler'],'reduction':red,'per_axis':per,'runtime':runtime,'gate':out['advancement_gate_passed'],'elapsed':elapsed},indent=2))
if __name__=='__main__':main()
