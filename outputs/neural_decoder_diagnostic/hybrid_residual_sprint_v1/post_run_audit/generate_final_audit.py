"""Build read-only, post-run reports from the frozen sprint evidence.

This script never loads independent-test files and never changes the run tree.
It recomputes row and aggregate arithmetic from RESULTS.json and
PAIRED_EVALUATION.csv, then writes reports beside the post-run audit scripts.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path


AUDIT = Path(__file__).resolve().parent
BASE = AUDIT.parent
RUN = BASE / "run"
REPO = BASE.parents[2]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def pct(x: float) -> str:
    return f"{100 * x:.6f}%"


def pp(x: float) -> str:
    return f"{100 * x:.6f} pp"


def fmt_n(x: float) -> str:
    return f"{x:,}"


def load_inputs():
    results = json.loads((RUN / "RESULTS.json").read_text(encoding="utf-8"))
    progress = json.loads((RUN / "PROGRESS.json").read_text(encoding="utf-8"))
    error = json.loads((RUN / "ERROR.json").read_text(encoding="utf-8"))
    cfg = json.loads((BASE / "config.json").read_text(encoding="utf-8"))
    recompute = json.loads((AUDIT / "INDEPENDENT_RECOMPUTATION.json").read_text(encoding="utf-8"))
    inventory_audit = json.loads((AUDIT / "SAVED_ARTIFACTS_AUDIT.json").read_text(encoding="utf-8"))
    with (RUN / "PAIRED_EVALUATION.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return results, progress, error, cfg, recompute, inventory_audit, rows


def main() -> None:
    results, progress, error, cfg, recompute, inventory_audit, rows = load_inputs()
    assert progress["status"] == "failed"
    assert results["status"] == "completed_development_only"
    assert len(progress["completed_jobs"]) == 30 == progress["target_jobs"]
    assert len(results["training_jobs"]) == 30
    assert len(rows) == 135
    assert len(results["summary"]) == 9
    expected_final = (cfg["sampling"]["final_development_shots_per_regime_root"]
                      * cfg["roots"] * len(cfg["circuit"]["regimes"]))
    assert expected_final == 225_000
    assert recompute["final_development_shots"] == expected_final
    assert recompute["final_development_shots_total"] == expected_final
    train = cfg["sampling"]["train_budgets_per_regime_root"][-1] * cfg["roots"] * len(cfg["circuit"]["regimes"])
    other = sum(cfg["sampling"][k] for k in (
        "monitor_shots_per_regime_root", "calibration_shots_per_regime_root",
        "threshold_selection_shots_per_regime_root", "final_development_shots_per_regime_root"))
    production = (train + other * cfg["roots"] * len(cfg["circuit"]["regimes"]))
    assert production == results["unique_production_shots"] == 1_665_000

    # Independent arithmetic checks: recombine all per-root paired rows and
    # compare them to the frozen JSON summary cells.
    lookup = {}
    for r in rows:
        key = (r["strategy"], int(r["train_size_per_regime"]), r["policy"])
        lookup.setdefault(key, []).append(r)
    for s in results["summary"]:
        cell = lookup[(s["strategy"], int(s["train_size_per_regime"]), s["policy"])]
        assert len(cell) == 15
        assert sum(int(x["shots"]) for x in cell) == 225_000
        assert sum(int(x["errors"]) for x in cell) == s["pooled_errors"]
        assert sum(int(x["pymatching_errors"]) for x in cell) == 1_129
        assert sum(int(x["candidate_only"]) for x in cell) == s["candidate_only"]
        assert sum(int(x["pymatching_only"]) for x in cell) == s["pymatching_only"]
        assert math.isclose(s["pooled_ler"], s["pooled_errors"] / 225_000, abs_tol=1e-12)

    # Save a clean derived per-regime table and a full root-level copy for
    # reader convenience, leaving the runner's original files untouched.
    regime_rows = results["per_regime"]
    with (AUDIT / "AUDITED_PER_REGIME.csv").open("w", newline="", encoding="utf-8") as f:
        fields = ["strategy", "train_size_per_regime", "policy", "regime", "shots", "errors", "ler",
                  "pymatching_errors", "pymatching_ler", "paired_difference", "candidate_only",
                  "pymatching_only", "beneficial_corrections", "harmful_corrections"]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in regime_rows:
            w.writerow({k: r[k] for k in fields})
    with (AUDIT / "AUDITED_PER_ROOT.csv").open("w", newline="", encoding="utf-8") as f:
        fields = list(rows[0].keys())
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    summary_lines = [
        "| Training strategy | Samples / regime / root | Policy | Errors / 225,000 | LER | Paired Δ vs PM (95% root bootstrap CI) | Candidate-only / PM-only | Root wins/losses/ties | Sign-flip p | Holm p |",
        "|---|---:|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for s in results["summary"]:
        ci = s["root_paired_bootstrap_ci95"]
        delta = f"{pp(s['root_paired_delta']['mean'])} [{pp(ci['low'])}, {pp(ci['high'])}]"
        summary_lines.append(
            f"| {s['strategy']} | {s['train_size_per_regime']:,} | {s['policy']} | "
            f"{s['pooled_errors']:,} | {pct(s['pooled_ler'])} | {delta} | "
            f"{s['candidate_only']} / {s['pymatching_only']} | "
            f"{s['roots_won_vs_pm']}/{s['roots_lost_vs_pm']}/{s['roots_tied_vs_pm']} | "
            f"{s['exploratory_root_signflip_p']:.4g} | {s['holm_p_over_all_candidate_policies']:.4g} |"
        )

    regime_lines = [
        "| Strategy | N / regime | Policy | Regime | Candidate errors / 75,000 | Candidate LER | PM errors / 75,000 | PM LER | Paired Δ | Root mean Δ (95% t CI) | Candidate-only / PM-only |",
        "|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in regime_rows:
        regime_lines.append(
            f"| {r['strategy']} | {r['train_size_per_regime']:,} | {r['policy']} | {r['regime']} | "
            f"{r['errors']:,} / {r['shots']:,} | {pct(r['ler'])} | "
            f"{r['pymatching_errors']:,} / {r['shots']:,} | {pct(r['pymatching_ler'])} | "
            f"{pp(r['paired_difference'])} | "
            f"{pp(r['root_paired_delta']['mean'])} "
            f"[{pp(r['root_paired_delta']['ci95_low'])}, {pp(r['root_paired_delta']['ci95_high'])}] | "
            f"{r['candidate_only']} / {r['pymatching_only']} |"
        )

    primary = next(s for s in results["summary"] if s["strategy"] == "balanced_minibatch"
                   and s["train_size_per_regime"] == 60_000 and s["policy"] == "confidence_gate")
    selection_records = [json.loads(p.read_text(encoding="utf-8"))
                         for p in (RUN / "selections").glob("*.json")]
    confidence_jobs = [j for j in selection_records if j["strategy"] == "balanced_minibatch"]
    assert len(confidence_jobs) == 15 and all(j["confidence_gate"]["fallback"] for j in confidence_jobs)

    report = f"""# Q-SHIFT Hybrid Residual Sprint — Audited Final Research Report

**Study class:** development-only feasibility study; not confirmatory.  
**Controller state:** `failed` during finalization.  
**Scientific evidence status:** saved training/evaluation evidence independently recomputed and passed; no training restart was performed.  
**Independent-test access:** 0; the test allocation remains sealed.

## Executive finding

The frozen sprint completed all **30/30 training jobs** across five independent development roots and generated the planned **1,665,000 unique production shots**, plus **384 diagnostic shots**. It evaluated **225,000 paired final-development shots** (five roots × three regimes × 15,000). The independent read-only verifier re-decoded all 30 saved prediction archives, recomputed the selected-model probabilities and all 135 paired metric rows, and reproduced the aggregate and root-level statistics. The final evidence audit passes, with an important operational exception: the controller itself recorded `failed` because its verifier was called before the controller changed status from sampling to completed. The runner therefore did not create its own checkpoint manifest.

Frozen PyMatching made **1,129/225,000 errors (0.501778% LER)**. The predeclared primary candidate—balanced residual CNN, 60,000 training shots per regime/root, confidence-gated correction—also made **1,129 errors**, exactly matching PyMatching on every evaluated shot. Its paired LER difference was zero; all five root clusters tied. The gate selected no residual corrections in all five primary-root selections, so correction precision is not estimable. The predeclared development gate failed. **Recommendation: NO-GO for scaling this residual decoder to 10M or 60M shots.**

## Design and audit scope

The frozen task was Z-memory, rotated surface code, distance 3, five rounds, 40 detectors, one logical observable, with 0.003 gate and measurement probabilities and x-biased, balanced, and z-biased regimes. Each model was a residual 3-D CNN correcting the frozen Phase 2B PyMatching prediction. Final output followed the frozen convention: PyMatching prediction XOR predicted residual. The two training approaches were balanced minibatches and natural sampling with training-only inverse-prevalence weighting. Per-regime training budgets were 10k, 30k, and 60k; calibration, threshold selection, and final development evaluation used separate generated streams. No final-evaluation labels entered fitting, checkpoint choice, temperature selection, thresholds, or gate decisions according to the frozen protocol and audited source/data partitions.

The audit validated frozen configuration and source hashes; data archive hashes, seed maps, and partition sizes; all 30 model-weight and optimizer-state checkpoint hashes; all 30 prediction archive hashes and bindings to frozen selections; 135 paired evaluation rows; and independent PyMatching re-decoding / CNN prediction recomputation. The final-development samples were paired across each candidate and its PyMatching baseline. Five roots are the inferential clusters; shot counts do not replace the small root count.

## Frozen comparisons

LER differences below are candidate minus PyMatching; negative is favorable. Root-bootstrap intervals resample the five independent roots and are descriptive. All nine Holm-adjusted p-values equal 1.0. See the source JSON and `AUDITED_PER_ROOT.csv` for root values.

{chr(10).join(summary_lines)}

For the primary confidence-gated 60k candidate, PyMatching and candidate each had **1,129 errors**; candidate-only / PyMatching-only failures were **0 / 0**, paired delta **0.000000 percentage points**, root bootstrap interval **[0, 0]**, exact root sign-flip p = **1**, and Holm p = **1**. There was no change in prediction on the evaluated samples.

## Results by generating regime

Each row pools 75,000 paired shots (five roots × 15,000) for that regime. The complete per-root input rows are preserved in the derived audit CSV.

{chr(10).join(regime_lines)}

Baseline regime counts were x-biased **617/75,000 (0.822667%)**, balanced **393/75,000 (0.524000%)**, and z-biased **119/75,000 (0.158667%)**. No candidate was better in the aggregate than fixed PyMatching. Some threshold-selected candidates traded small gains in one regime against losses in another. The largest apparent regime gains remain exploratory and are not reliable evidence of specialization with five roots and nine comparisons.

## Learning and paired correction diagnostics

The confidence-gated balanced candidates fell back exactly to PyMatching in **15/15** root × training-size selections. For the non-gated threshold-minimized candidates, useful and harmful residual corrections were mixed:

- Balanced 10k: 20 PyMatching-only errors corrected versus 28 candidate-only failures; aggregate LER was worse.
- Balanced 30k: 23 versus 23; aggregate LER tied, despite root-level variation.
- Balanced 60k: 48 versus 56; aggregate LER was worse.
- Weighted-natural 10k: 2 versus 4; worse.
- Weighted-natural 30k: 16 versus 21; worse.
- Weighted-natural 60k: 20 versus 20; aggregate tie.

The best monitor checkpoint was restored before calibration, per the frozen protocol. This study shows that the CNN can emit some nonzero residual corrections under threshold-minimized policies, but their utility did not beat the matching baseline. It does not establish that additional examples will fix the problem. The confidence gate's conservative all-fallback behavior avoided added errors but also delivered no gain.

## Resource use

Recorded active wall time was **1,211.8 s (20.2 min)**; CUDA training and selection **684.9 s**; CUDA inference **4.5 s**; maximum process RSS **1.405 GiB**; maximum CUDA allocation **0.066 GiB**; minimum free disk **252.49 GiB**. The frozen resource limits were not exceeded.

## Limitations and decision

This is a small feasibility study with five independent roots. Root t intervals and 100,000-resample root bootstraps are descriptive, and exact sign-flip tests have coarse resolution at n=5. The nine candidate/policy/budget comparisons were exploratory and Holm-adjusted. The endpoint is simulated development LER under one distance, basis, and noise family; there is no hardware evaluation, no independent test evaluation, and no claim of generalization. No direct MLP, non-residual CNN, or pooled CNN arm was part of this sprint; prior runs must not be conflated with these residual-CNN results.

**Decision: NO-GO for 10M/60M scaling under the current model and protocol.** Keep frozen PyMatching as the default. A non-training administrative recovery may preserve an external audit manifest and corrected report; do not relaunch or resume this experiment. Any future training effort should first present a distinct, evidence-based hypothesis and a separately frozen bounded development design. The runner's failed status should remain in the historical run record.

## Reproduction and evidence

The run was manually launched using the frozen controller. Read-only evidence recomputation was performed with `post_run_audit/verify_saved_results_after_runner_failure.py`; report tables are regenerated by `post_run_audit/generate_final_audit.py`. Neither script samples new shots or accesses test data. See `RUNNER_FAILURE_DIAGNOSIS.md`, `NEXT_EXPERIMENT_DECISION_AUDITED.md`, and `FINAL_EVIDENCE_MANIFEST.json`.
"""
    (AUDIT / "FINAL_RESEARCH_REPORT_AUDITED.md").write_text(report, encoding="utf-8")

    decision = f"""# Further Scaling Decision — Q-SHIFT Hybrid Residual Sprint

## Decision: NO-GO

Do not scale the current residual-CNN experiment to 10M or 60M shots. The frozen primary candidate was balanced minibatch training at 60k samples per regime/root with the confidence-gated residual policy. It produced **1,129 errors / 225,000 shots (0.501778% LER)**, exactly the same paired result as frozen PyMatching. Its paired delta was zero with five root ties, zero discordant outcomes, and no corrections selected. It fails the frozen minimum improvement of 0.0002, the four-of-five favorable-root criterion, the negative bootstrap-upper-bound criterion, and the precision criterion (precision is undefined because the gate made zero corrections).

No other frozen candidate had fewer aggregate errors than PyMatching. The lowest-error alternatives tied the baseline and had root-level confidence intervals spanning zero; all nine Holm-adjusted p-values were 1.0. Five independent roots are insufficient for confirmatory inference, so this is a development feasibility decision, not proof of equivalence.

## Operational status

The Python controller is terminal and its persisted state is `failed`; it is not running (`PID 11656` absent, no sprint lock). All 30 jobs, data partitions, predictions, and evaluations are present and pass the separate read-only evidence audit. The controller's only failure was the final verifier/status ordering described in `RUNNER_FAILURE_DIAGNOSIS.md`. Do not restart or resume training. Keep the historical `failed` status and use the external audit manifest for the verified evidence inventory.

## Independent test

Independent-test access was **0**. No independent-test files or test labels were read. The independent test remains sealed.
"""
    (AUDIT / "NEXT_EXPERIMENT_DECISION_AUDITED.md").write_text(decision, encoding="utf-8")

    failure = f"""# Runner Failure Diagnosis — Hybrid Residual Sprint v1

## Observed terminal state

The controller's persisted `run/PROGRESS.json` says `failed`, with `current_phase=final_evaluation`, all **30/30 jobs** committed, all five roots trained, and **1,665,000/1,665,000** planned production shots attempted and committed. PID 11656 is no longer running; no `sprint.lock` remains. `run/ERROR.json` contains the complete traceback. `run/CHECKPOINT_MANIFEST.json` is absent.

## Root cause

`run_sprint.py` invokes `verify_results.py` at finalization before it writes the final `PROGRESS.status="completed"`. The verifier's first gate requires exactly that status and raises `AssertionError: Run is not complete: sampling`. The runner wraps the nonzero verifier exit as `RuntimeError("Independent evidence verifier failed ...")` and marks the controller `failed`. This is a lifecycle/finalization ordering defect, not a sampling, training, checkpoint, prediction, or paired-metric failure.

The immutable historical runner verifier also had a separate configuration-key issue discovered during the read-only verification attempt: it referred to `monitor_per_regime_root`, `calibration_per_regime_root`, and `threshold_selection_per_regime_root`, while the frozen configuration uses the corresponding `*_shots_per_regime_root` keys. The audit used a separate copy under `post_run_audit/` with only the finalization-status precondition and these config-key names corrected. The frozen source was not edited.

## Evidence and safe recovery

The saved-evidence inventory passed: 30 checkpoint sets, 30 prediction archives, 135 paired rows, all expected data partition hashes/seed maps, selections, optimizer states, and frozen source hashes. A separate verifier re-decoded the 30 saved PyMatching predictions, recomputed CNN outputs from selected weights, and matched every candidate aggregate and root statistic. It passed with **225,000 final development shots** and `independent_test_access=0`.

An initial post-run audit serializer incorrectly reported 333,000 in one field by dividing all 1,665,000 production shots by five roots. That arithmetic was invalid for the final evaluation partition. The audit-only serializer has been corrected and rerun; the validated count is **15,000 × 5 roots × 3 regimes = 225,000**, now consistent in both fields. No run data or frozen files were changed.

## Recommendation

Do not relaunch/resume the experiment. The scientific calculations are complete and evidence-audited, while the controller's historical status remains failed. Any code repair for future experiments should ensure the verifier accepts a well-defined `finalizing` state (or verifies candidate results before the completed-status commit), fix the config key names, and only then atomically write completion status and the checkpoint manifest. Do not retrofit the original run to say the controller completed.
"""
    (AUDIT / "RUNNER_FAILURE_DIAGNOSIS.md").write_text(failure, encoding="utf-8")

    # Hash frozen definitions, saved development evidence, audit code and
    # reports. The test allocation is intentionally neither enumerated nor read.
    files: list[Path] = []
    for p in BASE.rglob("*"):
        if not p.is_file() or "__pycache__" in p.parts:
            continue
        if p.name == "FINAL_EVIDENCE_MANIFEST.json":
            continue
        files.append(p)
    # Also retain the specific Phase 2B model/generator source references
    # named by the freeze; independent test namespaces remain excluded.
    freeze = json.loads((BASE / "FREEZE.json").read_text(encoding="utf-8"))
    frozen_paths = []
    for rel in freeze.get("source_sha256", {}):
        p = REPO / Path(rel)
        if p.exists() and p.is_file():
            frozen_paths.append(p)
    files.extend(frozen_paths)
    # Make paths unique and ensure the new report artifacts enter the evidence.
    unique = {p.resolve() for p in files}
    entries = []
    for p in sorted(unique, key=lambda x: str(x).lower()):
        try:
            rel = p.relative_to(REPO.resolve()).as_posix()
        except ValueError:
            rel = str(p)
        entries.append({"path": rel, "bytes": p.stat().st_size, "sha256": sha256(p)})
    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "read-only audit of development sprint artifacts; independent-test files were not accessed",
        "run_status_preserved": progress["status"],
        "scientific_evidence_audit": recompute["status"],
        "independent_test_access": 0,
        "final_development_shots_verified": expected_final,
        "production_shots_verified": production,
        "files_hashed": len(entries),
        "manifest_self_hash_excluded": True,
        "files": entries,
    }
    (AUDIT / "FINAL_EVIDENCE_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "reports": [
        "FINAL_RESEARCH_REPORT_AUDITED.md", "NEXT_EXPERIMENT_DECISION_AUDITED.md",
        "RUNNER_FAILURE_DIAGNOSIS.md", "AUDITED_PER_REGIME.csv", "AUDITED_PER_ROOT.csv",
        "FINAL_EVIDENCE_MANIFEST.json"], "final_shots": expected_final,
        "production_shots": production, "hashed_files": len(entries),
        "independent_test_access": 0}, indent=2))


if __name__ == "__main__":
    main()
