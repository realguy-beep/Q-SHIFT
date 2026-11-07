"""Verify every entry in this audit's manifest, excluding the manifest itself."""
import hashlib,json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def main():
    m=json.loads((HERE/'MANIFEST.json').read_text(encoding='utf-8'))
    bad=[]
    for e in m['files']:
        p=ROOT/e['path']
        if not p.is_file():bad.append((e['path'],'MISSING'));continue
        if p.stat().st_size!=e['size_bytes'] or sha(p)!=e['sha256']:
            bad.append((e['path'],'MISMATCH'))
    print(json.dumps({'entries':len(m['files']),'passed':len(m['files'])-len(bad),'failures':bad},indent=2))
    return int(bool(bad))

if __name__=='__main__':raise SystemExit(main())
