"""Deterministic estimator and feature-map benchmark; performs no sampling."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import tempfile
import time

import numpy as np
import psutil
import stim

ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from outputs.qshift_advanced_research_v3a.qshift_estimators import CandidateA,CandidateB,TemplateBank,detector_features
from outputs.qshift_advanced_research_v3a import run_finite_history_study
from outputs.qshift_advanced_research_v3a import analyze_finite_history_study

HERE=Path(__file__).resolve().parent
BANK_PATH=HERE/'template_bank_v1.json'
OUT_PATH=HERE/'benchmark_results.json'
BASELINE_COMMIT='6070fa875a14fe8e4e9b713607dd0f3a4e6e1c23'


def digest(path:Path)->str: return hashlib.sha256(path.read_bytes()).hexdigest()


def processor_name()->str:
    if os.name=='nt':
        try:
            import winreg
            key=winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                r'HARDWARE\DESCRIPTION\System\CentralProcessor\0')
            return str(winreg.QueryValueEx(key,'ProcessorNameString')[0]).strip()
        except OSError: pass
    return platform.processor()


def load_baseline_implementation():
    source=subprocess.check_output(['git','show',
        f'{BASELINE_COMMIT}:outputs/qshift_advanced_research_v3a/qshift_estimators.py'],
        cwd=ROOT)
    temp=tempfile.TemporaryDirectory(prefix='qshift-v3a-baseline-')
    path=Path(temp.name)/'qshift_estimators_baseline.py'; path.write_bytes(source)
    spec=importlib.util.spec_from_file_location('qshift_estimators_baseline',path)
    module=importlib.util.module_from_spec(spec); sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module,temp


def measure(callable_,repetitions:int=200)->dict:
    for _ in range(10): callable_()
    times=[]
    for _ in range(repetitions):
        start=time.perf_counter_ns(); callable_(); times.append(time.perf_counter_ns()-start)
    ordered=sorted(times)
    return {'repetitions':repetitions,'median_ms':statistics.median(times)/1e6,
            'p95_ms':ordered[int(.95*(len(ordered)-1))]/1e6,
            'mean_ms':statistics.mean(times)/1e6}


def main()->None:
    bank=TemplateBank.load(BANK_PATH)
    baseline_module,baseline_temp=load_baseline_implementation()
    baseline_bank=baseline_module.TemplateBank.load(BANK_PATH)
    process=psutil.Process()
    machine={'platform':platform.platform(),'processor':processor_name(),
        'logical_cpus':os.cpu_count(),'physical_cpus':psutil.cpu_count(logical=False),
        'total_ram_bytes':psutil.virtual_memory().total,'python':platform.python_version(),
        'numpy':np.__version__,'stim':stim.__version__,'psutil':psutil.__version__}
    init={}; estimators={}; baseline_init={}; baseline_estimators={}; feature_cost={}; windows=[200,1000,5000,10000]
    for family in ('exact_categorical','approximate_dem'):
        for arm,cls in (('A',CandidateA),('B',CandidateB)):
            start=time.perf_counter_ns(); estimators[(family,arm)]=cls(bank,family)
            init[f'{family}_{arm}']=(time.perf_counter_ns()-start)/1e9
    optimized_rss=int(process.memory_info().rss)
    for family in ('exact_categorical','approximate_dem'):
        for arm in ('A','B'):
            start=time.perf_counter_ns()
            old_cls=getattr(baseline_module,'Candidate'+arm)
            baseline_estimators[(family,arm)]=old_cls(baseline_bank,family)
            baseline_init[f'{family}_{arm}']=(time.perf_counter_ns()-start)/1e9
    for family in ('exact_categorical','approximate_dem'):
        target_sets=[]
        for i in range(32):
            pb=.008 + ((i%5)-2)*.001
            pm=.003 + ((i%7)-3)*.001
            pb=min(.020,max(0,pb)); pm=min(.010,max(0,pm))
            target_sets.append(bank.interpolated(family,pb,pm))
        for arm in ('A','B'):
            est=estimators[(family,arm)]; cursor={'i':0}
            def evaluate():
                i=cursor['i']; cursor['i']=(i+1)%len(target_sets)
                return est.estimate_mean(target_sets[i],history_length=1000)
            machine_key=f'{family}_{arm}'
            init[machine_key+'_evaluation']=measure(evaluate,200)
            old_est=baseline_estimators[(family,arm)]; old_cursor={'i':0}
            def baseline_evaluate():
                i=old_cursor['i']; old_cursor['i']=(i+1)%len(target_sets)
                return old_est.estimate_mean(target_sets[i],history_length=1000)
            baseline_init[machine_key+'_evaluation']=measure(baseline_evaluate,200)
    # Deterministic binary fixture, not a Stim history or experimental outcome.
    columns=np.arange(40,dtype=np.uint16)[None,:]
    for n in windows:
        rows=np.arange(n,dtype=np.uint32)[:,None]
        fixture=((rows*7+columns*11)%13<3).astype(np.uint8)
        feature_cost[str(n)]=measure(lambda d=fixture:detector_features(d).mean(axis=0),30)
    counts={str(n):len(range(n,10100,100)) for n in windows}
    study_config=json.loads((HERE/'finite_history_study_config.json').read_text())
    roots=sum(study_config['split_roots_per_condition'].values())
    condition_count=len(study_config['conditions'])
    total_roots=roots*condition_count
    updates_per_root=sum(counts.values())
    update_windows=total_roots*updates_per_root
    evaluations=update_windows*len(('exact_categorical','approximate_dem'))*2
    estimator_seconds=0.0; feature_seconds=0.0
    for n in windows:
        visits=total_roots*counts[str(n)]
        feature_seconds+=visits*feature_cost[str(n)]['median_ms']/1000
        for family in ('exact_categorical','approximate_dem'):
            for arm in ('A','B'):
                estimator_seconds+=visits*init[f'{family}_{arm}_evaluation']['median_ms']/1000
    construction_seconds=sum(init[k] for k in ('exact_categorical_A','exact_categorical_B',
                                                  'approximate_dem_A','approximate_dem_B'))
    info=process.memory_info()
    peak=getattr(info,'peak_wset',None)
    if peak is None: peak=info.rss
    baseline_eval={k:v for k,v in baseline_init.items() if k.endswith('_evaluation')}
    current_eval={k:v for k,v in init.items() if k.endswith('_evaluation')}
    speedups={k:baseline_eval[k]['median_ms']/current_eval[k]['median_ms'] for k in current_eval}
    result={'schema':'qshift-deterministic-benchmark-v1','command':'python outputs/qshift_advanced_research_v3a/benchmark_estimators.py',
        'machine':machine,'template_bank_sha256':digest(BANK_PATH),
        'benchmark_script_sha256':digest(Path(__file__).resolve()),
        'baseline_commit':BASELINE_COMMIT,
        'implementation_hashes':{'estimator_sha256':digest(HERE/'qshift_estimators.py'),
            'runner_sha256':digest(Path(run_finite_history_study.__file__).resolve()),
            'analysis_sha256':digest(Path(analyze_finite_history_study.__file__).resolve()),
            'template_generator_sha256':digest(HERE/'generate_templates.py'),
            'circuit_builder_sha256':digest(ROOT/'outputs/phase3a_correlated_noise_preflight/simulator.py'),
            'protocol_sha256':digest(HERE/'DEVELOPMENT_STUDY_PROTOCOL.md'),
            'study_config_sha256':digest(HERE/'finite_history_study_config.json'),
            'runtime_fingerprint_sha256':hashlib.sha256(json.dumps(
                {'python':platform.python_version(),'numpy':np.__version__,'stim':stim.__version__},
                sort_keys=True,separators=(',',':')).encode('utf-8')).hexdigest()},
        'method':'warm-up 10; 200 deterministic population-feature evaluations per estimator; median/p95 wall latency; 30 feature-map trials per history length; deterministic modular binary fixture; no Stim sampler',
        'candidate_initialization_seconds':{k:v for k,v in init.items() if not k.endswith('_evaluation')},
        'evaluation_latency':{k:v for k,v in init.items() if k.endswith('_evaluation')},
        'baseline_candidate_initialization_seconds':{k:v for k,v in baseline_init.items() if not k.endswith('_evaluation')},
        'baseline_evaluation_latency':baseline_eval,
        'median_latency_speedup_vs_baseline':speedups,
        'feature_map_and_mean_latency':feature_cost,'fixture_shot_counts':counts,
        'proposed_design':{'conditions':condition_count,'roots':total_roots,
            'updates_per_root_all_windows':updates_per_root,'estimator_evaluations':evaluations,
        'update_windows':update_windows,
        'per_estimator_family_arm_evaluations':update_windows},
        'projection_measured_core_only':{'estimator_initialization_seconds_once':construction_seconds,
            'feature_map_seconds_estimate':feature_seconds,'estimator_seconds_estimate':estimator_seconds,
            'combined_seconds_excluding_sampling_checkpoint_io_and_analysis':construction_seconds+feature_seconds+estimator_seconds},
        'memory':{'optimized_runner_resident_bytes_after_four_estimators':optimized_rss,
            'peak_rss_or_peak_wset_bytes_for_comparison_process':int(peak)},
        'scope':'deterministic computation benchmark only; no detector histories sampled; full-study end-to-end wall time not claimed'}
    OUT_PATH.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2,sort_keys=True))
    baseline_temp.cleanup()


if __name__=='__main__': main()
