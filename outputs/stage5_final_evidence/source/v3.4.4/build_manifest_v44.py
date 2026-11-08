from __future__ import annotations
import hashlib, json
from pathlib import Path

HERE = Path(__file__).resolve().parent

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1<<20),b''): h.update(block)
    return h.hexdigest()

def main():
    files={}
    for path in sorted(HERE.rglob('*')):
        if not path.is_file() or '__pycache__' in path.parts or path.suffix=='.pyc':
            continue
        if path.name=='V44_EVIDENCE_MANIFEST.json':
            continue
        rel=path.relative_to(HERE).as_posix()
        files[rel]={'sha256':sha(path),'size_bytes':path.stat().st_size}
    payload={
        'format':'qshift-stage5-v344-evidence-manifest',
        'base_commit':'8c06750808582137f6a81e2170ad702a552594fb',
        'implementation_base_commit':'d4d4e8411311385bd6cc9823ec80475484ab1a14',
        'revision':'3.4.4',
        'independent_audit_status':'PASS_WITH_DEVIATION',
        'files':files,
        'stage5_recovery_executed':False,
        'additional_stage5_samples_generated':0,
        'sealed_outcomes_accessed':False,
    }
    out=HERE/'V44_EVIDENCE_MANIFEST.json'
    out.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps({'path':str(out),'files_hashed':len(files),'sha256':sha(out)},indent=2))

if __name__=='__main__': main()
