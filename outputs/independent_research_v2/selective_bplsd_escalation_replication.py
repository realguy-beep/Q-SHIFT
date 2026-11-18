"""Fresh-seed efficacy replication for the fixed selective BP+LSD hybrid."""
from __future__ import annotations
import json,time
from pathlib import Path
import stim
from selective_bplsd_escalation import (
    CONDITIONS,MAIN_SHOTS,PREFLIGHT_SHOTS,THRESHOLD,build_circuit,decoder_set,evaluate,
)

HERE=Path(__file__).resolve().parent
PREFLIGHT_SEEDS=(2026114301,2026114302,2026114303,2026114304,2026114305,2026114306)
MAIN_SEEDS=(2026114311,2026114312,2026114313,2026114314,2026114315,2026114316)

def main():
    start=time.perf_counter();prepared=[];pre=[]
    for (basis,regime),seed in zip(CONDITIONS,PREFLIGHT_SEEDS,strict=True):
        c=build_circuit(basis,regime)
        if (c.num_qubits,c.num_detectors,c.num_observables)!=(26,40,1):raise RuntimeError("geometry mismatch")
        dem,corr,plain,lsd,h,l=decoder_set(c)
        clean=stim.Circuit()
        for ins in c.flattened():
            if ins.name not in ("PAULI_CHANNEL_1","PAULI_CHANNEL_2","X_ERROR","Z_ERROR"):
                clean.append(ins.name,ins.targets_copy(),ins.gate_args_copy())
        nd,no=clean.compile_detector_sampler(seed=1).sample(20,separate_observables=True)
        if nd.any() or no.any():raise RuntimeError("noiseless mismatch")
        decs=(dem,corr,plain,lsd,h,l)
        row=evaluate(c,decs,PREFLIGHT_SHOTS,seed)
        prepared.append((c,decs))
        projected=(row["sample_seconds"]+row["decode_seconds"]["correlation_batch"]+
                   row["decode_seconds"]["plain_batch"]+row["decode_seconds"]["lsd_flagged_only"])*MAIN_SHOTS/PREFLIGHT_SHOTS
        pre.append({"basis":basis,"regime":regime,"metrics":row,"projected_seconds":projected})
    projection=sum(x["projected_seconds"] for x in pre)
    if projection>300:raise RuntimeError(f"runtime gate failed: {projection:.1f}s")
    rows=[]
    for (basis,regime),seed,(c,decs) in zip(CONDITIONS,MAIN_SEEDS,prepared,strict=True):
        row=evaluate(c,decs,MAIN_SHOTS,seed);row.update({"memory_basis":basis,"regime":regime});rows.append(row)
    base=sum(r["ler"]["correlation_matching"] for r in rows)/len(rows)
    hyb=sum(r["ler"]["hybrid"] for r in rows)/len(rows)
    rel=1-hyb/base
    rels=[1-r["ler"]["hybrid"]/r["ler"]["correlation_matching"] for r in rows]
    tr=sum(r["hybrid_to_correlation_decode_time_ratio"] for r in rows)/len(rows)
    out={"status":"selective_bplsd_escalation_independent_replication","conditions":rows,"preflight":pre,
         "macro_ler":{"correlation_matching":base,"hybrid":hyb},
         "macro_relative_reduction":rel,"per_condition_relative_reductions":rels,
         "mean_total_decode_time_ratio":tr,
         "efficacy_direction_replicated":rel>=.10 and min(rels)>=-.05 and all(r["invalid_lsd_syndromes"]==0 for r in rows),
         "runtime_gate_passed":tr<2,"advancement_gate_passed":rel>=.10 and min(rels)>=-.05 and tr<2 and all(r["invalid_lsd_syndromes"]==0 for r in rows),
         "preflight_samples":len(CONDITIONS)*PREFLIGHT_SHOTS,"main_samples":len(CONDITIONS)*MAIN_SHOTS,
         "projected_main_seconds":projection,"elapsed_seconds":time.perf_counter()-start,
         "scope":"independent efficacy replication; known BP+LSD cost gate remains separate"}
    (HERE/"selective_bplsd_escalation_replication_results.json").write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps({"status":out["status"],"macro_ler":out["macro_ler"],
                      "reduction":rel,"time_ratio":tr,"efficacy_replicated":out["efficacy_direction_replicated"],
                      "gate":out["advancement_gate_passed"],"elapsed":out["elapsed_seconds"]},indent=2))

if __name__=="__main__":main()
