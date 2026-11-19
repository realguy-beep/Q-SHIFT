"""Cluster-bootstrap audit of the frozen h=8.5946 CUSUM validation streams."""
from __future__ import annotations
import json,time,platform,hashlib
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
from adaptive_histogram_cusum import sample_scores
from adaptive_histogram_cusum_calibrated import events,EDGES,PROBS,DWELL,EPISODES
H=float(json.loads((HERE/'adaptive_histogram_cusum_calibrated_results.json').read_text())['threshold_calibration']['threshold'])
STREAMS=[
 ('initial','nominal','x_biased',.003,2026122211,5,5),
 ('initial','nominal','z_biased',.003,2026122212,4,4),
 ('initial','measurement_shift','x_biased',.006,2026122215,10,10),
 ('initial','measurement_shift','z_biased',.006,2026122216,110,110),
 ('replication_frozen_h','nominal','x_biased',.003,2026122311,10,10),
 ('replication_frozen_h','nominal','z_biased',.003,2026122312,3,3),
 ('replication_frozen_h','measurement_shift','x_biased',.006,2026122315,9,9),
 ('replication_frozen_h','measurement_shift','z_biased',.006,2026122316,107,107),
]
BOOT=20_000;ANALYSIS_SEED=2026122691
def rate(stream,truth):
 vals=[]
 for i in range(EPISODES):
  s=stream[i*DWELL:(i+1)*DWELL]
  vals.append(sum(int(state!=truth) for _,state in events(s,H)))
 return np.asarray(vals,dtype=np.int16)
def main():
 start=time.perf_counter();rng=np.random.default_rng(ANALYSIS_SEED);out=[]
 for label,regime,profile,mp,seed,expected,unused in STREAMS:
  scores,sec=sample_scores(profile,mp,EPISODES*DWELL,seed);truth=profile=='x_biased';counts=rate(scores,truth)
  total=int(counts.sum())
  if total!=expected:raise RuntimeError(f'fixed-seed replay mismatch {label}/{regime}/{profile}: {total}!={expected}')
  boot=rng.integers(0,EPISODES,size=(BOOT,EPISODES),endpoint=False)
  rates=counts[boot].sum(axis=1)*100_000/(EPISODES*(DWELL-100))
  limit=5 if regime=='nominal' else 25
  out.append({'validation_stream':label,'regime':regime,'profile':profile,'measurement_p':mp,'seed':seed,'episode_count':EPISODES,'shots_per_episode':DWELL,'monitored_shots':EPISODES*(DWELL-100),'threshold':H,'false_switches':total,'false_switches_per_100k':total*100_000/(EPISODES*(DWELL-100)),'episodes_with_any_false_switch':int(np.count_nonzero(counts)),'cluster_bootstrap_95_ci_per_100k':[float(np.quantile(rates,.025)),float(np.quantile(rates,.975))],'point_limit':limit,'bootstrap_upper_below_limit':bool(np.quantile(rates,.975)<=limit),'replay_sampling_seconds':sec})
 result={'status':'completed_same_seed_precision_audit','threshold':H,'bootstrap_replicates':BOOT,'analysis_seed':ANALYSIS_SEED,'streams':out,'unique_new_stochastic_samples':0,'elapsed_seconds':time.perf_counter()-start,'software_versions':{'python':platform.python_version(),'numpy':np.__version__},'scope':'cluster-bootstrap intervals for already reported stable-validation streams; same seeds replayed exactly'}
 (HERE/'adaptive_histogram_cusum_validation_precision.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({'rows':[{k:r[k] for k in ('validation_stream','regime','profile','false_switches','false_switches_per_100k','cluster_bootstrap_95_ci_per_100k','point_limit','bootstrap_upper_below_limit')} for r in out],'elapsed':result['elapsed_seconds']},indent=2))
if __name__=='__main__':main()
