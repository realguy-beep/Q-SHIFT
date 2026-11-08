"""Run the frozen Stage 5 path on an isolated, reduced benchmark allocation."""
from __future__ import annotations
import argparse, hashlib, json, os, sys, threading, time
from pathlib import Path

import numpy as np
import psutil

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
RUN=HERE/'benchmark_run'
FREEZE=HERE/'BENCHMARK_FREEZE.json'
INVENTORY=HERE/'BENCHMARK_SEED_INVENTORY.json'
CONFIG=HERE/'benchmark_config.json'
PROTOCOL=HERE/'BENCHMARK_PROTOCOL.md'
STAGE5=ROOT/'outputs/stage5_secondary_inference_repair_v1'
STAGE5_RESERVED_START=14_000_000_001
STAGE5_RESERVED_COUNT=12_100
PROBS=(0.0,0.004,0.008,0.012,0.016)
ROOTS=4; CAL_SHOTS=2000; EVAL_SHOTS=2500
TOTAL_ROOTS=len(PROBS)*ROOTS; TOTAL_SHOTS=TOTAL_ROOTS*(CAL_SHOTS+EVAL_SHOTS)
_deadline=[None]

class PlannedInterruption(Exception): pass

def check_deadline():
    if _deadline[0] is not None and time.monotonic()>_deadline[0]:
        raise TimeoutError('benchmark-only 300 second wall limit exceeded')

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1<<20),b''): h.update(block)
    return h.hexdigest()

def verify_benchmark_freeze():
    if not FREEZE.is_file(): raise RuntimeError('benchmark freeze is missing')
    freeze=json.loads(FREEZE.read_text(encoding='utf-8'))
    if freeze.get('created_before_sampling') is not True or freeze.get('benchmark_samples_generated')!=0:
        raise RuntimeError('benchmark freeze was not created before sampling')
    for rel,digest in freeze['sha256'].items():
        if sha(ROOT/rel)!=digest: raise RuntimeError(f'benchmark/source hash mismatch: {rel}')
    inv=json.loads(INVENTORY.read_text(encoding='utf-8'))
    seeds=[int(x['seed']) for x in inv['streams']]
    if len(seeds)!=40 or len(set(seeds))!=40 or inv['historical_collision_count'] or inv['stage5_reserved_allocation_collision_count']:
        raise RuntimeError('benchmark seed inventory failed integrity check')
    return freeze,inv

def benchmark_map(inv):
    result={}
    for row in inv['streams']:
        key=(row['kind'],float(row['probability']),int(row['root']))
        if key in result: raise RuntimeError('duplicate benchmark stream key')
        result[key]=int(row['seed'])
    expected={(kind,p,r) for kind in ('calibration_detector_only','paired_evaluation_detector_observable')
              for p in PROBS for r in range(ROOTS)}
    if set(result)!=expected: raise RuntimeError('benchmark stream coverage mismatch')
    if any(STAGE5_RESERVED_START<=s<STAGE5_RESERVED_START+STAGE5_RESERVED_COUNT for s in result.values()):
        raise RuntimeError('benchmark seed overlaps the Stage 5 reserved allocation')
    return result

def independent_benchmark_screen():
    """Verify only the benchmark list and nonsealed historical hashes."""
    inv=json.loads(INVENTORY.read_text(encoding='utf-8'))
    seeds=[int(x['seed']) for x in inv['streams']]
    if len(seeds)!=len(set(seeds)): raise RuntimeError('duplicate benchmark seeds')
    for row in inv['historical_sources_checked']:
        if sha(ROOT/row['path'])!=row['sha256']:
            raise RuntimeError(f'nonsealed history changed after benchmark freeze: {row["path"]}')
    return 'benchmark seeds screened; Stage 5 sample seed rows not read'

class Timings:
    def __init__(self): self.seconds={}; self.bytes_written=0; self.sample_calls=0; self.sampled_shots=0
    def add(self,key,duration): self.seconds[key]=self.seconds.get(key,0.0)+duration

class TimedSampler:
    def __init__(self,base,timings): self.base=base; self.timings=timings
    def sample(self,*args,**kwargs):
        t=time.perf_counter()
        try: return self.base.sample(*args,**kwargs)
        finally:
            self.timings.add('stim_sampling',time.perf_counter()-t)
            self.timings.sample_calls+=1
            shots=args[0] if args else kwargs.get('shots',0)
            self.timings.sampled_shots+=int(shots or 0)
            check_deadline()

class TimedCircuit:
    def __init__(self,base,timings): self.base=base; self.timings=timings
    def __getattr__(self,name): return getattr(self.base,name)
    def compile_detector_sampler(self,*args,**kwargs):
        t=time.perf_counter()
        try: sampler=self.base.compile_detector_sampler(*args,**kwargs)
        finally: self.timings.add('stim_sampler_compile',time.perf_counter()-t)
        check_deadline()
        return TimedSampler(sampler,self.timings)

def make_instrumented_runner(interrupt_after_first_calibration=False):
    sys.path.insert(0,str(ROOT))
    sys.path.insert(0,str(STAGE5))
    import stage5_sampling_runner_v2 as runner
    runner.RUN=RUN
    runner.PROBS=PROBS; runner.ROOTS=ROOTS; runner.CAL_SHOTS=CAL_SHOTS
    runner.EVAL_SHOTS=EVAL_SHOTS; runner.TOTAL_ROOTS=TOTAL_ROOTS; runner.TOTAL_SHOTS=TOTAL_SHOTS
    _,inv=verify_benchmark_freeze(); seedmap=benchmark_map(inv)
    runner.seed_map=lambda:(seedmap,inv)
    runner.verify_candidate_screen=independent_benchmark_screen
    timing=Timings()

    original_build_circuit=runner.build_spatial_burst_circuit
    def build_circuit(*args,**kwargs):
        t=time.perf_counter()
        try: circuit=original_build_circuit(*args,**kwargs)
        finally: timing.add('circuit_build',time.perf_counter()-t)
        check_deadline()
        return TimedCircuit(circuit,timing)
    runner.build_spatial_burst_circuit=build_circuit

    original_build_decoder=runner.build_decoder
    def build_decoder(*args,**kwargs):
        t=time.perf_counter()
        try: return original_build_decoder(*args,**kwargs)
        finally: timing.add('decoder_build',time.perf_counter()-t); check_deadline()
    runner.build_decoder=build_decoder

    original_decode=runner.decode_prediction
    def decode(matching,detectors):
        t=time.perf_counter()
        try: return original_decode(matching,detectors)
        finally: timing.add('decoding',time.perf_counter()-t); check_deadline()
    runner.decode_prediction=decode

    estimator_class=runner.DetectorProfileEstimator
    original_estimate=estimator_class.estimate
    def estimate(self,detectors):
        t=time.perf_counter()
        try: return original_estimate(self,detectors)
        finally: timing.add('profile_estimation',time.perf_counter()-t); check_deadline()
    estimator_class.estimate=estimate

    original_npz=runner.atomic_npz
    def atomic_npz(path,**arrays):
        t=time.perf_counter()
        try: return original_npz(path,**arrays)
        finally:
            timing.add('compressed_npz_atomic_io',time.perf_counter()-t)
            try: timing.bytes_written+=Path(path).stat().st_size
            except OSError: pass
            check_deadline()
    runner.atomic_npz=atomic_npz

    original_json=runner.atomic_json
    def atomic_json(path,obj):
        t=time.perf_counter()
        try: return original_json(path,obj)
        finally: timing.add('atomic_json_io',time.perf_counter()-t); check_deadline()
    runner.atomic_json=atomic_json

    def descriptive_analysis(groups,cfg,roots):
        out={}
        for p,values in groups.items():
            x=np.asarray(values,dtype=np.float64)
            if x.shape!=(roots,) or not np.isfinite(x).all(): raise RuntimeError('benchmark aggregate input invalid')
            out[str(p)]={'root_count':int(roots),'mean_paired_difference':float(x.mean()),
                         'root_sd_descriptive':float(x.std(ddof=1)) if roots>1 else None}
        return {'scope':'benchmark descriptive aggregation only; no inferential Stage 5 test',
                'conditions':out}
    runner.analyze=descriptive_analysis

    original_summarize=runner.summarize
    def summarize(rootdir,cfg):
        t=time.perf_counter()
        try: return original_summarize(rootdir,cfg)
        finally: timing.add('saved_root_aggregation',time.perf_counter()-t); check_deadline()
    runner.summarize=summarize

    if interrupt_after_first_calibration:
        original_adaptive=runner.get_adaptive
        fired={'value':False}
        def interrupt_once(bank,p_hat):
            if not fired['value']:
                fired['value']=True
                raise PlannedInterruption('planned process stop after durable first calibration checkpoint')
            return original_adaptive(bank,p_hat)
        runner.get_adaptive=interrupt_once
    return runner,timing

def monitor_rss(stop_event,peak):
    proc=psutil.Process()
    while not stop_event.wait(0.01):
        try: peak[0]=max(peak[0],proc.memory_info().rss)
        except psutil.Error: pass

def main(argv=None):
    parser=argparse.ArgumentParser()
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--interrupt-after-first-calibration',action='store_true')
    mode.add_argument('--resume',action='store_true')
    args=parser.parse_args(argv)
    _,inv=verify_benchmark_freeze()
    if args.interrupt_after_first_calibration:
        if RUN.exists(): raise RuntimeError('benchmark output already exists; refusing to overwrite')
    elif not (RUN/'status.json').is_file():
        raise RuntimeError('resume requested without the planned benchmark interruption checkpoint')
    root=RUN/'roots'
    if args.resume and not (root/'root_p0.000_r000.npz').is_file():
        raise RuntimeError('first durable calibration checkpoint is missing')

    started=time.perf_counter(); _deadline[0]=time.monotonic()+300
    peak=[psutil.Process().memory_info().rss]; stop=threading.Event()
    monitor=threading.Thread(target=monitor_rss,args=(stop,peak),daemon=True); monitor.start()
    runner,timing=make_instrumented_runner(args.interrupt_after_first_calibration)
    status='completed'; interruption=None
    try:
        runner.execute()
    except PlannedInterruption as exc:
        status='planned_interruption'; interruption=str(exc)
    finally:
        stop.set(); monitor.join(timeout=2)
    elapsed=time.perf_counter()-started
    if args.interrupt_after_first_calibration:
        if status!='planned_interruption': raise RuntimeError('planned interruption did not occur')
        cp=root/'root_p0.000_r000.npz'
        with np.load(cp,allow_pickle=False) as z:
            if str(np.asarray(z['phase']).item())!='calibration_complete': raise RuntimeError('calibration checkpoint phase not durable')
            if np.asarray(z['calibration_detectors']).shape!=(CAL_SHOTS,40): raise RuntimeError('durable calibration shape mismatch')
        st=json.loads((RUN/'status.json').read_text(encoding='utf-8'))
        if st.get('calibration_shots_generated')!=CAL_SHOTS or st.get('unique_shots_generated')!=CAL_SHOTS or st.get('in_flight') is not None:
            raise RuntimeError('interruption status is not at a safe durable boundary')
        record={'status':'PASS_PLANNED_INTERRUPTION','benchmark_only':True,'stage5_shots':0,
                'durable_calibration_shots':CAL_SHOTS,'calibration_checkpoint_sha256':sha(cp),
                'persisted_runner_status':st.get('status'),'in_flight_clear':st.get('in_flight') is None,
                'invocation_seconds':elapsed,'peak_rss_bytes':peak[0],
                'sample_calls':timing.sample_calls,'sampled_shots':timing.sampled_shots,
                'timed_operations_seconds':timing.seconds}
        (HERE/'INTERRUPTION_TEST.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(record,indent=2)); return 75
    if status!='completed': raise RuntimeError(f'benchmark did not complete: {status}')
    st=json.loads((RUN/'status.json').read_text(encoding='utf-8'))
    if st.get('status')!='completed' or st.get('completed_roots')!=TOTAL_ROOTS or st.get('unique_shots_generated')!=TOTAL_SHOTS:
        raise RuntimeError('benchmark persisted completion totals are invalid')
    metric={'status':'PASS_BENCHMARK_COMPLETED','benchmark_only':True,'benchmark_roots':TOTAL_ROOTS,
            'calibration_shots':TOTAL_ROOTS*CAL_SHOTS,'evaluation_shots':TOTAL_ROOTS*EVAL_SHOTS,
            'unique_shots':TOTAL_SHOTS,'stage5_evaluation_shots':0,
            'invocation_seconds':elapsed,'throughput_shots_per_second':TOTAL_SHOTS/max(elapsed,1e-12),
            'peak_rss_bytes':peak[0],'free_disk_after_bytes':__import__('shutil').disk_usage(ROOT).free,
            'npz_bytes_written_timed':timing.bytes_written,'sample_calls':timing.sample_calls,
            'sampled_shots':timing.sampled_shots,'timed_operations_seconds':timing.seconds,
            'resumed_from_durable_checkpoint':True,'runner_status':st.get('status'),
            'independent_test_access':0}
    (HERE/'BENCHMARK_RUNTIME.json').write_text(json.dumps(metric,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(metric,indent=2)); return 0

if __name__=='__main__': raise SystemExit(main())
