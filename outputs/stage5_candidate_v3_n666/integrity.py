from __future__ import annotations
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[1]
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()
def verify():
 p=HERE/'STAGE5_V3_CANDIDATE_FREEZE.json'
 if not p.is_file(): raise RuntimeError('candidate pre-test freeze missing')
 record=json.loads(p.read_text(encoding='utf-8'))
 if record.get('status')!='CANDIDATE_NOT_AUTHORIZED_TO_SAMPLE' or record.get('stage5_evaluation_shots_generated')!=0 or record.get('sealed_historical_test_accessed') is not False:
  raise RuntimeError('candidate freeze boundary invalid')
 for rel,h in record['sha256'].items():
  if sha(ROOT/rel)!=h: raise RuntimeError(f'candidate source/config freeze mismatch: {rel}')
 return record
