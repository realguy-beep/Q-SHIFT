"""No-sampling structural and resource checks for Stage 5."""
from __future__ import annotations
import importlib.metadata as md, json, subprocess, sys, time
from pathlib import Path
import numpy as np, psutil, stim, pymatching

HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT))
from outputs.phase3a_correlated_noise_preflight.simulator import build_spatial_burst_circuit
from outputs.stage4_noise_adaptive_feasibility_v1.prototype import decode_prediction, build_decoder
from outputs.stage5_preexecution_v1.stage5_runner import seed_map, load_profile

P=(0.,.004,.008,.012,.016,.00731)

def run():
    if (HERE/'run').exists(): raise RuntimeError('stage5_preexecution_v1/run exists; preflight refuses to mix with data')
    check=subprocess.run([sys.executable,str(ROOT/'outputs/stage5_independent_confirmation/VERIFY_CANDIDATE_FREEZE.py')],
        cwd=ROOT,capture_output=True,text=True)
    if check.returncode: raise RuntimeError(check.stderr or check.stdout)
    seeds,_=seed_map()
    if len(seeds)!=1000: raise AssertionError('expected 1,000 distinct sampling streams')
    # No Stim sampler is compiled or called in this function.
    t=time.perf_counter()
    ideal=build_spatial_burst_circuit(memory_basis='z',regime='balanced',distance=3,rounds=5,
        gate_p=0.,measurement_p=0.,bias_ratio=10.,burst_probability=0.,burst_pair=(8,10))
    ideal_dem=ideal.detector_error_model(decompose_errors=True,approximate_disjoint_errors=True)
    ideal_match=pymatching.Matching.from_detector_error_model(ideal_dem,enable_correlations=True)
    zeros=np.zeros((256,40),dtype=np.uint8)
    if (ideal.num_detectors,ideal.num_observables,ideal_dem.num_detectors,ideal_dem.num_observables)!=(40,1,40,1):
        raise AssertionError('ideal circuit/DEM dimensions changed')
    if np.any(decode_prediction(ideal_match,zeros)): raise AssertionError('deterministic zero input not decoded to zero')
    records=[]
    for p in P:
        t0=time.perf_counter()
        c=build_spatial_burst_circuit(memory_basis='z',regime='balanced',distance=3,rounds=5,
          gate_p=.003,measurement_p=.003,bias_ratio=10.,burst_probability=p,burst_pair=(8,10))
        dem=c.detector_error_model(decompose_errors=True,approximate_disjoint_errors=True)
        matcher=pymatching.Matching.from_detector_error_model(dem,enable_correlations=True)
        build_s=time.perf_counter()-t0
        if (c.num_detectors,c.num_observables,dem.num_detectors,dem.num_observables,matcher.num_detectors)!=(40,1,40,1,40):
            raise AssertionError(f'circuit/DEM/graph shape mismatch at p={p}')
        if np.any(decode_prediction(matcher,zeros)): raise AssertionError(f'zero detector fixture predicted nonzero at p={p}')
        records.append({'p':p,'dem_instruction_count':sum(1 for _ in dem),'matching_edge_count':len(matcher.edges()),
                        'build_and_graph_seconds':build_s})
    profile=load_profile()
    # Deterministic engineering fixture, not sampled quantum data.
    fixture=np.zeros((2000,40),dtype=np.uint8)
    for i in range(2000):
        fixture[i,(i*7)%40]=1
        if i%5==0: fixture[i,(i*7+1)%40]=1
    t0=time.perf_counter(); estimate=profile.estimate(fixture); estimate_s=time.perf_counter()-t0
    nominal=build_decoder(0.)[2]; batch=np.zeros((256,40),dtype=np.uint8)
    t0=time.perf_counter()
    for _ in range(10): decode_prediction(nominal,batch)
    inference=(time.perf_counter()-t0)/10
    return {'status':'PASS_NO_STAGE5_SAMPLING','sampler_calls':0,'stage5_run_directory_exists':False,
      'candidate_freeze_check':check.stdout.strip(),'sampling_streams_validated':len(seeds),
      'software':{'python':sys.version,'stim':md.version('stim'),'pymatching':md.version('pymatching'),'numpy':np.__version__},
      'ideal_circuit_dem':{'detectors':40,'observables':1,'dem_instruction_count':sum(1 for _ in ideal_dem),
          'synthetic_zero_detector_rows_decoded':len(zeros),'all_predictions_zero':True},
      'no_shot_dem_graph_benchmarks':records,
      'deterministic_fixture_benchmark':{'rows':len(fixture),'estimated_probability':estimate,
          'profile_estimator_seconds':estimate_s,'nominal_decode_seconds_per_256_rows':inference},
      'peak_rss_bytes':psutil.Process().memory_info().rss,
      'elapsed_preflight_seconds':time.perf_counter()-t,
      'limitations':'No simulator samples were generated. The deterministic zero/feature matrices are engineering fixtures and do not estimate Stage 5 sampling throughput.'}

if __name__=='__main__': print(json.dumps(run(),indent=2))
