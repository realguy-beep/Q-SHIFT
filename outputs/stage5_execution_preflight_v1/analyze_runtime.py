"""Summarize benchmark-only root timing; does not open sample arrays or resample."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
RUN=HERE/'benchmark_run'

def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()

def main():
 runtime=json.loads((HERE/'BENCHMARK_RUNTIME.json').read_text(encoding='utf-8'))
 interrupted=json.loads((HERE/'INTERRUPTION_TEST.json').read_text(encoding='utf-8'))
 inventory=json.loads((HERE/'BENCHMARK_SEED_INVENTORY.json').read_text(encoding='utf-8'))
 seed=int(inventory['runtime_bootstrap_seed'])
 files=sorted((RUN/'roots').glob('root_p*.npz'),key=lambda p:p.stat().st_mtime_ns)
 if len(files)!=20: raise RuntimeError('expected exactly 20 benchmark root archives')
 timestamps=np.asarray([f.stat().st_mtime_ns/1e9 for f in files],dtype=np.float64)
 intervals=np.diff(timestamps)
 if len(intervals)!=19 or np.any(intervals<=0): raise RuntimeError('root completion timestamps are not strictly increasing')
 rng=np.random.Generator(np.random.PCG64(seed))
 draw=rng.integers(0,len(intervals),size=(20000,len(intervals)))
 means=intervals[draw].mean(axis=1)
 low,high=np.quantile(means,[.025,.975])
 n_roots=6050
 outside=float(runtime['invocation_seconds']-intervals.sum())
 analysis_upper=float(json.loads((ROOT/'outputs/stage5_secondary_inference_repair_v1/STAGE5_NO_SAMPLING_PREFLIGHT_V2.json').read_text())['preflight_runtime_seconds'])
 rate=float(runtime['throughput_shots_per_second'])
 allocation=27225000
 sensitivity={}
 for factor in (1,2,4,6,7):
  seconds=allocation/(rate/factor)+analysis_upper
  sensitivity[f'{factor}x_slower']={'seconds':seconds,'minutes':seconds/60,'within_7200_seconds':seconds<7200}
 root_projection={'mean_seconds':n_roots*float(intervals.mean())+outside+analysis_upper,
   'bootstrap_95_seconds':[n_roots*float(low)+outside+analysis_upper,
                           n_roots*float(high)+outside+analysis_upper],
   'bootstrap_99_upper_seconds':n_roots*float(np.quantile(means,.99))+outside+analysis_upper}
 result={'benchmark_only':True,'stage5_evaluation_shots':0,
   'analysis_method':'descriptive nonparametric bootstrap of 19 between-root archive-completion intervals; 20,000 resamples, PCG64 runtime seed from benchmark inventory',
   'runtime_bootstrap_seed':seed,'root_intervals':len(intervals),
   'root_interval_seconds':{'min':float(intervals.min()),'median':float(np.median(intervals)),
     'mean':float(intervals.mean()),'sd':float(intervals.std(ddof=1)),'max':float(intervals.max()),
     'bootstrap_95_mean_ci':[float(low),float(high)],'bootstrap_99_mean_upper':float(np.quantile(means,.99))},
   'fixed_time_outside_intervals_seconds':outside,
   'full_allocation_linear_end_to_end_sample_seconds':allocation/rate,
   'conservative_statistical_analysis_overhead_seconds':analysis_upper,
   'linear_projection_sample_plus_analysis_seconds':allocation/rate+analysis_upper,
   'root_interval_projection_sample_plus_analysis':root_projection,
   'slowdown_sensitivity':sensitivity,
   'archive':{'benchmark_root_file_count':len(files),
      'final_compressed_bytes':sum(f.stat().st_size for f in files),
      'mean_compressed_bytes_per_root':sum(f.stat().st_size for f in files)/len(files),
      'projected_compressed_bytes_at_6050_roots':sum(f.stat().st_size for f in files)/len(files)*6050,
      'frozen_uncompressed_upper_estimate_bytes':1150000000},
   'peak_memory':{'execution_benchmark_bytes':runtime['peak_rss_bytes'],
      'statistics_aggregation_synthetic_probe_bytes':115445760,
      'configured_limit_bytes':2147483648},
   'restart_sampling_accounting':{'first_invocation_sampled_shots':interrupted['sampled_shots'],
      'resume_invocation_sampled_shots':runtime['sampled_shots'],
      'total_sampled_shots':interrupted['sampled_shots']+runtime['sampled_shots'],
      'total_sampler_calls':interrupted['sample_calls']+runtime['sample_calls']}}
 out=HERE/'BENCHMARK_RUNTIME_ANALYSIS.json'
 out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(result,indent=2))
if __name__=='__main__': main()
