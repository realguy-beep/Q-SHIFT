import sys,json,hashlib,pathlib,time,math,itertools,platform
import numpy as np,stim,pymatching,psutil
from scipy.stats import chi2
R=pathlib.Path.cwd();sys.path.insert(0,str(R)); P=R/'outputs/qshift_correlated_decoder_v1_6b'; RUN=P/'pilot_runs/attempt_001'; OUT=R/'outputs/qshift_v1_6b_calibration_reconstruction_v1'; started=time.monotonic()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
r={'state':'running','checks':[],'errors':[],'metadata':{},'seconds':None}
def save():
 r['seconds']=time.monotonic()-started;(OUT/'reconstruction_results.json').write_text(json.dumps(r,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def check(name,a,b,tol=1e-10):
 ok=(a==b) if not isinstance(a,(float,np.floating)) else math.isclose(float(a),float(b),rel_tol=0,abs_tol=tol)
 r['checks'].append({'name':name,'actual':a,'saved':b,'pass':bool(ok)})
 if not ok:r['errors'].append(name)
try:
 freeze=load(P/'PRETEST_FREEZE.json'); identity=load(RUN/'execution_identity.json'); status=load(RUN/'status.json'); manifest=load(RUN/'run_manifest.json'); replay=load(R/'outputs/qshift_v1_6b_replay_verification_v1/result.json')
 assert replay['state']=='PASS' and replay['shots']==900 and len(replay['rows'])==18
 assert all(not any(row['disagreements'].values()) for row in replay['rows'])
 assert status['state']=='completed' and identity['git_head']==manifest['source_commit']=='02b7aa276d8b3c4ba68824e7b4d839caac4178c8'
 assert sha(P/'PRETEST_FREEZE.json')==identity['pretest_freeze_sha256'] and sha(RUN/'run_manifest.json')==status['run_manifest_sha256']
 for path,h in freeze['files'].items():
  if sha(R/path)!=h:raise ValueError('source hash '+path)
 registry={v['path']:v for v in manifest['archive_manifest']}; assert len(registry)==300
 for rel,entry in registry.items():
  path=RUN/rel
  if sha(path)!=entry['sha256'] or path.stat().st_size!=entry['bytes']:raise ValueError('archive mismatch '+rel)
 for row in replay['rows']:
  if registry[row['archive']]['sha256']!=row['archive_sha256']:raise ValueError('replay mismatch')
 env={'python':platform.python_version(),'stim':stim.__version__,'pymatching':pymatching.__version__,'numpy':np.__version__,'psutil':psutil.__version__}
 if env!=identity['environment']:raise ValueError('environment mismatch')
 r['frozen_files_verified']=len(freeze['files']);r['archives_verified']=len(registry);r['environment']=env
 from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m
 from outputs.qshift_correlated_decoder_v1_6 import learner as L
 from outputs.qshift_v1_4b_decoder_optimality.mld import ExactLogicalDecoder,dem_mechanisms
 classes=L.signature_classes(); subsets=L.test_subsets(classes); spec=m.CodeSpec(); mechs=dem_mechanisms(L.base_dem())
 baseline=np.array([sum(math.log1p(-2*t.p) for t in mechs if len(set(t.detectors)&set(a))%2) for a in subsets]); matrix=np.array([[sum(len(set(s)&set(a))%2 for s in c.events) for a in subsets] for c in classes],dtype=float)
 threshold=float(chi2.ppf(1-0.01/15,df=1))
 def fit(x,idx):
  par=np.array([np.bitwise_xor.reduce(x[:,list(a)],axis=1).mean() for a in subsets]); mu=np.maximum(1-2*par,1e-6); y=np.log(mu)-baseline;w=1/np.maximum((1-mu**2)/(len(x)*mu**2),1e-12); n=matrix[idx]; den=float(np.sum(w*n*n)); numerator=float(np.sum(w*n*y)); beta=numerator/den if den else 0.;delta=numerator**2/den if den and beta<0 else 0.;q=min(max((1-math.exp(beta))/2,0.),m.MAX_BURST_PROBABILITY);return q,delta
 def read(rel,labels=False):
  with np.load(RUN/rel,allow_pickle=False) as z:
   x=z['detectors'].copy(); y=z['observables'][:,0].copy() if labels else None
  return x,y
 for cond in ('known','hidden'):
  dp=RUN/cond/'device_learning.json';mp=RUN/cond/'models_frozen.json';device=load(dp);models=load(mp)
  r['metadata'][cond]={'device_learning.json':sha(dp),'models_frozen.json':sha(mp)}
  x=np.vstack([read(f'{cond}/device/device_det_q{i}.npz')[0] for i in range(3)]); scores=[fit(x,i) for i in range(len(classes))]; idx=max(range(len(scores)),key=lambda i:(scores[i][1],-i)); q,delta=scores[idx]; idx=idx if delta>=threshold else None
  check(cond+'.class',idx,device['learned_class_index']);check(cond+'.device_q',q,device['device_q_hat']);check(cond+'.delta',delta,device['delta']);check(cond+'.threshold',threshold,device['threshold'])
  for i,(_,v) in enumerate(scores):check(f'{cond}.delta.{i}',v,device['all_deltas'][i])
  if idx is None:raise ValueError('no learned class')
  labeled=[read(f'{cond}/device/device_lab_q{i}.npz',True) for i in range(3)];xx=np.vstack([v[0] for v in labeled]); yy=np.concatenate([v[1] for v in labeled]).astype(int); ll=[]
  for flip in (0,1):
   circuit=m.build_candidate_circuit(spec,q,classes[idx].representative(flip));dec=ExactLogicalDecoder(circuit.detector_error_model(decompose_errors=False,approximate_disjoint_errors=True));scale,table=dec.joint(xx);ll.append(float(np.sum(scale+np.log(table[np.arange(len(yy)),yy]))))
  flip=0 if ll[0]>=ll[1] else 1;check(cond+'.flip',flip,device['flip']);check(cond+'.llr',ll[1]-ll[0],device['flip_log_likelihood_ratio_1_minus_0'],1e-8);check(cond+'.representative',list(classes[idx].representative(flip)),device['learned_representative_support']);check(cond+'.model_class',idx,models['learned_class_index']);check(cond+'.model_flip',flip,models['learned_flip']);check(cond+'.model_representative',device['learned_representative_support'],models['learned_representative_support'])
  true_idx=models['true_class_index'];true=tuple(models['true_support']);check(cond+'.true_support_class',true in classes[true_idx].supports_flip0+classes[true_idx].supports_flip1,True)
  for qi in range(3):
   for root in range(24):
    if time.monotonic()-started>850:raise TimeoutError('deadline')
    xx,_=read(f'{cond}/calibration/cal_q{qi}_r{root:02d}.npz');rid=f'q{qi}_r{root:02d}';check(cond+'.learned.'+rid,fit(xx,idx)[0],models['root_qhat_learned_class'][rid]);check(cond+'.true.'+rid,fit(xx,true_idx)[0],models['root_qhat_true_class'][rid])
  save()
 r['state']='PASS' if not r['errors'] else 'FAIL'
except BaseException as e:r['state']='FAIL';r['errors'].append(type(e).__name__+': '+str(e))
finally:save();print(json.dumps({'state':r['state'],'checks':len(r['checks']),'errors':r['errors'],'seconds':r['seconds'],'metadata':r['metadata']}))
if r['state']!='PASS':sys.exit(1)
