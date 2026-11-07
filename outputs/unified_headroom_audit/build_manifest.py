"""Build this audit's own SHA-256 manifest (excluding the manifest itself)."""
import hashlib, json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def main():
    files=[]
    for p in sorted(HERE.rglob('*')):
        if not p.is_file() or p.name=='MANIFEST.json' or '__pycache__' in p.parts:
            continue
        files.append({'path':p.relative_to(ROOT).as_posix(),
                      'size_bytes':p.stat().st_size,'sha256':sha(p)})
    record={'study':'Q-SHIFT unified decoder potential and adaptive headroom evidence audit',
            'created_after_archive_recomputation':True,
            'historical_artifacts_modified':False,
            'new_simulation_shots':0,
            'manifest_excludes_itself':True,
            'file_count':len(files),'files':files}
    (HERE/'MANIFEST.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'file_count':len(files),'manifest':str(HERE/'MANIFEST.json')},indent=2))

if __name__=='__main__':main()
