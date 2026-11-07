"""Re-hash every archived input recorded by audit_existing_headroom.py."""
from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path.cwd().resolve()
OUT=ROOT/'outputs'/'unified_headroom_audit'

def digest(p: Path) -> str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def main():
    source=json.loads((OUT/'SOURCE_FILE_HASHES.json').read_text(encoding='utf-8'))
    rows=[]
    for raw,meta in sorted(source.items()):
        p=(ROOT/raw).resolve()
        if not p.is_file():
            rows.append({'path':raw,'status':'MISSING','expected_sha256':meta['sha256']})
            continue
        actual=digest(p); size=p.stat().st_size
        ok=actual==meta['sha256'] and size==meta['bytes']
        rows.append({'path':raw,'status':'PASS' if ok else 'MISMATCH',
                     'expected_sha256':meta['sha256'],'actual_sha256':actual,
                     'expected_bytes':meta['bytes'],'actual_bytes':size})
    result={'scope':'read-only rehash of SOURCE_FILE_HASHES.json inputs',
            'expected_entries':len(source),'passed':sum(r['status']=='PASS' for r in rows),
            'mismatched':sum(r['status']=='MISMATCH' for r in rows),
            'missing':sum(r['status']=='MISSING' for r in rows),'entries':rows}
    (OUT/'SOURCE_HASH_VERIFICATION.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    bad=[r for r in rows if r['status']!='PASS']
    lines=['# Audit source hash verification','',
           f"Rehashed {len(rows)} archived source files recorded by the paired-array audit. "
           "This check is read-only and confirms the inputs have not changed since that audit output was generated.", '',
           f"**Result:** {result['passed']}/{result['expected_entries']} PASS; "
           f"{result['mismatched']} mismatches; {result['missing']} missing.", '']
    if bad:
        lines+=['## Non-passing entries','']
        for r in bad:lines.append(f"- `{r['path']}`: {r['status']} ({r.get('expected_sha256')} vs {r.get('actual_sha256')}).")
    (OUT/'SOURCE_HASH_VERIFICATION.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('expected_entries','passed','mismatched','missing')},indent=2))
    return 0 if not bad else 2

if __name__=='__main__':raise SystemExit(main())
