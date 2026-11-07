"""Independent read-only SHA-256 verification of MANIFEST.json."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]

def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    manifest=json.loads((HERE/"MANIFEST.json").read_text(encoding="utf-8"))
    checks=0
    for rel,record in manifest["local_files"].items():
        path=HERE/Path(rel)
        if not path.is_file() or digest(path)!=record["sha256"] or path.stat().st_size!=record["bytes"]:
            raise SystemExit(f"LOCAL HASH FAIL: {rel}")
        checks+=1
    for rel,record in manifest["read_only_historical_inputs"].items():
        path=ROOT/Path(rel)
        if record.get("status")=="MISSING" or not path.is_file() or digest(path)!=record["sha256"] or path.stat().st_size!=record["bytes"]:
            raise SystemExit(f"HISTORICAL INPUT HASH FAIL: {rel}")
        checks+=1
    print(f"PASS: {checks} SHA-256/size checks ({len(manifest['local_files'])} local, {len(manifest['read_only_historical_inputs'])} historical inputs)")

if __name__=="__main__":main()
