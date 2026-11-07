import json,hashlib,time,sys,csv
from pathlib import Path
import numpy as np,stim,pymatching
P=Path(__file__).resolve().parent; C=json.loads((P/'config.json').read_text()); start=time.perf_counter()
def sha(x):return hashlib.sha256(Path(x).read_bytes()).hexdigest()
freeze=json.loads((P/'STAGE1_FREEZE.json').read_text())
assert all(sha(P/n)==h for n,h in freeze['hashes'].items())
grid=[(g,m) for g in C['grid'] for m in C['grid']]; conditions=list(C['conditions'])
roots={c:[C['roots_start']+100000*j+10000*i for i in range(20)] for j,c in enumerate(conditions)}
seeds=[r+100+ci for ci,c in enumerate(conditions) for r in roots[c]]; assert len(seeds)==len(set(seeds))==60
def circuit(g,m):return stim.Circuit.generated('surface_code:rotated_memory_z',distance=3,rounds=5,after_clifford_depolarization=g,before_measure_flip_probability=m)
models={};meta={}
for pair in grid:
 c=circuit(*pair);assert c.num_detectors==40 and c.num_observables==1
 dem=c.detector_error_model(decompose_errors=True);model=pymatching.Matching.from_detector_error_model(dem);assert model.num_detectors==40
 models[pair]=(c,model);meta[str(pair)]={'edges':model.num_edges,'circuit_sha256':hashlib.sha256(str(c).encode()).hexdigest(),'dem_sha256':hashlib.sha256(str(dem).encode()).hexdigest()}
ideal=circuit(0,0);d,y=ideal.compile_detector_sampler(seed=74000000).sample(shots=128,separate_observables=True);assert not d.any() and not y.any()
for c,pars in C['conditions'].items():
 q=circuit(*pars); names=[x.name for x in q.flattened()];assert 'DEPOLARIZE1' in names and 'DEPOLARIZE2' in names and ('X_ERROR' in names or 'Z_ERROR' in names)
diag={}
for pair,(c,m) in models.items():
 ds,ys=c.compile_detector_sampler(seed=74100000+grid.index(pair)).sample(shots=100,separate_observables=True);pred=m.decode_batch(ds);assert pred.shape==ys.shape
 diag[str(pair)]={'detectors':ds.shape[1],'observable':ys.shape[1],'prediction_shape':list(pred.shape)}
(P/'PHASE4C_STAGE1_VALIDATION.md').write_text('# Stage 1 validation\n\nFrozen hashes pass. All nine DEMs build with 40 detectors/one observable. Native gate depolarization and measurement flips present; ideal 128-shot sample is zero. 9 deterministic 100-shot diagnostics produce valid paired prediction shapes. Derived 60 development seeds are unique. Actual historical collision screening is incomplete: frozen file contains no historical seed inventory; explicit Phase4A/B roots are disjoint.\n\n'+json.dumps({'models':meta,'diagnostics':diag,'seeds':seeds},indent=2)+'\n')
rows=[];raw=P/'development_raw';raw.mkdir(exist_ok=True)
for ci,name in enumerate(conditions):
 gen=tuple(C['conditions'][name])
 for root in roots[name]:
  seed=root+100+ci;det,obs=circuit(*gen).compile_detector_sampler(seed=seed).sample(shots=C['shots_per_root'],separate_observables=True);obs=obs[:,0].astype(bool)
  preds=np.asarray([models[p][1].decode_batch(det)[:,0].astype(bool) for p in grid]);res=preds^obs
  rec={'condition':name,'root':root,'seed':seed,'shots':len(obs),'raw':int(obs.sum()),'errors':res.sum(axis=1).astype(int).tolist()};rows.append(rec)
  np.savez_compressed(raw/f'{name}_{root}.npz',detectors=np.packbits(det,axis=1,bitorder='little'),detector_count=np.array(det.shape[1]),observable=obs,predictions=preds)
  if len(rows)%10==0:print('completed',len(rows),'/',60,flush=True)
rates={c:[sum(x['errors'][i] for x in rows if x['condition']==c)/(20*C['shots_per_root']) for i in range(9)] for c in conditions}
pooled=[sum(rates[c][i] for c in conditions)/3 for i in range(9)];worst=[max(rates[c][i] for c in conditions) for i in range(9)]
order=lambda i:(pooled[i],worst[i],grid[i]);pidx=min(range(9),key=order);midx=min(range(9),key=lambda i:(worst[i],pooled[i],grid[i]))
oracle={c:min(range(9),key=lambda i:(rates[c][i],pooled[i],worst[i],grid[i])) for c in conditions}
out={'conditions':conditions,'grid':grid,'rates':rates,'pooled_objective':pooled,'worst_objective':worst,'pooled_index':pidx,'minimax_index':midx,'oracle_indices':oracle,'rows':rows,'shots':len(rows)*C['shots_per_root'],'runtime_seconds':time.perf_counter()-start,'metadata':meta,'diagnostic':diag}
(P/'DEVELOPMENT_RESULTS.json').write_text(json.dumps(out,indent=2)+'\n')
with (P/'DEVELOPMENT_PER_SEED.csv').open('w',newline='') as f:w=csv.writer(f);w.writerow(['condition','root','seed','shots','raw']+[str(x) for x in grid]);[w.writerow([x['condition'],x['root'],x['seed'],x['shots'],x['raw']]+x['errors']) for x in rows]
with (P/'DEVELOPMENT_CANDIDATE_MATRIX.csv').open('w',newline='') as f:w=csv.writer(f);w.writerow(['condition']+[str(x) for x in grid]);[w.writerow([c]+rates[c]) for c in conditions]
sel={'pooled_fixed':grid[pidx],'minimax_fixed':grid[midx],'condition_specific':{c:grid[i] for c,i in oracle.items()},'development_hash':sha(P/'DEVELOPMENT_RESULTS.json'),'stage2_test_generated':False}
(P/'PHASE4C_BASELINE_FREEZE.json').write_text(json.dumps(sel,indent=2)+'\n')
for name,content in {'PHASE4C_DEVELOPMENT_RESULTS.md':'# Development results\n\n'+json.dumps(rates,indent=2),'PHASE4C_BASELINE_SELECTION.md':'# Baseline selection\n\n'+json.dumps(sel,indent=2),'PHASE4C_STAGE1_INTERPRETATION.md':'# Interpretation\n\nDevelopment-selected baselines are descriptive selections; close development rates do not establish unique superiority. No held-out test evidence yet.','PHASE4C_STAGE2_FROZEN_PLAN.md':'# Stage 2 plan frozen\n\n20 roots/regime, 30k paired test shots/root; fresh detector calibration. Equal-regime calibrated-minus-pooled endpoint, two-sided .05; stratified seed bootstrap; Holm secondary comparisons. Stage 2 not executed.','PHASE4C_STAGE1_REPRODUCIBILITY.md':'Run `python outputs/phase4c_strong_baselines/run_stage1.py`. Requires Stim, PyMatching, NumPy. Stage 1 only.'}.items():(P/name).write_text(content+'\n')
print('DONE',out['shots'],sel,flush=True)
