import json,hashlib,platform,time
from pathlib import Path
import numpy as np,stim,pymatching
from decoder_bank import GRID,build_bank
from schedules import REGIMES,schedule
P=Path(__file__).resolve().parent;cfg=json.loads((P/'phase5e_config.json').read_text());models=build_bank();names=list(REGIMES);pairs=list(GRID);started=time.perf_counter()
def circ(reg):
 g,m=REGIMES[reg];return stim.Circuit.generated('surface_code:rotated_memory_z',distance=3,rounds=5,after_clifford_depolarization=g,before_measure_flip_probability=m)
def sample(reg,seed,n):return circ(reg).compile_detector_sampler(seed=seed).sample(shots=n,separate_observables=True)
def preds(d):return np.array([m.decode_batch(d)[:,0].astype(bool) for m in models])
# Graph and DEM structural audit, especially pairs previously reported as identical.
graphs=[]
for i,(g,m) in enumerate(pairs):
 c=stim.Circuit.generated('surface_code:rotated_memory_z',distance=3,rounds=5,after_clifford_depolarization=g,before_measure_flip_probability=m);dem=c.detector_error_model(decompose_errors=True);model=models[i]
 edges=sorted(((-1 if a is None else a),(-1 if b is None else b),round(attr['weight'],12)) for a,b,attr in model.edges())
 graphs.append({'id':i,'params':[g,m],'dem_sha256':hashlib.sha256(str(dem).encode()).hexdigest(),'edge_count':model.num_edges,'edge_signature_sha256':hashlib.sha256(repr(edges).encode()).hexdigest(),'edges':edges})
dis_by_reg={};eval_by_reg={};seed_log=[]
for ri,reg in enumerate(names):
 dm=np.zeros((9,9),dtype=np.int64);ec=np.zeros(9,dtype=np.int64);n=0
 for rep in range(6):
  d,y=sample(reg,112000001+ri*1000+rep,5000);pr=preds(d);n+=len(y)
  for i in range(9):ec[i]+=np.count_nonzero(pr[i]^y[:,0]);
  for i in range(9):
   for j in range(9):dm[i,j]+=np.count_nonzero(pr[i]!=pr[j])
  seed_log.append({'kind':'pairwise','regime':reg,'seed':112000001+ri*1000+rep,'shots':len(y),'detector_hash':hashlib.sha256(d.tobytes()).hexdigest()})
 dis_by_reg[reg]={'shots':n,'disagreements':dm.tolist(),'errors':ec.tolist(),'rates':(ec/n).tolist(),'symmetric':bool(np.array_equal(dm,dm.T)),'diagonal_zero':bool(np.all(np.diag(dm)==0))}
# Calibration selection by independent roots; selection accuracy/stability tracked.
cal_rates={r:[] for r in names}
for ri,r in enumerate(names):
 for rep in range(3):
  d,y=sample(r,111000001+ri*1000+rep,5000);pr=preds(d);cal_rates[r].append(np.mean(pr^y[:,0],axis=1).tolist())
cal_mean={r:np.mean(v,axis=0) for r,v in cal_rates.items()};best={r:int(np.argmin(cal_mean[r])) for r in names};global_best=int(np.argmin(np.mean(np.array([cal_mean[r] for r in names]),axis=0)))
stationary={r:{'shots':0,'errors':np.zeros(9,dtype=int).tolist(),'roots':[]} for r in names}
for ri,r in enumerate(names):
 for rep in range(3):
  d,y=sample(r,112500001+ri*1000+rep,10000);pr=preds(d);e=np.count_nonzero(pr^y[:,0],axis=1);z=stationary[r];z['shots']+=len(y);z['errors']=(np.array(z['errors'])+e).tolist();z['roots'].append({'seed':112500001+ri*1000+rep,'errors':e.tolist()})
 z['rates']=(np.array(z['errors'])/z['shots']).tolist();z['cal_selected_index']=best[r]
dynamic={};kinds=['stationary','slow','rapid','random']
for ki,kind in enumerate(kinds):
 reps=[]
 for rep in range(3):
  seq=schedule(kind,113000001+ki*10+rep,blocks=12,dwell=256);blocks=[]
  for bi,state in enumerate(seq):
   d,y=sample(state,114000001+ki*1000+rep*100+bi,256);blocks.append((state,d,y[:,0].astype(bool)))
  totals={x:0 for x in ['pooled_fixed','best_global_fixed','calibrated_regime_policy','regime_matched','hindsight_diagnostic','adaptive_ml','adaptive_utility']};roots_detail=[];last=None;pending=0;current=1;sw=0;mlest=[];chosen=[]
  for bi,(state,d,y) in enumerate(blocks):
   pp=preds(d);state_i=names.index(state);ml_idx=int(np.argmin(pp.shape)) if False else best[state]
   # Causal ML uses only immediately previous detector batch, template likelihood; first block pooled.
   if last is not None:
    k=last.sum(0);prof=np.array(json.loads((P/'profiles.json').read_text()));ll=(k*np.log(prof)+(len(last)-k)*np.log1p(-prof)).sum(1);est_grid=int(ll.argmax());est_reg=int([0,1,2][[0,4,2].index(est_grid)]) if est_grid in [0,4,2] else int(np.argmin([abs(est_grid-6),abs(est_grid-4),abs(est_grid-2)]));mlest.append(est_reg)
    target=best[names[est_reg]];pending=pending+1 if target==current else 1
    if target==current:pending=0
    if pending>=2: current=target;sw+=1;pending=0
   else: est_reg=None
   ad=current if last is not None else 1; chosen.append(ad)
   picks={'pooled_fixed':1,'best_global_fixed':global_best,'calibrated_regime_policy':best[state],'regime_matched':{'data_heavy':6,'nominal':4,'measurement_heavy':2}[state],'hindsight_diagnostic':int(np.argmin(np.count_nonzero(pp^y,axis=1))),'adaptive_ml':ad,'adaptive_utility':ad}
   for nm,idx in picks.items():totals[nm]+=int(np.count_nonzero(pp[idx]^y))
   roots_detail.append({'block':bi,'regime':state,'estimate':est_reg,'choice':ad,'errors':{nm:int(np.count_nonzero(pp[idx]^y)) for nm,idx in picks.items()}});last=d
  reps.append({'schedule':seq,'totals':totals,'shots':len(seq)*256,'switches':sw,'block_results':roots_detail})
 dynamic[kind]=reps
out={'software':{'python':platform.python_version(),'stim':stim.__version__,'pymatching':pymatching.__version__,'numpy':np.__version__},'config':cfg,'grid':pairs,'graph_audit':graphs,'regime_disagreement':dis_by_reg,'calibration_replicates':cal_rates,'calibration_mean_errors':{r:cal_mean[r].tolist() for r in names},'selected_per_regime':best,'global_best':global_best,'stationary_evaluation':stationary,'dynamic':dynamic,'seed_log':seed_log,'runtime_seconds':time.perf_counter()-started,'confirmatory':False}
(P/'PHASE5E_RESULTS.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'best':best,'global':global_best,'disagreements':{r:x['disagreements'] for r,x in dis_by_reg.items()},'runtime':out['runtime_seconds']}))
