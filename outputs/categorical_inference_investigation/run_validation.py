"""Run final code/tests and save the actual command outputs."""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OLD_TEST=ROOT/"outputs"/"categorical_decoder_feasibility"/"test_categorical_reference.py"
SOURCES=[
    "baseline_reproduction.py","categorical_dem_analysis.py","controlled_variants.py",
    "controlled_cycle_variants.py","factor_graph.py","structured_inference.py",
    "phase2b_fragments.py","run_fragment.py","toy_ve_analysis.py","circuit_heuristics.py",
    "summarize_investigation.py","separator_ablation.py","test_exact_inference.py",
    "test_dem_attribution.py","build_manifest.py","verify_manifest.py","run_validation.py",
]

def run(label,command,cwd):
    result=subprocess.run(command,cwd=cwd,capture_output=True,text=True)
    return {"label":label,"command":[str(x) for x in command],"return_code":result.returncode,
            "stdout":result.stdout,"stderr":result.stderr}

def main():
    py=sys.executable
    runs=[]
    runs.append(run("py_compile",[py,"-B","-m","py_compile",*SOURCES],HERE))
    for label,script in (("baseline_reproduction","baseline_reproduction.py"),
                         ("independent_dem_enumeration","categorical_dem_analysis.py"),
                         ("separator_ablation","separator_ablation.py"),
                         ("fixed_marginal_variants","controlled_cycle_variants.py"),
                         ("product_marginal_sensitivity","controlled_variants.py"),
                         ("toy_variable_elimination","toy_ve_analysis.py"),
                         ("circuit_symbolic_heuristics","circuit_heuristics.py")):
        runs.append(run(label,[py,"-B",script],HERE))
    runs.append(run("new_unit_tests",[py,"-B","-m","unittest","discover","-v"],HERE))
    runs.append(run("historical_toy_unit_tests",[py,"-B",str(OLD_TEST),"-v"],HERE))
    runs.append(run("aggregate_numerical_audit",[py,"-B","summarize_investigation.py"],HERE))
    failed=[r["label"] for r in runs if r["return_code"]!=0]
    out={"status":"PASS" if not failed else "FAIL","commands":runs,
         "new_test_count":5,"historical_test_count":8,"failed_commands":failed,
         "scientific_data_generated_by_validation":False}
    (HERE/"VALIDATION_RESULTS.json").write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":out["status"],"new_test_count":5,"historical_test_count":8,
                      "failed_commands":failed},indent=2))
    if failed: raise SystemExit(1)

if __name__=="__main__":main()
