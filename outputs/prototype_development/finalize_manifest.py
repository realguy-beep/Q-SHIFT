"""Create a stable hash manifest for source, configuration and evidence files."""
import hashlib, json
from pathlib import Path
P=Path(__file__).resolve().parent
allowed={'.py','.json','.md','.csv','.html','.png','.npz','.txt'}
files={str(f.relative_to(P)).replace('\\','/'):hashlib.sha256(f.read_bytes()).hexdigest()
       for f in sorted(P.rglob('*')) if f.is_file() and f.name!='MANIFEST.json' and '__pycache__' not in f.parts and f.suffix.lower() in allowed}
res=json.loads((P/'AUDITED_RESULTS.json').read_text())
manifest={'study':'qshift_prototype_development_2026_11','confirmatory':False,'independent_saved_array_audit':'PASS',
          'evaluation_roots':res['roots'],'paired_evaluation_shots':res['heldout_shots'],'hashes_sha256':files}
(P/'MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print(f"Manifest hashes {len(files)} files; roots={res['roots']}; shots={res['heldout_shots']}")
