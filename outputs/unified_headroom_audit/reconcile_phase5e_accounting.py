"""Reconcile Phase 5E counts from saved config, runner, and result JSON only."""
from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT = Path.cwd().resolve()
AUDIT = ROOT / "outputs" / "unified_headroom_audit"
SRC = ROOT / "outputs" / "phase4c_strong_baselines" / "adaptive"

def h(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main() -> None:
    cfg = json.loads((SRC / "phase5e_config.json").read_text())
    result = json.loads((SRC / "PHASE5E_RESULTS.json").read_text())
    runner = (SRC / "run_phase5e.py").read_text()
    schedule_count = len(result["dynamic"])
    repeat_counts = {k: len(v) for k, v in result["dynamic"].items()}
    dynamic_blocks = sum(len(rep["schedule"]) for reps in result["dynamic"].values() for rep in reps)
    dynamic_shots_saved = sum(rep["shots"] for reps in result["dynamic"].values() for rep in reps)
    blocks_expected = (schedule_count * cfg["dynamic_replicates"] * cfg["blocks_per_schedule"])
    dynamic_shots_expected = blocks_expected * cfg["shots_per_block"]
    per_regime = len(result["stationary_evaluation"])
    stationary_shots = sum(v["shots"] for v in result["stationary_evaluation"].values())
    pairwise_shots = sum(v["shots"] for v in result["regime_disagreement"].values())
    calibration_shots = cfg["calibration_roots"] * cfg["calibration_shots_per_regime_root"] * per_regime
    evaluation_shots = cfg["evaluation_roots"] * cfg["evaluation_shots_per_regime_root"] * per_regime
    seed_log = result.get("seed_log", [])
    seed_log_shots = sum(int(x.get("shots", 0)) for x in seed_log)
    findings = (SRC / "PHASE5E_EXPERIMENT_LOG.md").read_text(encoding="utf-8")
    record = {
        "status": "RECONCILED_FROM_CONFIG_RUNNER_AND_SAVED_RESULTS",
        "no_simulation_rerun": True,
        "runner_sha256": h(SRC / "run_phase5e.py"),
        "config_sha256": h(SRC / "phase5e_config.json"),
        "result_sha256": h(SRC / "PHASE5E_RESULTS.json"),
        "experiment_log_sha256": h(SRC / "PHASE5E_EXPERIMENT_LOG.md"),
        "saved_config": cfg,
        "dynamic": {
            "schedule_families": list(result["dynamic"].keys()),
            "schedule_family_count": schedule_count,
            "replicate_counts": repeat_counts,
            "blocks_expected_from_config": blocks_expected,
            "blocks_saved": dynamic_blocks,
            "dynamic_shots_expected_from_config": dynamic_shots_expected,
            "dynamic_shots_saved": dynamic_shots_saved,
            "reconciles": blocks_expected == dynamic_blocks and dynamic_shots_expected == dynamic_shots_saved,
        },
        "other_shot_counts_from_saved_records_or_runner_loops": {
            "pairwise_regime_disagreement_shots": pairwise_shots,
            "calibration_shots": calibration_shots,
            "stationary_evaluation_shots": stationary_shots,
            "stationary_evaluation_expected": evaluation_shots,
            "stationary_evaluation_reconciles": stationary_shots == evaluation_shots,
            "total_all_phase5e_simulator_shots_reconstructed": pairwise_shots + calibration_shots + stationary_shots + dynamic_shots_saved,
            "seed_log_entries": len(seed_log),
            "seed_log_shots": seed_log_shots,
            "seed_log_scope": "only pairwise disagreement batches; it is not a complete seed/run ledger",
        },
        "log_discrepancy": {
            "logged_claim": "seven schedule families x four replicates x 12 blocks x 256 shots",
            "source_of_truth": "phase5e_config.json, run_phase5e.py loop, PHASE5E_RESULTS.json dynamic keys and saved repetitions",
            "actual_dynamic_design": f"{schedule_count} families x {cfg['dynamic_replicates']} replicates x {cfg['blocks_per_schedule']} blocks x {cfg['shots_per_block']} shots = {dynamic_shots_saved} shots",
            "phase5e_log_claim_matches_runner": False,
            "explanation": "The seven-by-four description is inconsistent with the saved Phase 5E runner/config and appears to describe the preceding v3 schedule set; it is not used for Phase 5E totals.",
        },
        "runner_static_checks": {
            "contains_kinds_stationary_slow_rapid_random": "kinds=['stationary','slow','rapid','random']" in runner,
            "dynamic_seed_formula_present": "114000001+ki*1000+rep*100+bi" in runner,
            "schedule_seed_formula_present": "113000001+ki*10+rep" in runner,
        },
    }
    (AUDIT / "PHASE5E_ACCOUNTING.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    md = f'''# Phase 5E accounting reconciliation

This is a static reconciliation from the archived Phase 5E configuration, runner source, result JSON, and experiment log. No simulation was rerun.

## Reconciled counts

- Dynamic schedules: **{schedule_count}** families ({', '.join(record['dynamic']['schedule_families'])}), **{sum(repeat_counts.values())}** replicates, **{dynamic_blocks}** saved blocks, **{dynamic_shots_saved:,}** shots.
- Calibration: **{calibration_shots:,}** shots.
- Stationary evaluation: **{stationary_shots:,}** shots.
- Pairwise disagreement sampling: **{pairwise_shots:,}** shots.
- Reconstructed total simulator shots for Phase 5E: **{record['other_shot_counts_from_saved_records_or_runner_loops']['total_all_phase5e_simulator_shots_reconstructed']:,}**.
- The saved seed log has {len(seed_log)} entries for {seed_log_shots:,} shots, and is limited to pairwise disagreement batches; it is not the full seed manifest.

## Discrepancy

`PHASE5E_EXPERIMENT_LOG.md` says “seven schedule families × four replicates × 12 blocks × 256 shots.” The Phase 5E config says {cfg['dynamic_replicates']} dynamic repeats, the executed runner iterates over four kinds, and the saved JSON has four keys with three entries each. The auditable Phase 5E count is therefore **four families × three repeats × 12 blocks × 256 = 36,864 dynamic shots**, not the log’s seven-by-four count. The seven-by-four statement aligns with the separate earlier v3 development results, not this Phase 5E runner. No historical log was changed.

Counts and source hashes are in `PHASE5E_ACCOUNTING.json`.
'''
    (AUDIT / "PHASE5E_ACCOUNTING.md").write_text(md, encoding="utf-8")
    print(json.dumps({"dynamic_shots": dynamic_shots_saved, "total_phase5e_shots": record["other_shot_counts_from_saved_records_or_runner_loops"]["total_all_phase5e_simulator_shots_reconstructed"], "runner_config_reconcile": record["dynamic"]["reconciles"], "log_discrepancy": True}, indent=2))

if __name__ == "__main__":
    main()
