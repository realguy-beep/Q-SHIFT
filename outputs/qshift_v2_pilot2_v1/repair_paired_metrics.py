"""Rebuild paired CSV contingency cells from the immutable aligned outcome archive."""
import csv,hashlib,json
from pathlib import Path
import numpy as np
OUT=Path(__file__).resolve().parent

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
with np.load(OUT/'PILOT2_PAIRED_OUTCOMES.npz',allow_pickle=False) as z:
    pred=z['predictions'].astype(np.uint8); obs=z['observables'].astype(np.uint8)
    scenarios=z['stream_scenarios'].astype(str); reps=z['stream_replicates'].astype(int)
    policies=list(map(str,z['policy_names'])); modes=list(map(bool,z['decoder_modes']))
rows=list(csv.DictReader((OUT/'PILOT2_RESULTS_PREPAIR.csv').open(encoding='utf-8',newline='')))
if len(rows)!=len(scenarios)*len(modes)*len(policies): raise SystemExit('row count mismatch')
stream_index={(sc,int(r)):i for i,(sc,r) in enumerate(zip(scenarios,reps))}
for row in rows:
    si=stream_index[(row['scenario'],int(row['replicate']))]; mi=modes.index(row['correlation_decode']=='True'); pi=policies.index(row['policy'])
    e=(pred[si,mi,pi]^obs[si]).astype(bool)
    for cj,comp in enumerate(policies):
        c=(pred[si,mi,cj]^obs[si]).astype(bool)
        cells=(int(np.count_nonzero(e&c)),int(np.count_nonzero(e&~c)),int(np.count_nonzero(~e&c)),int(np.count_nonzero(~e&~c)))
        for key,val in zip((f'both_error_vs_{comp}',f'policy_only_error_vs_{comp}',f'comparator_only_error_vs_{comp}',f'neither_error_vs_{comp}'),cells): row[key]=val
    row['end_to_end_cpu_s']=sum(float(row[k]) for k in ('decoder_cpu_s','shared_initial_calibration_cpu_s','estimator_cpu_s','change_detection_cpu_s','graph_selection_cpu_s'))
path=OUT/'PILOT2_RESULTS.csv'
with path.open('w',encoding='utf-8',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
rp=OUT/'PILOT2_RUNTIME.json'; runtime=json.loads(rp.read_text(encoding='utf-8'))
runtime['pre_repair_results_sha256']=sha(OUT/'PILOT2_RESULTS_PREPAIR.csv')
runtime['results_sha256']=sha(path)
runtime['final_source_hashes_sha256']={name:sha(OUT/name) for name in ['prepare_pilot2.py','preflight_audit.py','controller.py','run_pilot2.py','test_pilot2.py','independent_audit.py','repair_paired_metrics.py']}
runtime['postrun_pair_metric_repair']={'performed':True,'columns_recomputed':['paired discordance cells','end_to_end_cpu_s'],'input_archive_sha256':sha(OUT/'PILOT2_PAIRED_OUTCOMES.npz'),
  'repair_script_sha256':sha(OUT/'repair_paired_metrics.py'),'runner_source_at_execution_sha256':runtime['source_hashes_sha256']['run_pilot2.py'],
  'runner_source_after_repair_sha256':sha(OUT/'run_pilot2.py'),'method':'paired contingency counts recomputed from stored per-shot predictions XOR shared observables; end-to-end CPU recomputed as decoder + shared initial calibration + estimator + change detection + graph selection'}
rp.write_text(json.dumps(runtime,indent=2),encoding='utf-8')
print(json.dumps({'rows_repaired':len(rows),'pre_repair_sha256':runtime['pre_repair_results_sha256'],'post_repair_sha256':runtime['results_sha256'],
  'paired_archive_sha256':runtime['paired_outcomes_sha256']},indent=2))
