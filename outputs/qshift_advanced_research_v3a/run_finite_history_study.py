"""Authorization-gated, causal and resumable finite-history study runner.

This module does not authorize itself. A separate approval record must bind
the exact protocol, config, template bank, runner, estimator and seed manifest.
Unit tests inject deterministic mock detector blocks; the Stim sampler is only
used by the explicitly authorized command-line run path.
"""
from __future__ import annotations

import argparse
from collections.abc import Callable, Iterator
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import time

import numpy as np
import platform
import stim

ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from outputs.phase3a_correlated_noise_preflight.simulator import build_spatial_burst_circuit
from outputs.qshift_advanced_research_v3a.qshift_estimators import (
    CandidateA, CandidateB, TemplateBank, detector_features,
)

HERE=Path(__file__).resolve().parent
PROTOCOL=HERE/'DEVELOPMENT_STUDY_PROTOCOL.md'
ESTIMATOR=HERE/'qshift_estimators.py'
ANALYZER=HERE/'analyze_finite_history_study.py'
TEMPLATE_GENERATOR=HERE/'generate_templates.py'
CIRCUIT_BUILDER=ROOT/'outputs/phase3a_correlated_noise_preflight/simulator.py'
APPROVAL_SCHEMA='qshift-finite-history-approval-v2'
SEED_SCHEMA='qshift-development-seed-manifest-v1'
RUN_SCHEMA='qshift-finite-history-run-v2'
RESULT_SCHEMA='qshift-finite-history-results-v1'


def sha256_bytes(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()


def sha256(path:Path)->str:
    return sha256_bytes(path.read_bytes())


def canonical_json(value:object)->bytes:
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,
                      allow_nan=False).encode('utf-8')


def atomic_write(path:Path,data:bytes)->None:
    """Same-directory temporary + fsync + atomic replace; never partial-write target."""
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix=f'.{path.name}.tmp-',dir=path.parent)
    temp=Path(name)
    try:
        with os.fdopen(fd,'wb') as f:
            f.write(data); f.flush(); os.fsync(f.fileno())
        os.replace(temp,path)
        # Windows does not expose a portable directory-fsync guarantee through
        # Python; file contents are flushed and replacement is same-volume.
    except BaseException:
        try: temp.unlink(missing_ok=True)
        finally: raise


def atomic_json(path:Path,value:object)->None:
    atomic_write(path,json.dumps(value,indent=2,sort_keys=True,ensure_ascii=False,
                                 allow_nan=False).encode('utf-8')+b'\n')


def _required_hashes(config_path:Path,bank_path:Path)->dict[str,str]:
    runtime={'python':platform.python_version(),'numpy':np.__version__,'stim':stim.__version__}
    return {'protocol_sha256':sha256(PROTOCOL),'config_sha256':sha256(config_path),
            'template_bank_sha256':sha256(bank_path),
            'runner_sha256':sha256(Path(__file__).resolve()),
            'estimator_sha256':sha256(ESTIMATOR),
            'analysis_sha256':sha256(ANALYZER),
            'template_generator_sha256':sha256(TEMPLATE_GENERATOR),
            'circuit_builder_sha256':sha256(CIRCUIT_BUILDER),
            'runtime_fingerprint_sha256':sha256_bytes(canonical_json(runtime))}


def _parse_utc(value:str,field:str)->datetime:
    try:
        parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
    except (TypeError,ValueError) as exc:
        raise PermissionError(f'approval {field} must be an ISO-8601 UTC timestamp') from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise PermissionError(f'approval {field} must include a UTC timezone')
    if parsed.utcoffset().total_seconds()!=0:
        raise PermissionError(f'approval {field} must be expressed in UTC')
    return parsed


def validate_seed_manifest(seeds:dict,config:dict,approval:dict,seed_sha:str)->dict:
    if seeds.get('schema')!=SEED_SCHEMA:
        raise ValueError('unsupported seed manifest schema')
    if seeds.get('split_scope')!='development_only':
        raise PermissionError('seed manifest is not marked development_only')
    manifest_id=seeds.get('manifest_id')
    if not isinstance(manifest_id,str) or not manifest_id.strip():
        raise ValueError('seed manifest requires a stable nonempty manifest_id')
    if approval.get('seed_manifest_id')!=manifest_id:
        raise PermissionError('approved seed-manifest identity does not match')
    if approval.get('seed_manifest_sha256')!=seed_sha:
        raise PermissionError('approved seed-manifest SHA-256 does not match')
    expected_counts=config['split_roots_per_condition']
    roots=seeds.get('roots')
    if not isinstance(roots,list): raise ValueError('seed manifest roots must be a list')
    seen=set(); root_ids=set(); seed_values=set(); counts={s:{c:0 for c in config['conditions']} for s in expected_counts}
    by_key={}
    for entry in roots:
        if not isinstance(entry,dict): raise ValueError('each root entry must be an object')
        split,scenario,root_id=entry.get('split'),entry.get('scenario'),entry.get('root_id')
        key=(split,scenario,root_id)
        if key in seen: raise ValueError(f'duplicate root entry {key}')
        seen.add(key)
        if split not in expected_counts or scenario not in config['conditions']:
            raise ValueError(f'unexpected split/scenario {key}')
        if not isinstance(root_id,str) or not root_id.strip(): raise ValueError('root_id must be a nonempty string')
        if root_id in root_ids: raise ValueError(f'root identity reused across conditions or splits: {root_id}')
        root_ids.add(root_id)
        planned=config['conditions'][scenario]; actual=entry.get('segments')
        if not isinstance(actual,list) or len(actual)!=len(planned):
            raise ValueError(f'incorrect segment count for {key}')
        if sum(int(x['shots']) for x in actual)!=config['shots_per_root']:
            raise ValueError(f'shot count mismatch for {key}')
        for seg_index,(got,want) in enumerate(zip(actual,planned)):
            if not isinstance(got,dict): raise ValueError(f'invalid segment in {key}')
            for field in ('shots','p_burst','p_measurement','gate_p'):
                if got.get(field)!=want.get(field):
                    raise ValueError(f'seed manifest condition mismatch for {key} segment {seg_index}: {field}')
            seed=got.get('seed')
            if isinstance(seed,bool) or not isinstance(seed,int) or seed<0 or seed in seed_values:
                raise ValueError('each segment requires a unique nonnegative integer seed')
            seed_values.add(seed)
        counts[split][scenario]+=1; by_key[key]=entry
    for split,n in expected_counts.items():
        if not isinstance(n,int) or n<1: raise ValueError(f'invalid configured root count for {split}')
        for scenario in config['conditions']:
            if counts[split][scenario]!=n:
                raise ValueError(f'expected {n} roots for {split}/{scenario}, found {counts[split][scenario]}')
    total_roots=len(roots); total_shots=total_roots*int(config['shots_per_root'])
    limits=approval['limits']
    if total_roots>limits['max_total_roots'] or total_shots>limits['max_total_shots']:
        raise PermissionError('seed manifest exceeds approved total root/shot limits')
    max_per_condition=max(sum(counts[split][scenario] for split in counts)
                          for scenario in config['conditions'])
    if max_per_condition>limits['max_roots_per_condition']:
        raise PermissionError('seed manifest exceeds approved per-condition root limit')
    if sorted(config['conditions'])!=sorted(limits['allowed_conditions']):
        raise PermissionError('approved conditions do not exactly match study configuration')
    if expected_counts!=limits['roots_per_split_per_condition']:
        raise PermissionError('approved split allocation does not exactly match study configuration')
    if sorted(expected_counts)!=sorted(limits['allowed_splits']):
        raise PermissionError('approved splits do not exactly match study configuration')
    return {'manifest_id':manifest_id,'seed_manifest_sha256':seed_sha,
            'root_count':total_roots,'segment_seed_count':len(seed_values),
            'total_shots':total_shots,'root_entries':by_key}


def validate_authorization(record_path:Path,seed_manifest_path:Path,config_path:Path,
                           bank_path:Path,config:dict,now:datetime|None=None)->dict:
    """Validate executable, study inputs, scope, limits, expiry, and seed identity."""
    if not record_path.is_file(): raise PermissionError('explicit approval record is missing')
    try: approval=json.loads(record_path.read_text(encoding='utf-8'))
    except Exception as exc: raise PermissionError('approval record is unreadable or invalid JSON') from exc
    if approval.get('schema')!=APPROVAL_SCHEMA or approval.get('approved') is not True:
        raise PermissionError('approval record is not an explicit Phase 3B approval')
    if approval.get('scope')!='development_only' or approval.get('protected_data_access') is not False:
        raise PermissionError('approval scope must be development_only with protected access false')
    approved_by,reference=approval.get('approved_by'),approval.get('approval_reference')
    if not isinstance(approved_by,str) or not approved_by.strip() or not isinstance(reference,str) or not reference.strip():
        raise PermissionError('approval requires nonempty approver and approval reference')
    expiry=_parse_utc(approval.get('expires_at_utc',''),'expires_at_utc')
    current=now or datetime.now(timezone.utc)
    if current.tzinfo is None: raise ValueError('clock must be timezone-aware')
    if expiry<=current.astimezone(timezone.utc): raise PermissionError('approval record has expired')
    not_before=approval.get('not_before_utc')
    if not_before and _parse_utc(not_before,'not_before_utc')>current.astimezone(timezone.utc):
        raise PermissionError('approval record is not yet valid')
    hashes=_required_hashes(config_path,bank_path)
    approved_hashes=approval.get('inputs')
    if not isinstance(approved_hashes,dict): raise PermissionError('approval is missing executable input hashes')
    for name,value in hashes.items():
        if approved_hashes.get(name)!=value:
            raise PermissionError(f'approval input hash mismatch: {name}')
    if not seed_manifest_path.is_file(): raise PermissionError('approved seed manifest is missing')
    limits=approval.get('limits')
    required_limits={'max_total_roots','max_roots_per_condition','max_total_shots',
                     'roots_per_split_per_condition','allowed_conditions','allowed_splits',
                     'cpu_time_limit_seconds','peak_rss_limit_bytes'}
    if not isinstance(limits,dict) or not required_limits.issubset(limits):
        raise PermissionError('approval is missing explicit root, condition, CPU, or memory limits')
    for name in ('max_total_roots','max_roots_per_condition','max_total_shots','peak_rss_limit_bytes'):
        value=limits[name]
        if isinstance(value,bool) or not isinstance(value,int) or value<=0:
            raise PermissionError(f'approval limit {name} must be a positive integer')
    if not isinstance(limits['roots_per_split_per_condition'],dict):
        raise PermissionError('approval split/condition root limits must be an object')
    if not isinstance(limits['allowed_conditions'],list) or not all(isinstance(x,str) for x in limits['allowed_conditions']):
        raise PermissionError('approval allowed_conditions must be a list of names')
    if not isinstance(limits['allowed_splits'],list) or not all(isinstance(x,str) for x in limits['allowed_splits']):
        raise PermissionError('approval allowed_splits must be a list of names')
    seed_sha=sha256(seed_manifest_path)
    if approval.get('seed_manifest_sha256')!=seed_sha:
        raise PermissionError('approved seed-manifest SHA-256 does not match')
    try: seeds=json.loads(seed_manifest_path.read_text(encoding='utf-8'))
    except Exception as exc: raise ValueError('seed manifest is unreadable or invalid JSON') from exc
    seed_info=validate_seed_manifest(seeds,config,approval,seed_sha)
    cpu=limits['cpu_time_limit_seconds']; rss=limits['peak_rss_limit_bytes']
    if isinstance(cpu,bool) or not isinstance(cpu,(int,float)) or not math.isfinite(cpu) or cpu<=0:
        raise PermissionError('approval requires a finite positive CPU time limit')
    if isinstance(rss,bool) or not isinstance(rss,int) or rss<=0:
        raise PermissionError('approval requires a positive peak RSS limit')
    if rss>int(config['resources']['peak_rss_abort_bytes']):
        raise PermissionError('approved memory limit exceeds configured hard memory cap')
    return {'approval_sha256':sha256(record_path),'inputs':hashes,
            'seed_manifest_sha256':seed_sha,'seed_manifest_id':seed_info['manifest_id'],
            'root_count':seed_info['root_count'],'segment_seed_count':seed_info['segment_seed_count'],
            'total_shots':seed_info['total_shots'],'root_entries':seed_info['root_entries'],
            'approved_by':approved_by,'approval_reference':reference,
            'limits':limits}


def peak_rss_bytes()->int:
    try:
        import psutil
        info=psutil.Process().memory_info()
        if os.name=='nt' and getattr(info,'peak_wset',None) is not None:
            return int(info.peak_wset)
        if os.name!='nt':
            import resource
            value=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            return int(value if sys.platform=='darwin' else value*1024)
        return int(info.rss)
    except ImportError:
        if os.name=='nt':
            import ctypes
            from ctypes import wintypes
            class Counters(ctypes.Structure):
                _fields_=[('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD),
                    ('PeakWorkingSetSize',ctypes.c_size_t),('WorkingSetSize',ctypes.c_size_t),
                    ('QuotaPeakPagedPoolUsage',ctypes.c_size_t),('QuotaPagedPoolUsage',ctypes.c_size_t),
                    ('QuotaPeakNonPagedPoolUsage',ctypes.c_size_t),('QuotaNonPagedPoolUsage',ctypes.c_size_t),
                    ('PagefileUsage',ctypes.c_size_t),('PeakPagefileUsage',ctypes.c_size_t)]
            c=Counters(); c.cb=ctypes.sizeof(c)
            ok=ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.windll.kernel32.GetCurrentProcess(),ctypes.byref(c),c.cb)
            if not ok: raise OSError('GetProcessMemoryInfo failed')
            return int(c.PeakWorkingSetSize)
        import resource
        value=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return int(value if sys.platform=='darwin' else value*1024)


def check_resource_limits(rss:int,elapsed:float,limits:dict)->None:
    if rss>int(limits['peak_rss_limit_bytes']):
        raise MemoryError(f'peak RSS limit exceeded: {rss}>{limits["peak_rss_limit_bytes"]}')
    if elapsed>float(limits['cpu_time_limit_seconds']):
        raise TimeoutError(f'CPU time limit exceeded: {elapsed:.3f}>{limits["cpu_time_limit_seconds"]}')


def acquire_lock(path:Path)->None:
    if path.exists():
        try: owner=json.loads(path.read_text(encoding='utf-8')).get('pid')
        except Exception as exc: raise RuntimeError(f'run lock is malformed at {path}; inspect before resuming') from exc
        if isinstance(owner,bool) or not isinstance(owner,int) or owner<=0:
            raise RuntimeError(f'run lock has no valid PID at {path}; inspect before resuming')
        try:
            import psutil
            active=psutil.pid_exists(owner)
        except ImportError:
            try: os.kill(owner,0); active=True
            except ProcessLookupError: active=False
            except PermissionError: raise RuntimeError(f'run lock belongs to an inaccessible process {owner}')
            except OSError as exc:
                if os.name=='nt' and getattr(exc,'winerror',None) in (87,1168): active=False
                else: raise RuntimeError(f'cannot verify whether run-lock PID {owner} is active') from exc
        if active: raise RuntimeError(f'run is already active under PID {owner}')
        path.unlink(missing_ok=True)
    try:
        with path.open('x',encoding='utf-8') as f:
            f.write(json.dumps({'pid':os.getpid(),'created_utc':datetime.now(timezone.utc).isoformat()}))
            f.flush(); os.fsync(f.fileno())
    except FileExistsError as exc:
        raise RuntimeError(f'run lock exists at {path}; verify no process is active before removing a stale lock') from exc


def atomic_root_result(path:Path,payload:dict)->str:
    payload_bytes=canonical_json(payload)
    envelope={'payload':payload,'payload_sha256':sha256_bytes(payload_bytes)}
    atomic_json(path,envelope)
    return sha256(path)


def read_root_result(path:Path,expected_fingerprint:str)->dict:
    try: envelope=json.loads(path.read_text(encoding='utf-8'))
    except Exception as exc: raise ValueError(f'corrupt root checkpoint JSON: {path.name}') from exc
    payload=envelope.get('payload')
    if not isinstance(payload,dict) or envelope.get('payload_sha256')!=sha256_bytes(canonical_json(payload)):
        raise ValueError(f'root checkpoint checksum mismatch: {path.name}')
    if payload.get('run_fingerprint')!=expected_fingerprint:
        raise ValueError(f'root checkpoint belongs to different inputs: {path.name}')
    return payload


def root_token(key:tuple[str,str,str])->str:
    return sha256_bytes(canonical_json(list(key)))


class StimSegmentSampler:
    """Persistent seeded sampler; callers request only the next causal block."""
    def __init__(self,segment:dict):
        circuit=build_spatial_burst_circuit(gate_p=float(segment['gate_p']),
            measurement_p=float(segment['p_measurement']),burst_probability=float(segment['p_burst']))
        self.sampler=circuit.compile_detector_sampler(seed=int(segment['seed']))

    def sample(self,shots:int)->np.ndarray:
        d=self.sampler.sample(shots=shots,append_observables=False)
        if d.shape!=(shots,40): raise RuntimeError('Stim returned an unexpected detector shape')
        return np.asarray(d,dtype=np.uint8)


def causal_root_records(root:dict,config:dict,estimators:dict,
                        sampler_factory:Callable[[dict],object]=StimSegmentSampler,
                        rss_check:Callable[[],int]=peak_rss_bytes)->list[dict]:
    """Replay one stream online: estimate from past rows, then sample next block."""
    total=int(config['shots_per_root']); block=int(config['update_block_shots'])
    history_lengths=[int(x) for x in config['history_lengths']]
    detectors=np.empty((total,40),dtype=np.uint8); records=[]; pos=0
    for seg_index,segment in enumerate(root['segments']):
        sampler=sampler_factory(segment)
        remaining=int(segment['shots'])
        while remaining:
            if pos%block:
                raise ValueError('segment/update boundary is not aligned with frozen 100-shot chronology')
            current=segment
            for n in history_lengths:
                if pos>=n and (pos-n)%block==0:
                    history=detectors[pos-n:pos]
                    feature_mean=detector_features(history).mean(axis=0)
                    for family in config['template_families']:
                        for arm in ('A','B'):
                            estimate=estimators[(family,arm)].estimate_mean(feature_mean,history_length=n).to_dict()
                            records.append({'split':root['split'],'scenario':root['scenario'],
                                'root_id':root['root_id'],'history_length':n,
                                'history_end_exclusive':pos,'next_block_start':pos,
                                'truth_p_burst':current['p_burst'],
                                'truth_p_measurement':current['p_measurement'],
                                'truth_p_burst_for_next_block':current['p_burst'],
                                'truth_p_measurement_for_next_block':current['p_measurement'],
                                'arm':arm,'template_family':family,**estimate})
            take=min(block,remaining,total-pos)
            chunk=np.asarray(sampler.sample(take))
            if chunk.shape!=(take,40) or not np.isin(chunk,(0,1)).all():
                raise RuntimeError('detector sampler returned invalid detector block')
            detectors[pos:pos+take]=chunk.astype(np.uint8,copy=False)
            pos+=take; remaining-=take
            rss_check()
    if pos!=total: raise RuntimeError(f'root produced {pos} of {total} planned shots')
    return records


def _validate_config(config:dict)->None:
    if config.get('schema')!='qshift-finite-history-study-v1': raise ValueError('unsupported study config')
    if config.get('decoder_evaluation') is not False or config.get('protected_test_access') is not False:
        raise PermissionError('config scope includes prohibited decoder or protected-data access')
    if config.get('sampling_authorized') is not False or config.get('status')!='proposal_not_authorized':
        raise ValueError('study config must remain the unapproved proposal bound by separate authorization')
    if config.get('template_families')!=['exact_categorical','approximate_dem']:
        raise ValueError('template family order/scope differs from frozen proposal')
    if config.get('history_lengths')!=[200,1000,5000,10000] or config.get('update_block_shots')!=100:
        raise ValueError('history windows or update block differs from frozen protocol')
    run_mode=config.get('run_mode','full_proposed_study')
    if run_mode=='full_proposed_study':
        expected_splits={'development':20,'heldout_development':40}
    elif run_mode=='development_pipeline_pilot':
        expected_splits={'development':2}
    else:
        raise ValueError('unknown run mode; only frozen full proposal and bounded dev pilot are supported')
    if config.get('shots_per_root')!=10100 or config.get('split_roots_per_condition')!=expected_splits:
        raise ValueError('root shot count or split allocation differs from the selected frozen proposal')
    frozen_conditions={
        'stationary_nominal':[{'shots':10100,'p_burst':.008,'p_measurement':.003,'gate_p':.003}],
        'measurement_step_up':[{'shots':5000,'p_burst':.008,'p_measurement':.003,'gate_p':.003},
                               {'shots':5100,'p_burst':.008,'p_measurement':.006,'gate_p':.003}],
        'measurement_step_down':[{'shots':5000,'p_burst':.008,'p_measurement':.006,'gate_p':.003},
                                 {'shots':5100,'p_burst':.008,'p_measurement':.003,'gate_p':.003}],
        'gate_low_stationary':[{'shots':10100,'p_burst':.008,'p_measurement':.003,'gate_p':.002}],
        'gate_high_stationary':[{'shots':10100,'p_burst':.008,'p_measurement':.003,'gate_p':.004}],
    }
    if config.get('conditions')!=frozen_conditions:
        raise ValueError('condition values or transition schedule differs from frozen protocol')
    if config.get('template_calibration',{}).get('sampled_shots')!=0:
        raise ValueError('frozen proposal uses deterministic population templates only')
    if config.get('inference',{}).get('resampling') is not False:
        raise ValueError('frozen analysis does not permit resampling')
    resources=config.get('resources',{})
    if resources.get('peak_rss_abort_bytes')!=2*1024**3 or resources.get('cpu_time_limit_seconds') is not None:
        raise ValueError('resource proposal differs from the documented 2 GiB cap / owner-set CPU limit')
    for name,segments in config['conditions'].items():
        if sum(int(s['shots']) for s in segments)!=int(config['shots_per_root']):
            raise ValueError(f'condition {name} does not match configured root length')
        transition=0
        for s in segments[:-1]: transition+=int(s['shots'])
        if transition and transition%int(config['update_block_shots']):
            raise ValueError(f'condition {name} transition is not update-block aligned')


def _expected_run(config_path:Path,bank_path:Path,approval:dict)->dict:
    return {'schema':RUN_SCHEMA,'input_hashes':approval['inputs'],
            'seed_manifest_sha256':approval['seed_manifest_sha256'],
            'seed_manifest_id':approval['seed_manifest_id'],
            'approval_sha256':approval['approval_sha256'],
            'approval_reference':approval['approval_reference'],
            'approved_by':approval['approved_by'],
            'limits':approval['limits'],
            'config_sha256':sha256(config_path),'template_bank_sha256':sha256(bank_path)}


def _root_payload(path:Path,fingerprint:str,expected_root_hash:str)->dict:
    payload=read_root_result(path,fingerprint)
    if payload.get('root_manifest_entry_sha256')!=expected_root_hash:
        raise ValueError(f'root checkpoint seed identity mismatch: {path.name}')
    records=payload.get('records')
    if not isinstance(records,list): raise ValueError(f'root checkpoint records missing: {path.name}')
    return payload


def _recover_temporary_files(run_dir:Path,roots_dir:Path,root_entries:dict,
                             fingerprint:str)->None:
    """Promote complete atomic root temps; quarantine partial temps as evidence."""
    quarantine=run_dir/'incomplete_checkpoints'
    targets={f'{root_token(k)}.json':k for k in root_entries}
    for temp in list(roots_dir.iterdir()):
        if not temp.name.startswith('.') or '.tmp-' not in temp.name: continue
        match=next((name for name in targets if temp.name.startswith(f'.{name}.tmp-')),None)
        if match is None: raise ValueError(f'unrecognized temporary checkpoint: {temp.name}')
        key=targets[match]; expected_hash=sha256_bytes(canonical_json(root_entries[key]))
        target=roots_dir/match
        try:
            envelope=json.loads(temp.read_text(encoding='utf-8'))
        except Exception:
            envelope=None
        payload=envelope.get('payload') if isinstance(envelope,dict) else None
        intact=(isinstance(payload,dict) and
                envelope.get('payload_sha256')==sha256_bytes(canonical_json(payload)))
        if intact:
            if payload.get('run_fingerprint')!=fingerprint:
                raise ValueError(f'temporary checkpoint belongs to different inputs: {temp.name}')
            if payload.get('root_manifest_entry_sha256')!=expected_hash:
                raise ValueError(f'temporary checkpoint seed identity mismatch: {temp.name}')
            if not isinstance(payload.get('records'),list):
                raise ValueError(f'temporary checkpoint has invalid records: {temp.name}')
        else:
            quarantine.mkdir(exist_ok=True)
            dest=quarantine/f'{temp.name}.incomplete'
            if dest.exists(): raise ValueError(f'quarantine target already exists: {dest.name}')
            os.replace(temp,dest)
            continue
        if target.exists():
            # Never replace an existing checkpoint, even with a valid temp.
            quarantine.mkdir(exist_ok=True)
            dest=quarantine/f'{temp.name}.duplicate'
            if dest.exists(): raise ValueError(f'quarantine target already exists: {dest.name}')
            os.replace(temp,dest)
        else:
            os.replace(temp,target)
    for temp in list(run_dir.iterdir()):
        if temp.is_dir() or not temp.name.startswith('.') or '.tmp-' not in temp.name: continue
        if temp.name.startswith('.RUN_MANIFEST.json.tmp-') or temp.name.startswith('.finite-history.tmp-'):
            quarantine.mkdir(exist_ok=True)
            dest=quarantine/f'{temp.name}.incomplete'
            if dest.exists(): raise ValueError(f'quarantine target already exists: {dest.name}')
            os.replace(temp,dest)
        elif temp.name!='.':
            raise ValueError(f'unrecognized incomplete run file: {temp.name}')


def _manifest_write(run_dir:Path,run_base:dict,completed:dict,total_shots:int,status:str,
                    extra:dict|None=None)->dict:
    manifest={**run_base,'run_fingerprint':sha256_bytes(canonical_json(run_base)),
              'completed_roots':dict(sorted(completed.items())),
              'completed_root_count':len(completed),'completed_shots':total_shots,'status':status}
    if extra: manifest.update(extra)
    atomic_json(run_dir/'RUN_MANIFEST.json',manifest)
    return manifest


def _root_key_string(key:tuple[str,str,str])->str:
    return '|'.join(key)


def _iter_root_keys(root_entries:dict)->Iterator[tuple[str,str,str]]:
    return iter(sorted(root_entries))


def _write_final_results(run_dir:Path,root_entries:dict,completed:dict,expected_fingerprint:str,
                         run_base:dict,stim_version:str)->str:
    target=run_dir/'finite_history_results.json'
    fd,name=tempfile.mkstemp(prefix='.finite-history.tmp-',dir=run_dir)
    temp=Path(name)
    meta={**run_base,'schema':RESULT_SCHEMA,'run_fingerprint':expected_fingerprint,
          'stim_version':stim_version,'root_count':len(root_entries),
          'total_shots':sum(int(x['shots']) for e in root_entries.values() for x in e['segments']),
          'completed_root_count':len(completed),'sampling_scope':'development_only detector bits; no observables returned to estimator'}
    try:
        with os.fdopen(fd,'wb') as f:
            prefix=canonical_json(meta)[:-1]+b',"records":['
            f.write(prefix); first=True
            for key in _iter_root_keys(root_entries):
                entry=root_entries[key]; path=run_dir/'root_results'/f'{root_token(key)}.json'
                payload=_root_payload(path,expected_fingerprint,sha256_bytes(canonical_json(entry)))
                if completed.get(_root_key_string(key))!=sha256(path):
                    raise ValueError(f'root checkpoint file hash differs from manifest: {path.name}')
                for record in payload['records']:
                    if not first: f.write(b',')
                    first=False; f.write(canonical_json(record))
            f.write(b']}\n'); f.flush(); os.fsync(f.fileno())
        os.replace(temp,target)
    except BaseException:
        temp.unlink(missing_ok=True); raise
    return sha256(target)


def run_study(config_path:Path,bank_path:Path,seed_path:Path,auth_path:Path,out_dir:Path,
              sampler_factory:Callable[[dict],object]=StimSegmentSampler)->dict:
    config=json.loads(config_path.read_text(encoding='utf-8')); _validate_config(config)
    approval=validate_authorization(auth_path,seed_path,config_path,bank_path,config)
    bank=TemplateBank.load(bank_path)
    if bank.provenance.get('gate_p')!=.003: raise ValueError('template bank gate p mismatch')
    estimators={(family,arm):(CandidateA(bank,family) if arm=='A' else CandidateB(bank,family))
                for family in config['template_families'] for arm in ('A','B')}
    seeds=json.loads(seed_path.read_text(encoding='utf-8'))
    root_entries=approval['root_entries']; run_base=_expected_run(config_path,bank_path,approval)
    fingerprint=sha256_bytes(canonical_json(run_base))
    run_dir=out_dir.resolve(); run_dir.mkdir(parents=True,exist_ok=True)
    lock=run_dir/'RUNNING.lock'; acquire_lock(lock)
    try:
        roots_dir=run_dir/'root_results'; roots_dir.mkdir(exist_ok=True)
        _recover_temporary_files(run_dir,roots_dir,approval['root_entries'],fingerprint)
        manifest_path=run_dir/'RUN_MANIFEST.json'; completed={}
        original_status=None
        if manifest_path.exists():
            try: manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
            except Exception as exc: raise ValueError('run manifest is corrupt JSON; refusing resume') from exc
            for k,v in run_base.items():
                if manifest.get(k)!=v: raise ValueError(f'resume input mismatch: {k}')
            if manifest.get('run_fingerprint')!=fingerprint: raise ValueError('resume fingerprint mismatch')
            original_status=manifest.get('status')
            completed=manifest.get('completed_roots')
            if not isinstance(completed,dict): raise ValueError('run manifest completed_roots is corrupt')
            for key,value in completed.items():
                match=[k for k in root_entries if _root_key_string(k)==key]
                if len(match)!=1: raise ValueError(f'checkpoint includes unapproved root identity {key}')
                path=roots_dir/f'{root_token(match[0])}.json'
                if not path.is_file() or sha256(path)!=value:
                    raise ValueError(f'completed root checkpoint missing or corrupted: {key}')
                _root_payload(path,fingerprint,sha256_bytes(canonical_json(root_entries[match[0]])))
            allowed_top={'RUN_MANIFEST.json','root_results','finite_history_results.json','RUNNING.lock','incomplete_checkpoints'}
            unexpected={p.name for p in run_dir.iterdir()}-allowed_top
            if unexpected: raise ValueError(f'unexpected output directory entries: {sorted(unexpected)}')
            expected_files={f'{root_token(k)}.json' for k in root_entries}
            for p in roots_dir.iterdir():
                if p.name.startswith('.'): raise ValueError(f'incomplete temporary checkpoint could not be recovered: {p.name}')
                if p.name not in expected_files: raise ValueError(f'unexpected file in checkpoint directory: {p.name}')
                key=next(k for k in root_entries if f'{root_token(k)}.json'==p.name)
                _root_payload(p,fingerprint,sha256_bytes(canonical_json(root_entries[key])))
                root_key=_root_key_string(key); file_hash=sha256(p)
                if root_key in completed and completed[root_key]!=file_hash:
                    raise ValueError(f'checkpoint manifest disagrees with root artifact: {root_key}')
                completed.setdefault(root_key,file_hash)
            if original_status=='complete':
                result_path=run_dir/'finite_history_results.json'
                if not result_path.is_file() or manifest.get('results_sha256')!=sha256(result_path):
                    raise ValueError('complete run result is missing or corrupted')
                if len(completed)!=len(root_entries): raise ValueError('complete run has missing root checkpoints')
                return manifest
        elif any(run_dir.iterdir()):
            # Existing unknown or partial data is never silently overwritten.
            allowed={roots_dir.name,'RUNNING.lock','incomplete_checkpoints'}
            if set(p.name for p in run_dir.iterdir())-allowed:
                raise ValueError('output directory contains data but no valid RUN_MANIFEST.json')
        # Validate/recover root artifacts before any new root can be sampled.
        expected_files={f'{root_token(k)}.json' for k in root_entries}
        for p in roots_dir.iterdir():
            if p.name.startswith('.'): raise ValueError(f'incomplete temporary checkpoint could not be recovered: {p.name}')
            if p.name not in expected_files: raise ValueError(f'unexpected file in checkpoint directory: {p.name}')
            key=next(k for k in root_entries if f'{root_token(k)}.json'==p.name)
            _root_payload(p,fingerprint,sha256_bytes(canonical_json(root_entries[key])))
            root_key=_root_key_string(key); file_hash=sha256(p)
            if root_key in completed and completed[root_key]!=file_hash:
                raise ValueError(f'checkpoint manifest disagrees with root artifact: {root_key}')
            completed.setdefault(root_key,file_hash)
        initial_rss=peak_rss_bytes()
        check_resource_limits(initial_rss,0,approval['limits'])
        manifest=_manifest_write(run_dir,run_base,completed,
                                 sum(int(s['shots']) for k in root_entries if _root_key_string(k) in completed for s in root_entries[k]['segments']),
                                 'in_progress')
        started=time.perf_counter()
        for key in _iter_root_keys(root_entries):
            key_string=_root_key_string(key)
            if key_string in completed: continue
            expected_entry_hash=sha256_bytes(canonical_json(root_entries[key]))
            target=roots_dir/f'{root_token(key)}.json'
            if target.exists():
                payload=_root_payload(target,fingerprint,expected_entry_hash)
                completed[key_string]=sha256(target)
            else:
                root={**root_entries[key]}
                def resource_check()->int:
                    rss_now=peak_rss_bytes()
                    check_resource_limits(rss_now,time.perf_counter()-started,approval['limits'])
                    return rss_now
                records=causal_root_records(root,config,estimators,sampler_factory=sampler_factory,
                                            rss_check=resource_check)
                rss=resource_check(); elapsed=time.perf_counter()-started
                payload={'schema':'qshift-root-checkpoint-v1','root_key':list(key),
                         'root_manifest_entry_sha256':expected_entry_hash,
                         'run_fingerprint':fingerprint,'records':records}
                completed[key_string]=atomic_root_result(target,payload)
            total_done=sum(int(s['shots']) for k in root_entries if _root_key_string(k) in completed for s in root_entries[k]['segments'])
            _manifest_write(run_dir,run_base,completed,total_done,'in_progress')
        # A valid root file written just before a crash but before the index
        # update is adopted only after its full input and internal checksum validate.
        expected_files={f'{root_token(k)}.json' for k in root_entries}
        for p in roots_dir.iterdir():
            if p.name.startswith('.'): raise ValueError(f'incomplete temporary checkpoint requires inspection: {p.name}')
            if p.name not in expected_files: raise ValueError(f'unexpected file in checkpoint directory: {p.name}')
            key=next(k for k in root_entries if f'{root_token(k)}.json'==p.name)
            _root_payload(p,fingerprint,sha256_bytes(canonical_json(root_entries[key])))
            completed.setdefault(_root_key_string(key),sha256(p))
        if len(completed)!=len(root_entries): raise ValueError('not all approved roots have valid checkpoints')
        results_sha=_write_final_results(run_dir,root_entries,completed,fingerprint,run_base,stim.__version__)
        elapsed=time.perf_counter()-started; rss=peak_rss_bytes()
        check_resource_limits(rss,elapsed,approval['limits'])
        done=_manifest_write(run_dir,run_base,completed,approval['total_shots'],'complete',
            {'results_sha256':results_sha,'cpu_wall_elapsed_seconds':elapsed,'peak_rss_bytes':rss})
        return done
    finally:
        lock.unlink(missing_ok=True)


def main()->None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=HERE/'finite_history_study_config.json')
    parser.add_argument('--templates',type=Path,default=HERE/'template_bank_v1.json')
    parser.add_argument('--seed-manifest',type=Path,required=True)
    parser.add_argument('--authorization-record',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    result=run_study(args.config,args.templates,args.seed_manifest,args.authorization_record,args.output_dir)
    print(json.dumps(result,indent=2,sort_keys=True))


if __name__=='__main__': main()
