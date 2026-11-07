import json,csv,re,hashlib
from pathlib import Path
BASE=Path(__file__).resolve().parent; ROOT=BASE.parent
old=json.loads((BASE/'stage2/STAGE2_SEED_INVENTORY.json').read_text(encoding='utf-8'))
names=['data_heavy','nominal','measurement_heavy']; generated={'roots':{},'derived_seeds':{'calibration':[],'validation':[],'test':[]},'template':[73000001+i for i in range(9)],'diagnostic':[72000000]}
for ri,name in enumerate(names):
 generated['roots'][name]=[]
 for i in range(20):
  root=72000001+10000*(20*ri+i);generated['roots'][name].append(root)
  generated['derived_seeds']['calibration'].append(root+101+ri)
  generated['derived_seeds']['validation'].append(root+201+ri)
  generated['derived_seeds']['test'].append(root+301+ri)
inventory_matches=(generated['roots']==old['roots'] and generated['derived_seeds']=={k:old['derived_seeds'][k] for k in ['calibration','validation','test']} and generated['template']==old['derived_seeds']['template'] and generated['diagnostic']==old['derived_seeds']['diagnostic'])
derived=sum(generated['derived_seeds'].values(),[])+generated['template']+generated['diagnostic']
assert len(derived)==190 and len(set(derived))==190
files=[]; values=set(); keypat=re.compile(r'(?:seed|rng)',re.I)
def walk(obj,key='',found=None):
 if isinstance(obj,dict):
  for k,v in obj.items(): walk(v,k,found)
 elif isinstance(obj,list):
  for v in obj: walk(v,key,found)
 elif isinstance(obj,int) and keypat.search(key): found.add(obj)
for phase in ['phase4a_model_adequacy','phase4b_replication','phase4c_strong_baselines']:
 folder=ROOT/phase
 for p in sorted(folder.rglob('*')):
  if not p.is_file() or '__pycache__' in p.parts or p==BASE/'audit_stage2_seeds.py': continue
  found=set(); kind='not_seed_structured'
  try:
   if p.suffix.lower()=='.json': walk(json.loads(p.read_text(encoding='utf-8-sig')),found=found);kind='json_seed_key_scan'
   elif p.suffix.lower()=='.csv':
    with p.open(encoding='utf-8-sig',newline='') as f:
     rd=csv.DictReader(f)
     for row in rd:
      for k,v in row.items():
       if keypat.search(k) and v:
        try:found.add(int(float(v)))
        except ValueError:pass
    kind='csv_seed_column_scan'
   elif p.suffix.lower()=='.npz':
    import numpy as np
    with np.load(p,allow_pickle=False) as z:
     for k in z.files:
      if keypat.search(k):
       try: found.update(map(int,z[k].reshape(-1)))
       except Exception: pass
    kind='npz_seed_key_scan'
  except Exception as e: kind='unreadable:'+repr(e)
  values.update(found);files.append({'path':str(p),'method':kind,'seed_values':sorted(found),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
collisions=sorted(set(derived)&values)
report={'formula_matches_uploaded_inventory':inventory_matches,'uploaded_inventory_mismatches':{'roots':generated['roots']!=old['roots'],'derived_streams':{k:generated['derived_seeds'][k]!=old['derived_seeds'].get(k) for k in generated['derived_seeds']},'templates':generated['template']!=old.get('derived_seeds',{}).get('template'),'diagnostic':generated['diagnostic']!=old.get('derived_seeds',{}).get('diagnostic')},'root_count':60,'derived_count':190,'unique_derived_count':len(set(derived)),'all_derived_unique':len(set(derived))==190,'historical_files_examined':files,'historical_unique_seed_values':sorted(values),'collisions':collisions,'recoverable_seed_collision_free':not collisions,'coverage_limitations':'Only explicit seed/RNG-named JSON fields, CSV columns, and NPZ keys were extracted. Seeds encoded solely in source logic, filenames, logs, or non-seed-named fields may be missed; historical coverage is not complete.'}
out=BASE/'stage2';out.mkdir(exist_ok=True)
(out/'STAGE2_SEED_INVENTORY_AMENDED.json').write_text(json.dumps({**generated,'all_unique':True,'derived_seed_count':190},indent=2)+'\n',encoding='utf-8')
(out/'STAGE2_COLLISION_AUDIT.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='historical_files_examined' and k!='historical_unique_seed_values'},indent=2))
