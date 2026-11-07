"""Read-only verification of manifests directly feeding this investigation."""
from __future__ import annotations
import hashlib, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

def digest(p: Path) -> str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20), b''): h.update(b)
    return h.hexdigest()

def check_manifest(path: Path, local_key: str, ref_key: str, root: Path):
    m=json.loads(path.read_text(encoding='utf-8'))
    checks=[]
    for rel, rec in m.get(local_key,{}).items():
        p=path.parent/rel
        actual=digest(p) if p.is_file() else None
        checks.append({'kind':'local','path':str(p.relative_to(root)),'expected':rec.get('sha256'),'actual':actual,
                       'expected_bytes':rec.get('bytes'),'actual_bytes':p.stat().st_size if p.is_file() else None,
                       'pass':p.is_file() and actual==rec.get('sha256') and p.stat().st_size==rec.get('bytes')})
    for rel, rec in m.get(ref_key,{}).items():
        p=root/rel
        actual=digest(p) if p.is_file() else None
        checks.append({'kind':'referenced_input','path':rel,'expected':rec.get('sha256'),'actual':actual,
                       'expected_bytes':rec.get('bytes'),'actual_bytes':p.stat().st_size if p.is_file() else None,
                       'pass':p.is_file() and actual==rec.get('sha256') and p.stat().st_size==rec.get('bytes')})
    return checks

def check_file_table(folder: Path, entries, root: Path, *, path_key='path', size_key='bytes', paths_from_root=False):
    """Verify list- or dict-shaped historical file tables without executing them."""
    if isinstance(entries,dict):
        iterable=[]
        for rel,rec in entries.items():
            rec=rec if isinstance(rec,dict) else {'sha256':rec}
            iterable.append({path_key:rel,**rec})
    else: iterable=entries
    checks=[]
    for rec in iterable:
        rel=rec[path_key];p=(root/rel) if paths_from_root else (folder/rel);actual=digest(p) if p.is_file() else None
        expected=rec.get('sha256');expected_bytes=rec.get(size_key,rec.get('size_bytes'))
        checks.append({'kind':'historical_manifest_file','path':str(p.relative_to(root)),'expected':expected,'actual':actual,
            'expected_bytes':expected_bytes,'actual_bytes':p.stat().st_size if p.is_file() else None,
            'pass':p.is_file() and actual==expected and (expected_bytes is None or p.stat().st_size==expected_bytes)})
    return checks

def main():
    results={}
    cat=ROOT/'outputs/categorical_decoder_feasibility/MANIFEST.json'
    results['categorical_decoder_feasibility']=check_manifest(cat,'local_files','read_only_source_references',ROOT)
    inf=ROOT/'outputs/categorical_inference_investigation/MANIFEST.json'
    results['categorical_inference_investigation']=check_manifest(inf,'local_files','read_only_historical_inputs',ROOT)
    p2=ROOT/'outputs/phase2b_pauli_bias'
    m=json.loads((p2/'SHA256_MANIFEST.json').read_text(encoding='utf-8'))
    pchecks=[]
    for rel,rec in m['files'].items():
        p=p2/rel; a=digest(p) if p.is_file() else None
        pchecks.append({'kind':'Phase2B_file','path':str(p.relative_to(ROOT)),'expected':rec['sha256'],'actual':a,
                        'expected_bytes':rec['bytes'],'actual_bytes':p.stat().st_size if p.is_file() else None,
                        'pass':p.is_file() and a==rec['sha256'] and p.stat().st_size==rec['bytes']})
    actual_files={p.relative_to(p2).as_posix() for p in p2.rglob('*') if p.is_file() and p.name!='SHA256_MANIFEST.json' and '__pycache__' not in p.parts and p.suffix!='.pyc'}
    p2_info={'checks':pchecks,'manifest_file_count':m.get('file_count'), 'manifest_entry_count':len(m['files']),
             'actual_inventory_count':len(actual_files),'extras':sorted(actual_files-set(m['files'])),
             'missing':sorted(set(m['files'])-actual_files)}
    # The sole extra is a same-byte duplicate of the frozen config; record it rather than hide it.
    duplicate={}
    if p2_info['extras']==['config - Copy.json']:
        extra=p2/'config - Copy.json'; base=p2/'config.json'
        duplicate={'path':str(extra.relative_to(ROOT)),'sha256':digest(extra),'bytes':extra.stat().st_size,
                   'identical_to_frozen_config':digest(extra)==digest(base),'paired_file':'outputs/phase2b_pauli_bias/config.json'}
    p2_info['unmanifested_duplicate_audit']=duplicate
    results['phase2b_manifest']=p2_info
    dem_path=ROOT/'outputs/dem_feasibility_gate/MANIFEST.json'
    dm=json.loads(dem_path.read_text(encoding='utf-8'))
    dem_checks=[]
    for rec in dm.get('referenced_evidence',[]):
        rel=rec['path']; p=ROOT/rel; actual=digest(p) if p.is_file() else None
        expected=rec.get('expected_sha256') or rec.get('actual_sha256')
        dem_checks.append({'kind':rec.get('kind'),'path':rel,'expected':expected,'actual':actual,
                           'bytes':p.stat().st_size if p.is_file() else None,
                           'expected_origin':'historical_expected' if rec.get('expected_sha256') else ('manifest_recorded_actual_only' if rec.get('actual_sha256') else None),
                           'status':'PASS' if expected is not None and actual==expected else ('UNHASHED_REFERENCE' if expected is None and p.is_file() else 'FAIL')})
    for rec in dm.get('new_outputs',[]):
        rel=rec['path']; p=dem_path.parent/rel; actual=digest(p) if p.is_file() else None
        dem_checks.append({'kind':'DEM_gate_output','path':str(p.relative_to(ROOT)),'expected':rec.get('sha256'),'actual':actual,
                           'bytes':p.stat().st_size if p.is_file() else None,
                           'status':'PASS' if p.is_file() and actual==rec.get('sha256') and p.stat().st_size==rec.get('size_bytes') else 'FAIL'})
    results['dem_feasibility_manifest']={'recorded_status':dm.get('status'),'recorded_hash_mismatches':dm.get('hash_mismatches'),
        'checks':dem_checks,'pass_count':sum(c['status']=='PASS' for c in dem_checks),
        'unhashed_reference_count':sum(c['status']=='UNHASHED_REFERENCE' for c in dem_checks),
        'manifest_recorded_actual_only_count':sum(c.get('expected_origin')=='manifest_recorded_actual_only' and c['status']=='PASS' for c in dem_checks),
        'failure_count':sum(c['status']=='FAIL' for c in dem_checks)}
    freeze=json.loads((p2/'PRETEST_FREEZE.json').read_text(encoding='utf-8'))
    freeze_checks=[]
    for rel,expected in freeze.get('files_sha256',{}).items():
        p=ROOT/rel; actual=digest(p) if p.is_file() else None
        freeze_checks.append({'path':rel,'expected':expected,'actual':actual,'pass':actual==expected})
    results['phase2b_pretest_freeze']={'revision':freeze.get('revision'),'hash_checks':freeze_checks,
        'check_count':len(freeze_checks),'failure_count':sum(not c['pass'] for c in freeze_checks)}
    # Existing fixed, correlation-aware, adaptive, and multi-distance headroom records.
    historical_tables = [
        ('correlation_pilot','outputs/correlation_pilot/MANIFEST.json','files','path','size_bytes'),
        ('correlation_mechanism_audit_inputs','outputs/correlation_mechanism_audit/MANIFEST.json','input_evidence','path','size_bytes'),
        ('correlation_mechanism_audit_outputs','outputs/correlation_mechanism_audit/MANIFEST.json','audit_outputs','path','bytes'),
        ('adaptive_prototype','outputs/prototype_development/MANIFEST.json','hashes_sha256',None,None),
        ('phase2a_specialization','outputs/phase2a_decoder_specialization/PHASE2A_MANIFEST.json','files',None,'bytes'),
        ('headroom_feasibility','outputs/headroom_feasibility/MANIFEST.json','files','path','bytes'),
    ]
    historical_checks={}
    for label,rel,key,path_key,size_key in historical_tables:
        mpath=ROOT/rel; hm=json.loads(mpath.read_text(encoding='utf-8'))
        entries=hm.get(key,{})
        historical_checks[label]=check_file_table(mpath.parent,entries,ROOT,
            path_key=path_key or 'path',size_key=size_key or 'bytes',
            paths_from_root=label=='correlation_mechanism_audit_inputs')
    results['historical_decoder_evidence_manifests']=historical_checks
    all_checks=results['categorical_decoder_feasibility']+results['categorical_inference_investigation']+pchecks
    all_checks+=freeze_checks
    all_checks += [c for vals in historical_checks.values() for c in vals]
    failures=[c for c in all_checks if not c['pass']]
    failures += [c for c in dem_checks if c['status']=='FAIL']
    results['summary']={'direct_manifest_file_checks':len(all_checks),'direct_manifest_failures':len(failures),
        'historical_decoder_evidence_checks':sum(len(v) for v in historical_checks.values()),
        'historical_decoder_evidence_failures':sum(not c['pass'] for vals in historical_checks.values() for c in vals),
        'phase2b_inventory_exact':not p2_info['extras'] and not p2_info['missing'],
        'phase2b_unmanifested_duplicate_identical_to_config':duplicate.get('identical_to_frozen_config',False),
        'dem_gate_missing_expected_hashes':results['dem_feasibility_manifest']['unhashed_reference_count'],
        'decision':'PASS' if not failures else 'FAIL',
        'note':'A manifest that lacks a hash is recorded as unhashed, not treated as independently authenticated.'}
    out=HERE/'PHASE0_VERIFICATION.json'
    out.write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'decision':results['summary']['decision'],'direct_checks':len(all_checks),
        'direct_failures':len(failures),'phase2b_entries':len(pchecks),'phase2b_inventory_exact':results['summary']['phase2b_inventory_exact'],
        'dem_gate_hashes_pass':results['dem_feasibility_manifest']['pass_count'],
        'dem_gate_actual_only_reference_hashes':results['dem_feasibility_manifest']['manifest_recorded_actual_only_count'],
        'dem_gate_unhashed_refs':results['dem_feasibility_manifest']['unhashed_reference_count'],
        'dem_gate_hash_failures':results['dem_feasibility_manifest']['failure_count'],'output':str(out)},indent=2))
    if failures: raise SystemExit(2)

if __name__=='__main__':main()
