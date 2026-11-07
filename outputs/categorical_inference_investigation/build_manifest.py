"""Hash this investigation and its read-only historical inputs."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
MANIFEST=HERE/"MANIFEST.json"
EXTERNAL=[
    "outputs/categorical_decoder_feasibility/MANIFEST.json",
    "outputs/categorical_decoder_feasibility/categorical_reference.py",
    "outputs/categorical_decoder_feasibility/toy_circuits.py",
    "outputs/categorical_decoder_feasibility/run_toy_comparisons.py",
    "outputs/categorical_decoder_feasibility/test_categorical_reference.py",
    "outputs/phase2b_pauli_bias/noise_model.py",
    "outputs/phase2b_pauli_bias/config.json",
    "outputs/phase2b_pauli_bias/PHASE2B_PROTOCOL.md",
    "outputs/phase2b_pauli_bias/CIRCUIT_VALIDATION.json",
    "outputs/phase2b_pauli_bias/PRETEST_FREEZE.json",
    "outputs/phase2b_pauli_bias/SHA256_MANIFEST.json",
    "outputs/dem_feasibility_gate/DEM_CONSTRUCTION_AUDIT.md",
    "outputs/dem_feasibility_gate/DEM_CONSTRUCTION_RESULTS.json",
]

def digest(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""): h.update(block)
    return h.hexdigest()

def main():
    local={}
    for path in sorted(HERE.rglob("*")):
        if not path.is_file() or path==MANIFEST or "__pycache__" in path.parts:
            continue
        local[path.relative_to(HERE).as_posix()]={"sha256":digest(path),"bytes":path.stat().st_size}
    external={}
    for rel in EXTERNAL:
        path=ROOT/Path(rel)
        external[rel]={"sha256":digest(path),"bytes":path.stat().st_size} if path.is_file() else {"status":"MISSING"}
    result={
        "purpose":"Categorical failure attribution and structured-inference feasibility evidence",
        "local_files":local,
        "read_only_historical_inputs":external,
        "accounting":{"stochastic_shots_generated":0,
                      "phase2b_evaluation_shots_generated":0,
                      "deterministic_toy_fault_configurations_checked":320,
                      "deterministic_phase2b_single_fault_outcomes_checked":5925,
                      "phase2b_noiseless_repeat_rows_checked":10},
        "historical_artifacts_modified":[],
        "decision":"PARTIAL",
    }
    MANIFEST.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(f"Wrote {MANIFEST}; hashed {len(local)} local files and {len(external)} historical references")

if __name__=="__main__":main()
