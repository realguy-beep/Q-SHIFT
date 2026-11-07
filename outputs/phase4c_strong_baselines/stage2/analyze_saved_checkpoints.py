import json,hashlib,csv
from pathlib import Path
import numpy as np,stim,pymatching
from scipy.stats import binomtest
P=Path(__file__).resolve().parent;RAW=P/'raw'; conditions=['data_heavy','nominal','measurement_heavy']; grid=[(g,m) for g in [.001,.003,.006] for m in [.001,.003,.006]]
sel=json.loads((P.parent/'PHASE4C_BASELINE_FREEZE.json').read_text()); pooled=tuple(sel['pooled_fixed']);nom=(.003,.003);mini=tuple(sel['minimax_fixed']);spec={k:tuple(v) for k,v in sel['condition_specific'].items()}
models={}
for pair in set(grid):
 c=stim.Circuit.generated('surface_code:rotated_memory_z',distance=3,rounds=5,after_clifford_depolarization=pair[0],before_measure_flip_probability=pair[1]);models[pair]=pymatching.Matching.from_detector_error_model(c.detector_error_model(decompose_errors=True))
files=sorted(list(RAW.glob('*.npz'))+list(RAW.glob('*.npz.quarantined'))); rows=[]; audit=[]
for f in files:
 cond=next((c for c in conditions if f.name.startswith(c+'_')),None)
 if cond is None: continue
 root=int(f.name[len(cond)+1:].split('.')[0]); ri=conditions.index(cond); expected=72000001+10000*(20*ri+(root-(72000001+200000*ri))//10000)
 try:
  assert root==expected and (root-(72000001+200000*ri))%10000==0
  h=hashlib.sha256(f.read_bytes()).hexdigest()
  with np.load(f,allow_pickle=False) as z:
   required={'detectors','detector_count','observable','predictions','choice','validation_prediction'};assert required.issubset(z.files)
   packed=z['detectors'];d=np.unpackbits(packed,axis=1,bitorder='little')[:,:40];y=z['observable'];pred=z['predictions'];choice=int(z['choice'])
   assert packed.shape==(30000,5) and int(z['detector_count'])==40 and d.shape==(30000,40) and y.shape==(30000,) and pred.shape==(5,30000) and z['validation_prediction'].shape==(10000,) and 0<=choice<9
   assert all(np.isin(a,[0,1]).all() for a in [d,y,pred,z['validation_prediction']])
   pairs=[grid[choice],pooled,nom,mini,spec[cond]]
   for i,pair in enumerate(pairs): assert np.array_equal(models[pair].decode_batch(d)[:,0].astype(bool),pred[i]),f'prediction mismatch decoder {i}'
   res=pred^y; base=res[1]; cand=res[0]
   row={'condition':cond,'root':root,'shots':len(y),'raw_errors':int(y.sum()),'errors':[int(x.sum()) for x in res], 'candidate_only':[int(np.count_nonzero(x&~base)) for x in res], 'fixed_only':[int(np.count_nonzero(~x&base)) for x in res], 'disagreements':[int(np.count_nonzero(pred[i]!=pred[1])) for i in range(5)],'choice':choice,'file':f.name,'sha256':h}
   rows.append(row);audit.append({'file':f.name,'sha256':h,'status':'PASS','root':root,'condition':cond,'calibration_samples_present':False})
 except Exception as e:audit.append({'file':f.name,'status':'FAIL','reason':repr(e)})
assert len(rows)==60 and len({(r['condition'],r['root']) for r in rows})==60
order=['calibrated','pooled_fixed','nominal_fixed','minimax_fixed','condition_specific']
reg={}
for c in conditions:
 rr=[x for x in rows if x['condition']==c]; n=sum(x['shots'] for x in rr); errs=[sum(x['errors'][j] for x in rr) for j in range(5)]
 reg[c]={'shots':n,'errors':dict(zip(order,errs)),'rates':dict(zip(order,[x/n for x in errs])),'paired_vs_pooled':{}}
 for j,k in enumerate(order):
  a=sum(x['candidate_only'][j] if j!=1 else 0 for x in rr); b=sum(x['fixed_only'][j] if j!=1 else 0 for x in rr); reg[c]['paired_vs_pooled'][k]={'candidate_only':a,'pooled_only':b,'disagreements':a+b,'mcnemar_p':float(binomtest(a,a+b,.5).pvalue) if a+b else 1.}
 reg[c]['primary_difference']=reg[c]['rates']['calibrated']-reg[c]['rates']['pooled_fixed'];reg[c]['relative_reduction']=(errs[1]-errs[0])/errs[1]
# Equal-regime primary and frozen sign-flip over 60 root-regime clusters.
cluster=np.array([(x['errors'][0]-x['errors'][1])/x['shots']/3 for x in rows]); obs=cluster.sum();rng=np.random.default_rng(74000001);draws=rng.integers(0,2,size=(100000,60),dtype=np.int8)*2-1;p=(1+np.count_nonzero(np.abs((draws*cluster).sum(1))>=abs(obs)))/100001
brng=np.random.default_rng(74000001);boot=np.empty(100000)
for q in range(len(boot)):
 vals=[]
 for c in conditions:
  rr=[x for x in rows if x['condition']==c]; ix=brng.integers(0,20,20); vals.append(np.mean([(rr[i]['errors'][0]-rr[i]['errors'][1])/rr[i]['shots'] for i in ix]))
 boot[q]=np.mean(vals)
primary={'equal_regime_difference':float(np.mean([reg[c]['primary_difference'] for c in conditions])),'sign_flip_p_two_sided':float(p),'bootstrap_ci95':np.quantile(boot,[.025,.975]).tolist(),'bootstrap_resamples':100000,'permutation_draws':100000,'seed':74000001}
sec=[]
for j,k in [(2,'nominal_fixed'),(3,'minimax_fixed'),(4,'condition_specific')]:
 a=sum(x['candidate_only'][j] for x in rows);b=sum(x['fixed_only'][j] for x in rows);sec.append({'comparator':k,'candidate_only':a,'comparator_only':b,'mcnemar_p':float(binomtest(a,a+b,.5).pvalue) if a+b else 1.})
ix=np.argsort([x['mcnemar_p'] for x in sec]);adj=[0]*3;run=0
for rank,i in enumerate(ix):run=max(run,min(1,(3-rank)*sec[i]['mcnemar_p']));adj[i]=run
for i in range(3):sec[i]['holm_p']=adj[i]
out={'status':'verified_test_evidence_calibration_provenance_incomplete','audit':audit,'accepted_roots':len(rows),'heldout_shots':sum(x['shots'] for x in rows),'per_regime':reg,'primary':primary,'secondary':sec,'per_root':rows,'calibration_selection_counts':{str(i):sum(x['choice']==i for x in rows) for i in range(9)},'calibration_raw_samples_saved':False,'decoder_predictions_independently_redecoded':True}
(P/'STAGE2_RECOVERED_RESULTS.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'roots':len(rows),'shots':out['heldout_shots'],'primary':primary,'per_regime':{c:reg[c]['errors'] for c in conditions}},indent=2))
