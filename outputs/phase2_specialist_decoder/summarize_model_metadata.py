"""Export DEM/graph metadata for every ideal specialist and oracle circuit."""
import importlib.util,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
PHASE1=ROOT.parent/"noise_composition_phase"/"run_composition_experiment.py"
spec=importlib.util.spec_from_file_location("phase1",PHASE1);p1=importlib.util.module_from_spec(spec);spec.loader.exec_module(p1)
sys.path.insert(0,str(ROOT))
from run_specialist_study import matching_for,CONDITIONS,SPECIALISTS
result={}
for name in CONDITIONS:
    model,meta=matching_for(p1.make_circuit(name));result[name]=meta
path=ROOT/"results"/"model_metadata.json"
if path.exists():raise FileExistsError(path)
path.write_text(json.dumps({"stim":__import__('stim').__version__,"pymatching":__import__('pymatching').__version__,"dem_approximation":"approximate_disjoint_errors=True","models":result},indent=2)+"\n",encoding="utf-8")
print("Saved",path)
