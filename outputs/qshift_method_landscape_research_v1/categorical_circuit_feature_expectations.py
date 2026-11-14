"""Exact detector-feature expectations for the categorical Q-SHIFT circuit.

No stochastic sampler is called. Stim's deterministic reference_sample is used
on a fault-injected Clifford circuit to map each single Pauli alternative to
its detector/observable support; independent categorical channel probabilities
are then combined algebraically. This is a circuit-level population calculation,
not a DEM expectation or sampled estimate.
"""
from __future__ import annotations
import json, sys, time
from pathlib import Path
import numpy as np
import stim
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
for p in (ROOT,ROOT/'outputs'/'phase3a_correlated_noise_preflight',ROOT/'outputs'/'stage4_noise_adaptive_feasibility_v1'):
 if str(p) not in sys.path: sys.path.insert(0,str(p))
from simulator import build_spatial_burst_circuit
from prototype import BURST_DETECTOR_PAIRS, DETECTOR_COUNT
from outputs.qshift_method_landscape_research_v1.dem_feature_expectations import build_dem, feature_means

PAULI1=('X','Y','Z')
PAULI2=('IX','IY','IZ','XI','XX','XY','XZ','YI','YX','YY','YZ','ZI','ZX','ZY','ZZ')

def pauli_targets(inst, qs):
 out=[]
 for t in inst.targets_copy():
  ch='X' if t.is_x_target else 'Y' if t.is_y_target else 'Z' if t.is_z_target else None
  if ch is None: raise ValueError(f'unsupported correlated Pauli target in {inst}')
  out.append((int(t.value),ch))
 return tuple(out)

def extract_sites(circuit):
 sites=[]; supported={'PAULI_CHANNEL_1','PAULI_CHANNEL_2','X_ERROR','E'}
 for ix,inst in enumerate(circuit):
  name=inst.name; args=tuple(map(float,inst.gate_args_copy())); targets=inst.targets_copy()
  if name=='PAULI_CHANNEL_1':
   if len(args)!=3: raise ValueError('unexpected PAULI_CHANNEL_1 arity')
   for t in targets:
    q=int(t.value); alts=[(args[k],((q,p),)) for k,p in enumerate(PAULI1)]
    sites.append((ix,1-sum(args),alts))
  elif name=='PAULI_CHANNEL_2':
   if len(args)!=15 or len(targets)%2: raise ValueError('unexpected PAULI_CHANNEL_2 shape')
   for start in range(0,len(targets),2):
    q0,q1=int(targets[start].value),int(targets[start+1].value)
    alts=[(args[k],tuple((q,ch) for q,ch in zip((q0,q1),pair) if ch!='I')) for k,pair in enumerate(PAULI2)]
    sites.append((ix,1-sum(args),alts))
  elif name=='X_ERROR':
   if len(args)!=1: raise ValueError('unexpected X_ERROR arity')
   for t in targets: sites.append((ix,1-args[0],[(args[0],((int(t.value),'X'),))]))
  elif name=='E':
   if len(args)!=1: raise ValueError('unexpected E arity')
   sites.append((ix,1-args[0],[(args[0],pauli_targets(inst,None))]))
  elif ('ERROR' in name or 'CHANNEL' in name or name.startswith('DEPOLARIZE')) and name not in supported:
   raise ValueError(f'unsupported noise operation {name}')
 return sites

def detector_support(circuit, converter, baseline_det, baseline_obs, instruction_index, paulis):
 out=stim.Circuit()
 for ix,inst in enumerate(circuit):
  out.append(inst)
  if ix==instruction_index:
   for q,p in paulis: out.append(p,[q])
 meas=out.reference_sample().reshape(1,-1)
 det,obs=converter.convert(measurements=meas,separate_observables=True)
 ds=np.bitwise_xor(baseline_det[0],det[0]); os=np.bitwise_xor(baseline_obs[0],obs[0])
 return frozenset(map(int,np.flatnonzero(ds))),tuple(map(int,os))

def categorical_sites(circuit):
 converter=circuit.compile_m2d_converter()
 baseline=circuit.reference_sample().reshape(1,-1)
 bd,bo=converter.convert(measurements=baseline,separate_observables=True)
 if np.any(bd) or np.any(bo): raise RuntimeError('noiseless reference has nonzero detector/observable outputs')
 raw=extract_sites(circuit); result=[]; calls=0; burst_supports=[]
 for instruction_index,q_identity,alts in raw:
  mapped=[]
  for probability,paulis in alts:
   if not paulis or probability==0: continue
   support,obs=detector_support(circuit,converter,bd,bo,instruction_index,paulis)
   mapped.append((float(probability),support,obs,paulis)); calls+=1
   if calls>3000: raise RuntimeError('deterministic fault-map work cap exceeded')
  if circuit[instruction_index].name=='E':
   if len(mapped)!=1: raise RuntimeError('each burst site must map to one Pauli alternative')
   burst_supports.append(tuple(sorted(mapped[0][1])))
  result.append((float(q_identity),mapped))
 expected=[(8,10),(16,18),(24,26),(32,34),(36,38)]
 if burst_supports!=expected: raise RuntimeError(f'burst detector supports differ: {burst_supports}')
 return result,{'physical_sites':len(raw),'fault_alternatives_mapped':calls,'burst_detector_supports':[list(v) for v in burst_supports],'baseline_reference_detector_weight':int(np.count_nonzero(bd)),'baseline_reference_observable_weight':int(np.count_nonzero(bo))}

def feature_supports():
 return [(i,) for i in range(DETECTOR_COUNT)]+[tuple(pair) for pair in BURST_DETECTOR_PAIRS]

def means_from_characters(sites):
 supports=feature_supports(); chars={}
 for selected in supports:
  value=1.0
  for qid,alts in sites:
   factor=1.0
   for p,support,_,_ in alts:
    if len(set(selected).intersection(support))%2: factor-=2*p
   value*=factor
  chars[selected]=value
 detector_chars=np.array([chars[(i,)] for i in range(DETECTOR_COUNT)])
 detector=(1-detector_chars)/2
 pairs=[]
 for a,b in BURST_DETECTOR_PAIRS:
  pairs.append((1-detector_chars[a]-detector_chars[b]+chars[(a,b)])/4)
 return np.concatenate([detector,np.asarray(pairs)])

def direct_xor(site_categories, selected):
 n=len(selected); states=1<<n; probs=np.zeros(states); probs[0]=1
 bit={d:i for i,d in enumerate(selected)}
 for qid,alts in site_categories:
  transitions=[(qid,0)]
  for p,support,_,_ in alts:
   mask=0
   for d in support:
    if d in bit: mask ^= 1<<bit[d]
   transitions.append((p,mask))
  nxt=np.zeros_like(probs)
  for p,mask in transitions: nxt += p*probs[np.arange(states)^mask]
  probs=nxt
 return probs

def means_by_direct_xor(sites):
 det=[]
 for d in range(DETECTOR_COUNT): det.append(direct_xor(sites,(d,))[1])
 pairs=[]
 for a,b in BURST_DETECTOR_PAIRS: pairs.append(direct_xor(sites,(a,b))[3])
 return np.concatenate([np.asarray(det),np.asarray(pairs)])

def main():
 start=time.perf_counter()
 circuit=build_spatial_burst_circuit(memory_basis='z',regime='balanced',distance=3,rounds=5,gate_p=.003,measurement_p=.003,bias_ratio=10.,burst_probability=.01,burst_pair=(8,10))
 sites,stats=categorical_sites(circuit); exact=means_from_characters(sites); direct=means_by_direct_xor(sites)
 if exact.shape!=(45,) or not np.isfinite(exact).all() or np.max(np.abs(exact-direct))>2e-12: raise RuntimeError('exact categorical feature algebra cross-check failed')
 _,dem_mechanisms=build_dem(.01,.003); dem=feature_means(dem_mechanisms)
 result={'classification':'EXACT_CATEGORICAL_CIRCUIT_POPULATION_FEATURE_EXPECTATIONS','configuration':{'memory_basis':'z','regime':'balanced','distance':3,'rounds':5,'gate_p':.003,'measurement_p':.003,'bias_ratio':10.,'burst_probability':.01,'burst_pair':[8,10],'stim_version':stim.__version__},'feature_count':45,'exact_categorical_circuit_feature_means':exact.tolist(),'independent_direct_xor_feature_means':direct.tolist(),'max_abs_algebra_crosscheck_error':float(np.max(np.abs(exact-direct))),'approximate_dem_feature_means_same_parameter_point':dem.tolist(),'approximate_dem_minus_exact_circuit_mean':(dem-exact).tolist(),'max_abs_dem_approximation_feature_mean_error':float(np.max(np.abs(dem-exact))),'fault_mapping':stats,'approximation_and_scope':['Exactness is for the existing ideal Clifford circuit with its independent categorical Pauli channels, readout X_ERROR sites and independent per-boundary E burst sites.','Each fault alternative is propagated deterministically by inserting that Pauli into a noiseless circuit reference calculation; no stochastic sample is generated.','Independent channel outcome probabilities are combined by exact categorical parity-characteristic products and independently checked by direct XOR recursion.','The comparison DEM uses Stim decompose_errors=True and approximate_disjoint_errors=True; its means are exact for that approximate DEM, not the original circuit.','No detector histories, decoder outputs, logical error rates, protected data, or seeds are used.'],'resource':{'deterministic_reference_fault_calls':stats['fault_alternatives_mapped'],'elapsed_wall_seconds':time.perf_counter()-start},'sampling_calls':0,'decoder_calls':0}
 path=HERE/'CATEGORICAL_CIRCUIT_FEATURE_EXPECTATIONS.json'; path.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({'output':path.relative_to(ROOT).as_posix(),'physical_sites':stats['physical_sites'],'fault_alternatives':stats['fault_alternatives_mapped'],'direct_xor_max_error':result['max_abs_algebra_crosscheck_error'],'approx_dem_max_mean_error':result['max_abs_dem_approximation_feature_mean_error'],'elapsed_seconds':result['resource']['elapsed_wall_seconds']},indent=2))
if __name__=='__main__': main()
