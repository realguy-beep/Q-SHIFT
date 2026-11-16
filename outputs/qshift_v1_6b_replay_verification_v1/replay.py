import sys,time,json,hashlib,pathlib,platform
import numpy as np
import stim,pymatching,psutil
R=pathlib.Path.cwd(); sys.path.insert(0,str(R)); P=R/'outputs/qshift_correlated_decoder_v1_6b'; RUN=P/'pilot_runs/attempt_001'; OUT=R/'outputs/qshift_v1_6b_replay_verification_v1'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p): return json.loads(p.read_text(encoding='utf-8-sig'))
started=time.monotonic(); result={'state':'running','rows':[],'shots':0,'errors':[]}; (OUT/'result.json').write_text(json.dumps(result,indent=2))
try:
 freeze=load(P/'PRETEST_FREEZE.json'); bad=[p for p,h in freeze['files'].items() if not (R/p).is_file() or sha(R/p)!=h]
 if bad: raise RuntimeError('frozen hashes mismatch: '+repr(bad))
 cfg=load(P/'config.json'); env={'python':platform.python_version(),'stim':stim.__version__,'pymatching':pymatching.__version__,'numpy':np.__version__,'psutil':psutil.__version__}
 if env!=cfg['environment']: raise RuntimeError('environment mismatch: '+repr(env))
 status=load(RUN/'status.json'); manifest=load(RUN/'run_manifest.json'); ident=load(RUN/'execution_identity.json')
 if status['state']!='completed' or status['shots_committed']!=675000 or len(status['sampler_calls_started'])!=300: raise RuntimeError('status mismatch')
 if sha(RUN/'run_manifest.json')!=status['run_manifest_sha256']: raise RuntimeError('manifest mismatch')
 if manifest['source_commit']!='02b7aa276d8b3c4ba68824e7b4d839caac4178c8' or ident['git_head']!=manifest['source_commit']: raise RuntimeError('execution source mismatch')
 registry={x['path']:x for x in manifest['archive_manifest']}
 if len(registry)!=300: raise RuntimeError('archive registry duplicate/incomplete')
 for path,entry in registry.items():
  f=RUN/path
  if not f.is_file() or sha(f)!=entry['sha256'] or f.stat().st_size!=entry['bytes']: raise RuntimeError('archive mismatch '+path)
 result.update(source_commit=manifest['source_commit'],frozen_files_verified=len(freeze['files']),archives_verified=len(registry),environment=env)
 from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m
 from outputs.qshift_correlated_decoder_v1_6b import contract as K
 from outputs.qshift_v1_4b_decoder_optimality.mld import ExactLogicalDecoder
 spec=m.CodeSpec()
 def matcher(s,q):
  circuit=m.build_base_circuit(spec) if s is None else m.build_candidate_circuit(spec,q,s)
  return m.build_matching(m.build_decomposed_dem(circuit))
 def exact(s,q):
  circuit=m.build_base_circuit(spec) if s is None or q<=0 else m.build_candidate_circuit(spec,q,s)
  return ExactLogicalDecoder(circuit.detector_error_model(decompose_errors=False,approximate_disjoint_errors=True))
 base=matcher(None,0.0)
 for cond in ('known','hidden'):
  models=load(RUN/cond/'models_frozen.json'); device=load(RUN/cond/'device_learning.json')
  if not models.get('model_choice_frozen_before_evaluation'):raise RuntimeError('model freeze absent')
  if models['learned_class_index']!=device['learned_class_index'] or models['learned_flip']!=device['flip'] or models['learned_representative_support']!=device['learned_representative_support']: raise RuntimeError('model/device state mismatch')
  true=tuple(models['true_support']); learned=tuple(models['learned_representative_support']) if models['learned_representative_support'] is not None else None
  ao=matcher(true,K.STATIC_MATCHING_Q); al=matcher(learned,K.STATIC_MATCHING_Q)
  five=m.FiveFactorDecoder(matcher(None,0),m.extract_burst_events(spec,true),spec.detectors,correlations=False)
  for qi in range(3):
   for root in (0,7,19):
    if time.monotonic()-started>=850: raise TimeoutError('internal deadline')
    rid=K.root_id(qi,root); rel=f'{cond}/evaluation/{K.eval_archive_name(qi,root)}'; path=RUN/rel
    with np.load(path,allow_pickle=False) as z: det=z['detectors'][:50].copy()
    if det.shape!=(50,40) or det.dtype!=np.uint8:raise RuntimeError('detector shape/dtype')
    eo=exact(true,models['root_qhat_true_class'][rid]); el=exact(learned,models['root_qhat_learned_class'][rid])
    col=lambda a:np.asarray(a,dtype=np.uint8).reshape(-1,1)
    pred={'A_nominal':col(base.decode_batch(det,enable_correlations=False)),'Astar_oracle':col(ao.decode_batch(det,enable_correlations=True)),'Astar_learned':col(al.decode_batch(det,enable_correlations=True)),'BoffStatic_oracle':five.decode_rows(det,{'x':K.BOFFSTATIC_Q})['x'],'Bexact_oracle':eo.decode(det,batch=256)[0].astype(np.uint8),'Blearn':el.decode(det,batch=256)[0].astype(np.uint8)}
    with np.load(path,allow_pickle=False) as z: diffs={a:int(np.count_nonzero(pred[a]!=z['pred_'+a][:50])) for a in K.ARMS}
    result['rows'].append({'archive':rel,'archive_sha256':registry[rel]['sha256'],'rows':'0:50','disagreements':diffs});result['shots']+=50
    (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    if any(diffs.values()):raise RuntimeError('prediction disagreement '+rel)
 result['state']='PASS'
except BaseException as e:
 result['state']='FAIL';result['errors'].append(type(e).__name__+': '+str(e))
finally:
 result['elapsed_seconds']=time.monotonic()-started
 (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({'state':result['state'],'shots':result['shots'],'elapsed_seconds':result['elapsed_seconds'],'errors':result['errors']}))
if result['state']!='PASS':sys.exit(1)
