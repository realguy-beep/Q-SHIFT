from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CONFIG = json.loads((HERE / "DESIGN_SIMULATION_CONFIG.json").read_text(encoding="utf-8"))
INVENTORY = json.loads((HERE / "DESIGN_SEED_INVENTORY.json").read_text(encoding="utf-8"))


def wilson_independent(successes, trials):
    z = 1.959963984540054
    p = successes / trials
    d = 1 + z*z/trials
    c = (p + z*z/(2*trials))/d
    h = z*math.sqrt(p*(1-p)/trials + z*z/(4*trials*trials))/d
    return [max(0.0,c-h), min(1.0,c+h)]


def reference_draw(rng, family, mean, sd, shape):
    # Separately written distribution generator; does not import the production simulator.
    loc, scale = mean, sd
    if family == "normal":
        return rng.normal(loc, scale, size=shape)
    if family.startswith("student_t"):
        df = int(family[10:])
        return loc + scale*rng.standard_t(df, size=shape)/math.sqrt(df/(df-2))
    if family == "lognormal_sigma1":
        raw = rng.lognormal(0, 1, size=shape)
        return loc + scale*(raw-math.exp(.5))/math.sqrt((math.e-1)*math.e)
    if family == "zero_inflated65_normal":
        q = .35
        conditional_mean = mean/q
        conditional_sd = math.sqrt((sd*sd + mean*mean)/q - conditional_mean*conditional_mean)
        y = rng.normal(conditional_mean, conditional_sd, size=shape)
        return np.where(rng.random(shape) < .65, 0.0, y)
    if family == "tied_asymmetric65":
        q0, ql, qh = .65, .28, .07
        q = ql+qh
        p_l, p_h = ql/q, qh/q
        conditional_mean = mean/q
        conditional_var = (sd*sd + mean*mean)/q - conditional_mean*conditional_mean
        low = conditional_mean - math.sqrt(conditional_var*p_h/p_l)
        high = conditional_mean + math.sqrt(conditional_var*p_l/p_h)
        u = rng.random(shape)
        return np.where(u < q0, 0.0, np.where(u < q0+ql, low, high))
    raise ValueError(family)


def hash_file(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1<<20),b""):
            h.update(block)
    return h.hexdigest()


def audit_generator():
    seed_map={(x["stream"],x["cell"]):x["seed"] for x in INVENTORY["rng_streams"]}
    means=[0.0001, -0.0002, 0.00005, -0.0001]
    sds=[0.0008, 0.0010, 0.0012, 0.0018]
    records=[]
    for family in ["normal","student_t5","student_t3","lognormal_sigma1","zero_inflated65_normal","tied_asymmetric65"]:
        seed=seed_map[("independent_generator_check",family)]
        rng=np.random.Generator(np.random.PCG64(seed))
        # Separately generate one million samples per condition for distribution checks.
        got=reference_draw(rng,family,np.asarray(means)[:,None],np.asarray(sds)[:,None],(4,250000))
        empirical_mean=got.mean(axis=1)
        empirical_sd=got.std(axis=1,ddof=1)
        mean_error=np.abs(empirical_mean-np.asarray(means))
        sd_relative=np.abs(empirical_sd/np.asarray(sds)-1)
        if np.any(mean_error > 0.015*np.asarray(sds)) or np.any(sd_relative > 0.025):
            raise AssertionError(f"Independent generator moment check failed: {family}")
        zero_mass=float(np.mean(got==0)) if family in {"zero_inflated65_normal","tied_asymmetric65"} else None
        if zero_mass is not None and abs(zero_mass-.65) > .004:
            raise AssertionError(f"Independent tie/zero mass check failed: {family} {zero_mass}")
        records.append({"family":family,"seed":seed,"draws_per_condition":250000,
                        "max_abs_mean_error":float(mean_error.max()),"max_relative_sd_error":float(sd_relative.max()),
                        "empirical_zero_mass":zero_mass})
    return records


def main():
    freeze=json.loads((HERE/"DESIGN_VALIDATION_FREEZE.json").read_text(encoding="utf-8"))
    for rel, expected in freeze["source_config_protocol_and_inventory_sha256"].items():
        if hash_file(ROOT/rel) != expected:
            raise AssertionError(f"Frozen source/config hash mismatch: {rel}")
    for rel, expected in freeze["historical_freezes_preserved_sha256"].items():
        if hash_file(ROOT/rel) != expected:
            raise AssertionError(f"Historical freeze changed: {rel}")
    result_path=HERE/"DESIGN_SIMULATION_RESULTS.json"
    if not result_path.is_file():
        raise FileNotFoundError("Design simulation results missing")
    result=json.loads(result_path.read_text(encoding="utf-8"))
    if result.get("stage5_evaluation_shots_generated") != 0 or result.get("sealed_historical_test_accessed") is not False:
        raise AssertionError("No-sampling/no-sealed-data assertion failed")
    if result.get("design_freeze_sha256") != hash_file(HERE/"DESIGN_VALIDATION_FREEZE.json"):
        raise AssertionError("Result freeze hash mismatch")
    cfg=CONFIG["monte_carlo"]["acceptance"]
    expected_n=set(CONFIG["allocations_roots_per_stratum"])
    null=result["primary_null_validation"]
    if len(null) != len(expected_n)*len(CONFIG["null_scenarios"]):
        raise AssertionError("Primary null validation cell count mismatch")
    for row in null:
        n=int(row["replicates"])
        if n != 100000 or row["allocation_roots_per_stratum"] not in expected_n:
            raise AssertionError("Primary validation did not meet frozen replicate/allocation requirements")
        count=int(row["candidate_rejections"])
        ci=wilson_independent(count,n)
        if abs(row["candidate_type1"]-count/n)>1e-14 or max(abs(a-b) for a,b in zip(ci,row["candidate_type1_wilson95"]))>1e-12:
            raise AssertionError("Type-I summary does not recompute from stored counts")
        cov=1-count/n
        cov_ci=[1-ci[1],1-ci[0]]
        if abs(row["candidate_upper_bound_coverage"]-cov)>1e-14 or max(abs(a-b) for a,b in zip(cov_ci,row["candidate_upper_bound_coverage_wilson95"]))>1e-12:
            raise AssertionError("One-sided bound coverage mismatch")
        ccount=int(row["central_interval_coverage_count"])
        if abs(row["central_interval_coverage"]-ccount/n)>1e-14:
            raise AssertionError("Central interval coverage count mismatch")
        cci=wilson_independent(ccount,n)
        if max(abs(a-b) for a,b in zip(cci,row["central_interval_coverage_wilson95"]))>1e-12:
            raise AssertionError("Central interval Wilson summary mismatch")
    for row in result["primary_power"]:
        count=int(row["candidate_power_count"])
        if abs(row["candidate_power"]-count/row["replicates"])>1e-14:
            raise AssertionError("Power count/rate mismatch")
        ci=wilson_independent(count,row["replicates"])
        if max(abs(a-b) for a,b in zip(ci,row["candidate_power_wilson95"]))>1e-12:
            raise AssertionError("Power Wilson summary mismatch")
    gen=audit_generator()
    inventory_seeds=[r["seed"] for r in INVENTORY["rng_streams"]]
    if len(inventory_seeds)!=len(set(inventory_seeds)) or INVENTORY["collision_count"]!=0:
        raise AssertionError("Seed inventory uniqueness/collision assertion failed")
    decision={"type1_pass":all(max(row["candidate_type1_wilson95"])<=cfg["type1_wilson_upper_max"] for row in null),
              "one_sided_coverage_pass":all(min(row["candidate_upper_bound_coverage_wilson95"])>=cfg["one_sided_coverage_wilson_lower_min"] for row in null),
              "central_coverage_pass":all(min(row["central_interval_coverage_wilson95"])>=cfg["central_coverage_wilson_lower_min"] for row in null)}
    decision["inference_pass"] = all(decision.values())
    out={"audit":"independent recomputation of simulation aggregates and independent RNG family checks",
         "stage5_evaluation_shots_generated":0,"sealed_historical_test_accessed":False,
         "freeze_sha256":hash_file(HERE/"DESIGN_VALIDATION_FREEZE.json"),
         "source_hashes_checked":len(freeze["source_config_protocol_and_inventory_sha256"]),
         "primary_validation_cells_recomputed":len(null),"independent_generator_checks":gen,
         "decision":decision,"limits":["Does not independently rerun every 100k-cell Monte Carlo stream.",
          "Validation supports only the finite prespecified simulation envelope, not arbitrary root-effect distributions."]}
    tmp=HERE/"INDEPENDENT_AUDIT_RESULTS.json.tmp"
    tmp.write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
    os.replace(tmp,HERE/"INDEPENDENT_AUDIT_RESULTS.json")
    print(json.dumps({"decision":decision,"primary_cells":len(null),"generator_checks":len(gen)},indent=2))


if __name__=="__main__":
    main()
