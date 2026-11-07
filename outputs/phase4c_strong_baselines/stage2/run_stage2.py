import json,hashlib,time,csv,sys,os
from pathlib import Path
import numpy as np,stim,pymatching
from scipy.stats import binomtest
try:
 import psutil
 _proc=psutil.Process(); peak_bytes=None
except Exception:
 _proc=None; peak_bytes=None
P=Path(__file__).resolve().parent; B=P.parent; C=json.loads((B/'config.json').read_text()); CONDITIONS=list(C['conditions']); GRID=[(g,m) for g in C['grid'] for m in C['grid']]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
if _proc:
 try: peak_bytes=_proc.memory_info().rss
 except Exception: _proc=None;peak_bytes=None
t0=time.perf_counter();timing={'sampling':0.,'decode':0.}; rows=[];selections=[];raw=P/'raw';raw.mkdir(exist_ok=True)
def circ(g,m):return stim.Circuit.generated('surface_code:rotated_memory_z',distance=3,rounds=5,after_clifford_depolarization=g,before_measure_flip_probability=m)
def get(c,n,s):
 t=time.perf_counter();d,y=c.compile_detector_sampler(seed=int(s)).sample(shots=n,separate_observables=True);timing['sampling']+=time.perf_counter()-t;return d,y[:,0].astype(bool)
def dec(m,d):
 t=time.perf_counter();x=m.decode_batch(d)[:,0].astype(bool);timing['decode']+=time.perf_counter()-t;return x
def savecp(path,obj):
 tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(obj,indent=2)+'\n');os.replace(tmp,path)
models={};circuits={};metadata={}
for pair in GRID:
 c=circ(*pair);dem=c.detector_error_model(decompose_errors=True);m=pymatching.Matching.from_detector_error_model(dem);assert c.num_detectors==40 and c.num_observables==1 and m.num_detectors==40
 circuits[pair]=c;models[pair]=m
nom=models[(.003,.003)];pool=models[(.001,.003)];mini=models[(.006,.003)];spec={k:models[tuple(v)] for k,v in json.loads((B/'PHASE4C_BASELINE_FREEZE.json').read_text())['condition_specific'].items()}
profiles=[]
for i,pair in enumerate(GRID):
 d,y=get(circuits[pair],50000,83000001+i);profiles.append((d.sum(0)+.5)/(len(d)+1));np.savez_compressed(raw/f'template_{i}.npz',detectors=np.packbits(d,axis=1,bitorder='little'),observable=y)
profiles=np.asarray(profiles)
roots={c:[72000001+10000*(20*j+i) for i in range(20)] for j,c in enumerate(CONDITIONS)}
assert len({r for rr in roots.values() for r in rr})==60
for ci,name in enumerate(CONDITIONS):
 g,m=C['conditions'][name];true=tuple([g,m])
 for root in roots[name]:
  cp=raw/f'{name}_{root}.npz'
  if cp.exists():
   try:
    with np.load(cp,allow_pickle=False) as z:
     d=np.unpackbits(z['detectors'],axis=1,bitorder='little')[:,:40];y=z['observable'];pred=z['predictions'];choice=int(z['choice'])
     assert d.shape==(30000,40) and y.shape==(30000,) and pred.shape==(5,30000) and choice in range(9)
     assert int(z['detector_count'])==40 and np.isin(d,[0,1]).all() and np.isin(y,[0,1]).all() and np.isin(pred,[0,1]).all()
     assert np.array_equal(pred[0],models[GRID[choice]][1].decode_batch(d)[:,0].astype(bool))
   except Exception:
    cp.rename(cp.with_suffix('.npz.quarantined'))
    continue
   selections.append({'condition':name,'root':root,'choice':GRID[choice],'resumed_checkpoint':True})
  else:
   dc,yc=get(circuits[true],20000,root+100+ci);counts=dc.sum(0);scores=(counts*np.log(profiles)+(len(dc)-counts)*np.log1p(-profiles)).sum(1);choice=int(np.argmax(scores));selections.append({'condition':name,'root':root,'choice':GRID[choice],'scores':scores.tolist()})
   dv,yv=get(circuits[true],10000,root+200+ci);pv=dec(models[GRID[choice]],dv); # diagnostic validation only
   d,y=get(circuits[true],30000,root+300+ci); decs=[models[GRID[choice]],pool,nom,mini,spec[name]];pred=np.array([dec(x,d) for x in decs]);
   tmp=cp.with_suffix('.npz.tmp');np.savez_compressed(tmp,detectors=np.packbits(d,axis=1,bitorder='little'),detector_count=np.array(40),observable=y,predictions=pred,choice=np.array(choice),validation_prediction=pv);os.replace(str(tmp)+'.npz',cp)
  residual=pred^y; fixed=residual[1]
  row={'condition':name,'root':root,'shots':len(y),'raw':int(y.sum()),'errors':[int(x.sum()) for x in residual],'candidate_only':[int(np.count_nonzero(x&~fixed)) for x in residual],'fixed_only':[int(np.count_nonzero(~x&fixed)) for x in residual],'disagreements':[int(np.count_nonzero(pred[i]!=pred[1])) for i in range(5)]};rows.append(row)
  savecp(P/'ROOT_CHECKPOINT.json',{'completed_roots':len(rows),'last':row,'selections':selections})
  print('root',len(rows),'/60',flush=True)
  if _proc:
   try: peak_bytes=max(peak_bytes or 0,_proc.memory_info().rss)
   except Exception: _proc=None;peak_bytes=None
matrix={c:[sum(r['errors'][j] for r in rows if r['condition']==c) for j in range(5)] for c in CONDITIONS};agg={'conditions':CONDITIONS,'decoder_order':['calibrated','pooled','nominal','minimax','condition_specific'],'shots_per_regime':600000,'errors':matrix,'per_root':rows,'calibration_selections':selections,'timing':timing,'wall_seconds':time.perf_counter()-t0,'peak_bytes':peak_bytes}
(P/'STAGE2_RESULTS.json').write_text(json.dumps(agg,indent=2)+'\n')
with (P/'STAGE2_PER_ROOT.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
print('COMPLETE',matrix,flush=True)
