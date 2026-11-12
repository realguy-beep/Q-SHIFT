from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock

import numpy as np

ROOT=Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from outputs.qshift_advanced_research_v3a import run_finite_history_study as runner
from outputs.qshift_advanced_research_v3a.qshift_estimators import (
    A_GRID, BURST_KNOTS, CandidateA, CandidateB, FEATURE_COUNT, FIT_BURST_GRID,
    FIT_MEASUREMENT_GRID, TemplateBank, bilinear,
)

BASE=Path(__file__).resolve().parents[1]
BANK=BASE/'template_bank_v1.json'


class FakeEstimator:
    def __init__(self): self.seen=[]
    def estimate_mean(self,mean,history_length=None):
        self.seen.append((int(history_length),float(mean[0])))
        return FakeEstimate(float(mean[0]))


class FakeEstimate:
    def __init__(self,value): self.value=value
    def to_dict(self):
        return {'p_burst':self.value,'p_measurement':.003,'objective':0.,
                'boundary_hit':False,'estimator':'mock','family':'exact_categorical'}


class ConstantSampler:
    def __init__(self,value): self.value=value
    def sample(self,shots): return np.full((shots,40),self.value,dtype=np.uint8)


class Phase3BRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.bank=TemplateBank.load(BANK)

    def _fixture(self,root:Path):
        config=json.loads((BASE/'finite_history_study_config.json').read_text(encoding='utf-8'))
        config['split_roots_per_condition']={'development':1,'heldout_development':2}
        config_path=root/'config.json'; config_path.write_text(json.dumps(config),encoding='utf-8')
        roots=[]; seed=1000
        for split,count in config['split_roots_per_condition'].items():
            for scenario,segments in config['conditions'].items():
                for i in range(count):
                    copied=[]
                    for seg in segments:
                        copied.append({**seg,'seed':seed}); seed+=1
                    roots.append({'split':split,'scenario':scenario,
                                  'root_id':f'{split}-{scenario}-{i}','segments':copied})
        seed_manifest={'schema':runner.SEED_SCHEMA,'manifest_id':'test-fixture-2026-01',
                       'split_scope':'development_only','roots':roots}
        seed_path=root/'seed-manifest.json'; seed_path.write_text(json.dumps(seed_manifest),encoding='utf-8')
        hashes=runner._required_hashes(config_path,BANK)
        limits={'max_total_roots':15,'max_roots_per_condition':3,'max_total_shots':151500,
                'roots_per_split_per_condition':config['split_roots_per_condition'],
                'allowed_conditions':sorted(config['conditions']),'allowed_splits':['development','heldout_development'],
                'cpu_time_limit_seconds':600,'peak_rss_limit_bytes':config['resources']['peak_rss_abort_bytes']}
        approval={'schema':runner.APPROVAL_SCHEMA,'approved':True,'scope':'development_only',
            'protected_data_access':False,'approved_by':'unit-test-fixture','approval_reference':'test-only/no-experiment',
            'expires_at_utc':'2099-01-01T00:00:00Z','inputs':hashes,
            'seed_manifest_id':seed_manifest['manifest_id'],'seed_manifest_sha256':runner.sha256(seed_path),
            'limits':limits}
        auth_path=root/'approval.json'; auth_path.write_text(json.dumps(approval),encoding='utf-8')
        return config,config_path,seed_path,auth_path,roots

    def _factory(self,fail_at=None):
        state={'constructors':0}
        def factory(segment):
            state['constructors']+=1
            if fail_at is not None and state['constructors']==fail_at:
                raise RuntimeError('synthetic interruption')
            return ConstantSampler(int(float(segment['p_measurement'])>=.006))
        factory.state=state
        return factory

    def _run_with_mock_estimators(self,*args,**kwargs):
        with mock.patch.object(runner,'CandidateA',side_effect=lambda bank,family:FakeEstimator()), \
             mock.patch.object(runner,'CandidateB',side_effect=lambda bank,family:FakeEstimator()), \
             mock.patch.object(runner,'_validate_config'), \
             mock.patch.object(runner,'causal_root_records',side_effect=self._synthetic_root_records):
            return runner.run_study(*args,**kwargs)

    @staticmethod
    def _synthetic_root_records(root,config,estimators,**kwargs):
        records=[]; total=config['shots_per_root']; step=config['update_block_shots']
        change=sum(int(x['shots']) for x in root['segments'][:-1])
        for pos in range(0,total,step):
            if pos>=total: break
            seg=root['segments'][1] if len(root['segments'])>1 and pos>=change else root['segments'][0]
            for n in config['history_lengths']:
                n=int(n)
                if pos>=n and (pos-n)%step==0:
                    for family in config['template_families']:
                        for arm in ('A','B'):
                            p_b=.009 if arm=='A' else .008
                            records.append({'split':root['split'],'scenario':root['scenario'],
                                'root_id':root['root_id'],'history_length':n,
                                'history_end_exclusive':pos,'next_block_start':pos,
                                'truth_p_burst':seg['p_burst'],'truth_p_measurement':seg['p_measurement'],
                                'truth_p_burst_for_next_block':seg['p_burst'],
                                'truth_p_measurement_for_next_block':seg['p_measurement'],
                                'arm':arm,'template_family':family,'p_burst':p_b,'p_measurement':.003,
                                'objective':0.,'boundary_hit':False})
        return records

    def test_causal_history_and_transition_boundaries(self):
        config={'shots_per_root':8,'update_block_shots':2,'history_lengths':[2,4],
                'template_families':['exact_categorical']}
        root={'split':'development','scenario':'measurement_step_up','root_id':'causal-test',
            'segments':[{'shots':4,'p_burst':.008,'p_measurement':.003,'gate_p':.003},
                        {'shots':4,'p_burst':.008,'p_measurement':.006,'gate_p':.003}]}
        estimators={(f,a):FakeEstimator() for f in config['template_families'] for a in ('A','B')}
        rows=runner.causal_root_records(root,config,estimators,
            sampler_factory=lambda seg:ConstantSampler(int(seg['p_measurement']>=.006)),rss_check=lambda:1)
        ends=sorted(set(r['history_end_exclusive'] for r in rows))
        self.assertEqual(ends,[2,4,6])
        at4=[r for r in rows if r['history_end_exclusive']==4]
        self.assertTrue(all(r['truth_p_measurement']==.006 for r in at4))
        # At the change boundary, a 4-shot history is entirely old data.
        seen=estimators[('exact_categorical','A')].seen
        self.assertIn((4,0.0),seen)
        # At end=6, trailing 4 rows contain two old and two new detector rows.
        self.assertIn((4,.5),seen)
        self.assertTrue(all(r['next_block_start']==r['history_end_exclusive'] for r in rows))

    def test_frozen_config_scope_and_conditions_are_enforced(self):
        config=json.loads((BASE/'finite_history_study_config.json').read_text())
        runner._validate_config(config)
        pilot=json.loads((BASE/'finite_history_pilot_config.json').read_text())
        runner._validate_config(pilot)
        self.assertEqual(pilot['split_roots_per_condition'],{'development':2})
        changed=json.loads(json.dumps(config)); changed['conditions']['measurement_step_up'][1]['p_measurement']=.007
        with self.assertRaisesRegex(ValueError,'condition values'):
            runner._validate_config(changed)
        changed=json.loads(json.dumps(config)); changed['split_roots_per_condition']['heldout_development']=39
        with self.assertRaisesRegex(ValueError,'split allocation'):
            runner._validate_config(changed)

    def test_authorization_fails_closed_missing_hash_scope_expiry_and_seed_id(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td); _,cp,sp,ap,_=self._fixture(d)
            with self.assertRaises(PermissionError):
                runner.validate_authorization(d/'absent.json',sp,cp,BANK,json.loads(cp.read_text()))
            approval=json.loads(ap.read_text()); approval['inputs']['runner_sha256']='0'*64
            ap.write_text(json.dumps(approval))
            with self.assertRaisesRegex(PermissionError,'runner_sha256'):
                runner.validate_authorization(ap,sp,cp,BANK,json.loads(cp.read_text()))
            valid=json.loads(ap.read_text()); valid['inputs']=runner._required_hashes(cp,BANK)
            for field in valid['inputs']:
                changed=json.loads(json.dumps(valid)); changed['inputs'][field]='0'*64
                ap.write_text(json.dumps(changed))
                with self.assertRaisesRegex(PermissionError,'input hash mismatch'):
                    runner.validate_authorization(ap,sp,cp,BANK,json.loads(cp.read_text()))
            ap.write_text(json.dumps(valid))
            changed_seed=json.loads(sp.read_text()); changed_seed['manifest_id']='tampered'
            sp.write_text(json.dumps(changed_seed))
            with self.assertRaisesRegex(PermissionError,'seed-manifest SHA-256'):
                runner.validate_authorization(ap,sp,cp,BANK,json.loads(cp.read_text()))
            changed_config=json.loads(cp.read_text()); changed_config['shots_per_root']+=1
            cp.write_text(json.dumps(changed_config))
            with self.assertRaisesRegex(PermissionError,'config_sha256'):
                runner.validate_authorization(ap,sp,cp,BANK,changed_config)
            # Restore a coherent ephemeral fixture; no approval or seeds persist.
            _,cp,sp,ap,_=self._fixture(d)
            approval=json.loads(ap.read_text())
            approval['scope']='protected_evaluation'; ap.write_text(json.dumps(approval))
            with self.assertRaises(PermissionError):
                runner.validate_authorization(ap,sp,cp,BANK,json.loads(cp.read_text()))
            approval=json.loads(ap.read_text()); approval['scope']='development_only'
            approval['expires_at_utc']='2020-01-01T00:00:00Z'; ap.write_text(json.dumps(approval))
            with self.assertRaisesRegex(PermissionError,'expired'):
                runner.validate_authorization(ap,sp,cp,BANK,json.loads(cp.read_text()),now=datetime(2026,1,1,tzinfo=timezone.utc))

    def test_seed_manifest_rejects_duplicate_seed_ids_bad_identity_and_protected_scope(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td); config,cp,sp,ap,roots=self._fixture(d); approval=json.loads(ap.read_text())
            seeds=json.loads(sp.read_text()); seeds['roots'][1]['segments'][0]['seed']=seeds['roots'][0]['segments'][0]['seed']
            with self.assertRaisesRegex(ValueError,'unique'):
                runner.validate_seed_manifest(seeds,config,approval,approval['seed_manifest_sha256'])
            seeds=json.loads(sp.read_text()); seeds['manifest_id']='different-id'
            with self.assertRaisesRegex(PermissionError,'identity'):
                runner.validate_seed_manifest(seeds,config,approval,approval['seed_manifest_sha256'])
            seeds=json.loads(sp.read_text()); seeds['split_scope']='protected'
            with self.assertRaises(PermissionError):
                runner.validate_seed_manifest(seeds,config,approval,approval['seed_manifest_sha256'])
            seeds=json.loads(sp.read_text()); seeds['roots'].append(seeds['roots'][0])
            with self.assertRaisesRegex(ValueError,'duplicate root'):
                runner.validate_seed_manifest(seeds,config,approval,approval['seed_manifest_sha256'])
            seeds=json.loads(sp.read_text()); seeds['roots'][1]['root_id']=seeds['roots'][0]['root_id']
            with self.assertRaisesRegex(ValueError,'reused across conditions or splits'):
                runner.validate_seed_manifest(seeds,config,approval,approval['seed_manifest_sha256'])
            seeds=json.loads(sp.read_text()); too_few=json.loads(json.dumps(approval))
            too_few['limits']['max_roots_per_condition']=2
            with self.assertRaisesRegex(PermissionError,'per-condition root limit'):
                runner.validate_seed_manifest(seeds,config,too_few,too_few['seed_manifest_sha256'])

    def test_runner_completion_analysis_compatibility_pairing_and_order(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td); _,cp,sp,ap,roots=self._fixture(d); out=d/'run'
            manifest=self._run_with_mock_estimators(cp,BANK,sp,ap,out)
            self.assertEqual(manifest['status'],'complete')
            self.assertEqual(manifest['completed_root_count'],15)
            payload=json.loads((out/'finite_history_results.json').read_text())
            self.assertEqual(payload['schema'],runner.RESULT_SCHEMA)
            self.assertEqual(len(payload['records']),15*968)
            self.assertEqual(payload['total_shots'],151500)
            rows=payload['records']
            ids=[(r['split'],r['scenario'],r['root_id'],r['history_end_exclusive'],
                  r['history_length'],r['template_family'],r['arm']) for r in rows]
            family_order={'exact_categorical':0,'approximate_dem':1}
            ordering=lambda x:(x[0],x[1],x[2],x[3],x[4],family_order[x[5]],x[6])
            self.assertTrue(ids==sorted(ids,key=ordering),'results are not in deterministic declared order')
            from outputs.qshift_advanced_research_v3a.analyze_finite_history_study import analyze_payload
            analysis=analyze_payload(payload)
            self.assertEqual(analysis['primary_strata']['measurement_step_up']['root_count'],2)
            self.assertEqual(analysis['primary_strata']['measurement_step_down']['root_count'],2)
            malformed=json.loads(json.dumps(payload))
            first=next(i for i,r in enumerate(malformed['records'])
                       if r['scenario']=='measurement_step_up' and r['split']=='heldout_development'
                       and r['arm']=='B' and r['history_length']==1000 and r['history_end_exclusive']>=6000)
            malformed['records'].pop(first)
            with self.assertRaisesRegex(ValueError,'unpaired update endpoints'):
                analyze_payload(malformed)
            # Completed rerun is a verified no-op and must not call its sampler.
            def forbidden(_segment): raise AssertionError('complete run attempted to repeat a root')
            again=self._run_with_mock_estimators(cp,BANK,sp,ap,out)
            self.assertEqual(again['results_sha256'],manifest['results_sha256'])
            (out/'finite_history_results.json').write_text('{corrupted',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'complete run result is missing or corrupted'):
                self._run_with_mock_estimators(cp,BANK,sp,ap,out)

    def test_interrupted_run_recovers_orphan_checkpoint_without_repeating_root(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td); _,cp,sp,ap,roots=self._fixture(d); out=d/'run'
            original=runner._manifest_write; calls={'n':0}
            def interrupt_after_atomic_root(*args,**kwargs):
                calls['n']+=1
                if calls['n']==2: raise RuntimeError('synthetic crash after root file commit')
                return original(*args,**kwargs)
            original_root_fn=self._synthetic_root_records; root_calls={'n':0}
            def interrupted_root(*args,**kwargs):
                root_calls['n']+=1
                if root_calls['n']==2: raise RuntimeError('synthetic interruption during next root')
                return original_root_fn(*args,**kwargs)
            with mock.patch.object(runner,'_manifest_write',side_effect=interrupt_after_atomic_root), \
                 mock.patch.object(runner,'causal_root_records',side_effect=interrupted_root), \
                 mock.patch.object(runner,'CandidateA',side_effect=lambda bank,family:FakeEstimator()), \
                 mock.patch.object(runner,'CandidateB',side_effect=lambda bank,family:FakeEstimator()), \
                 mock.patch.object(runner,'_validate_config'):
                with self.assertRaisesRegex(RuntimeError,'synthetic crash'):
                    runner.run_study(cp,BANK,sp,ap,out)
            before={p.name:runner.sha256(p) for p in (out/'root_results').glob('*.json')}
            self.assertEqual(len(before),1)
            committed=next((out/'root_results').glob('*.json'))
            temp_checkpoint=committed.with_name(f'.{committed.name}.tmp-simulated-crash')
            committed_name=committed.name
            committed.replace(temp_checkpoint)
            temp_sha=runner.sha256(temp_checkpoint)
            root_calls={'n':0}
            def resumed_root(*args,**kwargs):
                root_calls['n']+=1
                return original_root_fn(*args,**kwargs)
            with mock.patch.object(runner,'causal_root_records',side_effect=resumed_root), \
                 mock.patch.object(runner,'CandidateA',side_effect=lambda bank,family:FakeEstimator()), \
                 mock.patch.object(runner,'CandidateB',side_effect=lambda bank,family:FakeEstimator()), \
                 mock.patch.object(runner,'_validate_config'):
                complete=runner.run_study(cp,BANK,sp,ap,out)
            after={p.name:runner.sha256(p) for p in (out/'root_results').glob('*.json')}
            self.assertEqual(temp_sha,after[committed_name])
            self.assertEqual(complete['completed_root_count'],15)
            # First approved root was adopted from its orphan root file, not sampled again.
            self.assertEqual(root_calls['n'],len(roots)-1)

    def test_corrupt_checkpoint_resume_mismatch_and_atomic_rejection(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td); _,cp,sp,ap,roots=self._fixture(d); out=d/'run'
            original=runner._manifest_write; calls={'n':0}
            def interrupt(*args,**kwargs):
                calls['n']+=1
                if calls['n']==2: raise RuntimeError('interrupt')
                return original(*args,**kwargs)
            root_fn=self._synthetic_root_records
            with mock.patch.object(runner,'_manifest_write',side_effect=interrupt), \
                 mock.patch.object(runner,'CandidateA',side_effect=lambda bank,family:FakeEstimator()), \
                 mock.patch.object(runner,'CandidateB',side_effect=lambda bank,family:FakeEstimator()), \
                 mock.patch.object(runner,'causal_root_records',side_effect=root_fn), \
                 mock.patch.object(runner,'_validate_config'):
                with self.assertRaises(RuntimeError): runner.run_study(cp,BANK,sp,ap,out)
            artifact=next((out/'root_results').glob('*.json'))
            artifact.write_text('{corrupt',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'corrupt'):
                self._run_with_mock_estimators(cp,BANK,sp,ap,out)
            self.assertFalse((out/'RUNNING.lock').exists())

    def test_resume_rejects_checkpoint_from_different_input_fingerprint(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td); _,cp,sp,ap,_=self._fixture(d); out=d/'run'
            original=runner._manifest_write; calls={'n':0}
            def interrupt(*args,**kwargs):
                calls['n']+=1
                if calls['n']==2: raise RuntimeError('stop after first checkpoint')
                return original(*args,**kwargs)
            with mock.patch.object(runner,'_manifest_write',side_effect=interrupt), \
                 mock.patch.object(runner,'CandidateA',side_effect=lambda bank,family:FakeEstimator()), \
                 mock.patch.object(runner,'CandidateB',side_effect=lambda bank,family:FakeEstimator()), \
                 mock.patch.object(runner,'causal_root_records',side_effect=self._synthetic_root_records), \
                 mock.patch.object(runner,'_validate_config'):
                with self.assertRaises(RuntimeError): runner.run_study(cp,BANK,sp,ap,out)
            manifest_path=out/'RUN_MANIFEST.json'; run_manifest=json.loads(manifest_path.read_text())
            run_manifest['run_fingerprint']='0'*64
            manifest_path.write_text(json.dumps(run_manifest),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'fingerprint mismatch'):
                self._run_with_mock_estimators(cp,BANK,sp,ap,out)

    def test_active_and_stale_run_locks(self):
        with tempfile.TemporaryDirectory() as td:
            lock=Path(td)/'RUNNING.lock'
            lock.write_text(json.dumps({'pid':__import__('os').getpid()}),encoding='utf-8')
            with self.assertRaisesRegex(RuntimeError,'already active'):
                runner.acquire_lock(lock)
            lock.write_text(json.dumps({'pid':2**30}),encoding='utf-8')
            runner.acquire_lock(lock)
            self.assertTrue(lock.is_file())
            lock.unlink()

    def test_memory_budget_handling_and_exact_optimizer_equivalence(self):
        with self.assertRaises(MemoryError):
            runner.check_resource_limits(101,0,{'peak_rss_limit_bytes':100,'cpu_time_limit_seconds':10})
        with self.assertRaises(TimeoutError):
            runner.check_resource_limits(10,11,{'peak_rss_limit_bytes':100,'cpu_time_limit_seconds':10})
        for family in ('exact_categorical','approximate_dem'):
            a=CandidateA(self.bank,family); b=CandidateB(self.bank,family)
            old_a=np.column_stack([np.interp(A_GRID,BURST_KNOTS,a.templates[:,j])
                                   for j in range(FEATURE_COUNT)])
            old_b=np.asarray([[bilinear(self.bank.means[family],float(x),float(y))
                               for y in FIT_MEASUREMENT_GRID] for x in FIT_BURST_GRID])
            targets=[self.bank.interpolated(family,*p) for p in
                     ((0.,0.),(.02,.01),(.008,.003),(.008,.006),(.004,.009),(.015,.001),(.019,.009))]
            targets.append(np.linspace(.01,.99,FEATURE_COUNT))
            for target in targets:
                ref_a=np.mean(((old_a-target[None,:])/a.scales[None,:])**2,axis=1)
                self.assertEqual(a.estimate_mean(target).p_burst,float(A_GRID[int(np.argmin(ref_a))]))
                ref_b=np.mean(((old_b-target[None,None,:])/b.scales[None,None,:])**2,axis=2)
                expected=np.unravel_index(int(np.argmin(ref_b)),ref_b.shape)
                got=b.estimate_mean(target)
                self.assertEqual((got.p_burst,got.p_measurement),
                                 (float(FIT_BURST_GRID[expected[0]]),float(FIT_MEASUREMENT_GRID[expected[1]])))


if __name__=='__main__': unittest.main(verbosity=2)
