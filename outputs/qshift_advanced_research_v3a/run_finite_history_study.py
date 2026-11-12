"""Guarded future finite-history study executor.

This file is not run by Phase 3A. It refuses to sample unless supplied with a
separate development-only authorization record and pre-created seed manifest.
The current tests never invoke the sampling path.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

import numpy as np
import stim

ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from outputs.phase3a_correlated_noise_preflight.simulator import build_spatial_burst_circuit
from outputs.qshift_advanced_research_v3a.qshift_estimators import CandidateA,CandidateB,TemplateBank

HERE=Path(__file__).resolve().parent
PROTOCOL=HERE/'DEVELOPMENT_STUDY_PROTOCOL.md'


def peak_rss_bytes()->int:
    if os.name=='nt':
        import ctypes
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_=[('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD),
                ('PeakWorkingSetSize',ctypes.c_size_t),('WorkingSetSize',ctypes.c_size_t),
                ('QuotaPeakPagedPoolUsage',ctypes.c_size_t),('QuotaPagedPoolUsage',ctypes.c_size_t),
                ('QuotaPeakNonPagedPoolUsage',ctypes.c_size_t),('QuotaNonPagedPoolUsage',ctypes.c_size_t),
                ('PagefileUsage',ctypes.c_size_t),('PeakPagefileUsage',ctypes.c_size_t)]
        counters=Counters(); counters.cb=ctypes.sizeof(counters)
        handle=ctypes.windll.kernel32.GetCurrentProcess()
        ok=ctypes.windll.psapi.GetProcessMemoryInfo(handle,ctypes.byref(counters),counters.cb)
        if not ok: raise OSError('GetProcessMemoryInfo failed')
        return int(counters.PeakWorkingSetSize)
    try:
        import resource
    except ImportError as exc:
        raise RuntimeError('peak RSS measurement unsupported on this platform') from exc
    value=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value if sys.platform=='darwin' else value*1024)


def sha256(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_authorization(record_path:Path,seed_manifest_path:Path,config:dict)->dict:
    auth=json.loads(record_path.read_text(encoding='utf-8'))
    required={'schema':'qshift-sampling-authorization-v1','approved':True,
              'scope':'development_only','protected_data_access':False,
              'protocol_sha256':sha256(PROTOCOL)}
    for key,value in required.items():
        if auth.get(key)!=value:
            raise PermissionError(f"authorization record fails required field {key}")
    if not auth.get('approved_by') or not auth.get('approval_reference'):
        raise PermissionError('authorization record lacks approver/reference')
    seeds=json.loads(seed_manifest_path.read_text(encoding='utf-8'))
    if seeds.get('schema')!='qshift-development-seed-manifest-v1':
        raise ValueError('unsupported development seed manifest schema')
    if seeds.get('split_scope')!='development_only':
        raise PermissionError('seed manifest is not marked development_only')
    expected_counts=config['split_roots_per_condition']
    seen=set(); split_root_ids=set(); seed_values=set()
    for entry in seeds.get('roots',[]):
        key=(entry.get('split'),entry.get('scenario'),entry.get('root_id'))
        if key in seen: raise ValueError(f'duplicate root entry {key}')
        seen.add(key)
        split_key=(entry.get('scenario'),entry.get('root_id'))
        if split_key in split_root_ids:
            raise ValueError(f'root id reused across splits: {split_key}')
        split_root_ids.add(split_key)
        if key[0] not in expected_counts or key[1] not in config['conditions']:
            raise ValueError(f'unexpected split/scenario {key}')
        if not isinstance(key[2],str) or not key[2]:
            raise ValueError('root_id must be a nonempty string')
        if len(entry.get('segments',[]))!=len(config['conditions'][key[1]]):
            raise ValueError(f'incorrect segment count for {key}')
        for actual,planned in zip(entry['segments'],config['conditions'][key[1]]):
            if any(actual.get(k)!=planned[k] for k in ('shots','p_burst','p_measurement','gate_p')):
                raise ValueError(f'seed manifest condition mismatch for {key}')
            s=actual.get('seed')
            if not isinstance(s,int) or s<0 or s in seed_values:
                raise ValueError('each segment requires a unique nonnegative integer seed')
            seed_values.add(s)
        if sum(int(x['shots']) for x in entry['segments'])!=config['shots_per_root']:
            raise ValueError(f'shot count mismatch for {key}')
    for split,count in expected_counts.items():
        for scenario in config['conditions']:
            n=sum(1 for e in seeds.get('roots',[]) if e['split']==split and e['scenario']==scenario)
            if n!=count: raise ValueError(f'expected {count} roots for {split}/{scenario}, found {n}')
    return {'authorization_sha256':sha256(record_path),'seed_manifest_sha256':sha256(seed_manifest_path),
            'roots':len(seeds['roots']),'segment_seed_count':len(seed_values)}


def sample_root(segments:list[dict])->np.ndarray:
    """Sample detector bits only for one authorized future study root."""
    chunks=[]
    for s in segments:
        circuit=build_spatial_burst_circuit(gate_p=float(s['gate_p']),
            measurement_p=float(s['p_measurement']),burst_probability=float(s['p_burst']))
        sampler=circuit.compile_detector_sampler(seed=int(s['seed']))
        d=sampler.sample(shots=int(s['shots']),append_observables=False)
        if d.shape!=(int(s['shots']),40): raise RuntimeError('Stim returned an unexpected detector shape')
        chunks.append(np.asarray(d,dtype=np.uint8))
    return np.concatenate(chunks,axis=0)


def run_study(config_path:Path,bank_path:Path,seed_path:Path,auth_path:Path,out_dir:Path)->dict:
    config=json.loads(config_path.read_text(encoding='utf-8'))
    if config.get('schema')!='qshift-finite-history-study-v1': raise ValueError('unsupported study config')
    auth=validate_authorization(auth_path,seed_path,config)
    bank=TemplateBank.load(bank_path)
    if bank.provenance.get('gate_p')!=.003: raise ValueError('template bank gate p mismatch')
    estimators={}
    for family in config['template_families']:
        estimators[(family,'A')]=CandidateA(bank,family)
        estimators[(family,'B')]=CandidateB(bank,family)
    seeds=json.loads(seed_path.read_text(encoding='utf-8'))
    results=[]; out_dir.mkdir(parents=True,exist_ok=False)
    started=time.perf_counter()
    total_shots=0
    max_rss=int(config['resources']['peak_rss_abort_bytes'])
    for root in seeds['roots']:
        detectors=sample_root(root['segments'])
        total_shots+=len(detectors)
        change_at=(root['segments'][0]['shots'] if len(root['segments'])==2 else None)
        for n in config['history_lengths']:
            for end in range(int(n),len(detectors),int(config['update_block_shots'])):
                history=detectors[end-int(n):end]
                truth_seg=0
                if change_at is not None and end>=change_at:
                    truth_seg=1
                truth=root['segments'][truth_seg]
                for family in config['template_families']:
                    for arm in ('A','B'):
                        estimate=estimators[(family,arm)].estimate(history).to_dict()
                        results.append({'split':root['split'],'scenario':root['scenario'],
                            'root_id':root['root_id'],'history_length':int(n),
                            'history_end_exclusive':end,'next_block_start':end,
                            'truth_p_burst_for_next_block':truth['p_burst'],
                            'truth_p_measurement_for_next_block':truth['p_measurement'],
                            'arm':arm,'template_family':family,**estimate})
        rss_bytes=peak_rss_bytes()
        if rss_bytes>max_rss: raise MemoryError(f'RSS cap exceeded: {rss_bytes}>{max_rss}')
    elapsed=time.perf_counter()-started
    out={'schema':'qshift-finite-history-results-v1','config_sha256':sha256(config_path),
         'template_bank_sha256':sha256(bank_path),'seed_manifest_sha256':auth['seed_manifest_sha256'],
         'authorization_sha256':auth['authorization_sha256'],'stim_version':stim.__version__,
         'study_runner_sha256':sha256(Path(__file__).resolve()),
         'total_shots':total_shots,'root_count':auth['roots'],'record_count':len(results),
         'cpu_wall_elapsed_seconds':elapsed,'peak_rss_bytes':rss_bytes,
         'sampling_scope':'development_only detector bits; no observables returned to estimator',
         'records':results}
    target=out_dir/'finite_history_results.json'
    target.write_text(json.dumps(out,separators=(',',':'))+'\n',encoding='utf-8')
    out['results_sha256']=sha256(target)
    (out_dir/'RUN_MANIFEST.json').write_text(json.dumps({k:v for k,v in out.items() if k!='records'},indent=2)+'\n',encoding='utf-8')
    return out


def main()->None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=HERE/'finite_history_study_config.json')
    parser.add_argument('--templates',type=Path,default=HERE/'template_bank_v1.json')
    parser.add_argument('--seed-manifest',type=Path,required=True)
    parser.add_argument('--authorization-record',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    result=run_study(args.config,args.templates,args.seed_manifest,args.authorization_record,args.output_dir)
    print(json.dumps({k:v for k,v in result.items() if k!='records'},indent=2))


if __name__=='__main__': main()
