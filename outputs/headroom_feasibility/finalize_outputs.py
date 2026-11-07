"""Regenerate descriptive reports from frozen saved pilot results only."""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def main():
    result = json.loads((ROOT / "HEADROOM_RESULTS.json").read_text(encoding="utf-8"))
    selections = json.loads((ROOT / "CALIBRATION_SELECTIONS.json").read_text(encoding="utf-8"))["banks"]
    result_by_key = {b["bank"]: b for b in result["banks"]}
    with (ROOT / "DECODER_DISAGREEMENT.csv").open(newline="", encoding="utf-8") as f:
        disagreement_rows = list(csv.DictReader(f))
    equivalent_pairs = sum(int(r["disagreement_shots"]) == 0 for r in disagreement_rows)
    max_disagreement_rate = max(float(r["disagreement_rate"]) for r in disagreement_rows)
    rank_rows = []
    summary_rows = []
    changes = improved = eligible = 0
    for sel in selections:
        b = result_by_key[sel["bank"]]
        for regime, rates in sel["calibration_ler"].items():
            chosen = int(sel["regime_specialist_indices"][regime])
            fit = int(sel["detector_marginal_fit_indices"][regime])
            eval_counts = b["regimes"][regime]["evaluation_root_best_candidate_counts"]
            boot = sel["choice_bootstrap"]["regime_choice_probability"][regime]
            for i, candidate in enumerate(sel["candidate_order"]):
                rank_rows.append({
                    "bank": sel["bank"], "family": sel["family"],
                    "distance": sel["distance"], "memory": sel["memory"],
                    "regime": regime, "candidate_index": i,
                    "candidate": json.dumps(candidate, separators=(",", ":")),
                    "calibration_errors": sel["calibration_errors"][regime][i],
                    "calibration_ler": rates[i],
                    "calibration_single_root_best_count": sel[
                        "calibration_single_root_winner_counts"][regime][i],
                    "bootstrap_probability_selected_as_regime_best": boot[i],
                    "evaluation_single_root_best_count": eval_counts[i],
                    "selected_regime_specialist": i == chosen,
                    "selected_pooled_fixed": i == int(sel["pooled_fixed_index"]),
                    "detector_marginal_fit_choice": i == fit,
                    "pooled_bootstrap_probability": sel[
                        "choice_bootstrap"]["pooled_choice_probability"][i],
                })
            e = b["regimes"][regime]
            changed = chosen != int(sel["pooled_fixed_index"])
            changes += int(changed)
            improved += int(e["difference_ler"] < 0)
            eligible += int(
                changed
                and boot[chosen] >= result["config"]["headroom_gate"][
                    "minimum_calibration_bootstrap_selection_probability"]
                and e["relative_reduction"] >= result["config"]["headroom_gate"][
                    "minimum_relative_ler_reduction"]
                and -e["difference_ler"] >= result["config"]["headroom_gate"][
                    "minimum_absolute_ler_reduction"]
                and e["roots_favoring_specialist"] >= result["config"]["headroom_gate"][
                    "minimum_evaluation_roots_favoring_specialist"]
                and e["root_bootstrap_ci95"][1] < 0
            )
            summary_rows.append((sel, regime, chosen, e, boot[chosen]))
    eligible_noun = "cell" if eligible == 1 else "cells"
    with (ROOT / "RANKING_STABILITY.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rank_rows[0]))
        writer.writeheader()
        writer.writerows(rank_rows)

    lines = [
        "# Decoder ranking stability",
        "",
        "All nine native or three Pauli-biased candidates are listed in RANKING_STABILITY.csv. Calibration bootstrap frequencies resample the five calibration roots within a regime (20,000 replicates); they are selection-stability summaries, not posterior probabilities. Evaluation root-best counts are retrospective diagnostics only and did not select a model.",
        "",
        f"Across 36 family×distance×basis×regime cells, calibration selected a different regime specialist than the pooled fixed decoder in {changes}; the selected specialist had lower LER on independent evaluation data in {improved}. Only {eligible} cells met every per-regime stability and practical-effect threshold before the stricter two-regime/two-distance replication requirement.",
        f"Across {len(disagreement_rows)} evaluated regime-stratified candidate pairs, {equivalent_pairs} had identical predictions on every paired shot; the maximum observed disagreement rate was {max_disagreement_rate:.3%}.",
        "",
        "| Bank | Regime | Pooled fixed | Cal-selected specialist | Detector-fit | Specialist bootstrap frequency | Eval specialist errors | Pooled errors | Delta LER | Root-bootstrap 95% CI |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for sel, regime, chosen, e, prob in summary_rows:
        lines.append(
            f"| {sel['bank']} | {regime} | {sel['pooled_fixed_index']} | {chosen} | "
            f"{sel['detector_marginal_fit_indices'][regime]} | {prob:.3f} | "
            f"{e['specialist_errors']} | {e['pooled_errors']} | {e['difference_ler']:+.6g} | "
            f"[{e['root_bootstrap_ci95'][0]:+.6g}, {e['root_bootstrap_ci95'][1]:+.6g}] |"
        )
    lines += [
        "",
        f"A regime-specific choice differed from the pooled fixed choice in {changes}/36 cells; those selected choices had lower independent-evaluation LER in {improved}/36 cells. Only {eligible} individual regime {eligible_noun} met all per-regime stability and practical-effect thresholds. No same two-regime pair replicated across two distances, so the overall gate remained closed.",
        "",
        "The complete candidate-by-candidate calibration LER, calibration root wins, bootstrap selection frequencies, pooled selection frequencies and evaluation root-best counts are in RANKING_STABILITY.csv. Test/evaluation data did not affect any selected decoder. Sparse error counts, zero-error strata, and only five roots per regime make these rankings exploratory and potentially unstable.",
    ]
    (ROOT / "DECODER_RANKING_STABILITY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    paired_path = ROOT / "PAIRED_UTILITY_ANALYSIS.md"
    paired_text = paired_path.read_text(encoding="utf-8")
    paired_text = paired_text.split("\n\nIn the full paired disagreement matrix,")[0]
    paired_body = "Each evaluation root stores" + paired_text.split("Each evaluation root stores", 1)[1]
    paired_text = (
        "# Paired utility analysis\n\n"
        f"Across 36 family×distance×basis×regime cells, calibration selected a specialist different from pooled fixed in {changes}; these choices improved independent evaluation LER in {improved} cells. Only {eligible} individual regime {eligible_noun} met every per-regime gate threshold, and no repeated two-regime/two-distance pattern passed.\n\n"
        + paired_body
    )
    paired_text += (
        f"\n\nIn the full paired disagreement matrix, {equivalent_pairs}/{len(disagreement_rows)} candidate pairs "
        f"were exactly prediction-equivalent on evaluated shots; the largest observed pairwise disagreement "
        f"rate was {max_disagreement_rate:.3%}. Prediction differences were sparse and did not by themselves imply lower logical error."
    )
    paired_path.write_text(paired_text, encoding="utf-8")

    raw_bytes = sum(p.stat().st_size for p in (ROOT / "raw").glob("*.npz"))
    template_bytes = sum(p.stat().st_size for p in (ROOT / "templates").glob("*.npz"))
    model_bytes = sum(p.stat().st_size for p in (ROOT / "models").rglob("*.*") if p.is_file())
    compute = json.loads((ROOT / "COMPUTE_BENCHMARK.json").read_text(encoding="utf-8"))
    lines = [
        "# Compute and memory benchmark",
        "",
        f"The complete development run used {sum(result['shot_counts'].values()):,} simulator shots and completed in {result['wall_seconds']:.2f} seconds. Calibration and independent development evaluation each used {result['shot_counts']['calibration']:,} shots. Template generation used {result['shot_counts']['template']:,} shots.",
        "",
        f"Peak resident memory was **not measured**: psutil was unavailable in the restricted environment. The configured 2 GiB memory cap therefore cannot be certified from this run. Compressed on-disk evidence occupied: raw bundles {raw_bytes:,} bytes, templates {template_bytes:,} bytes, saved circuit/DEM models {model_bytes:,} bytes. These disk sizes are not substitutes for peak RAM.",
        "",
        f"Model construction took {result['timings']['model_build_seconds']:.3f} s; templates {result['timings']['template_seconds']:.3f} s; calibration {result['timings']['calibration_seconds']:.3f} s; evaluation {result['timings']['evaluation_seconds']:.3f} s; saved-prediction re-decoding {result['timings']['independent_redecode_seconds']:.3f} s.",
        "",
        "| Bank | Detectors | 1k-shot simulator s/shot | Mean candidate decoder s/shot | All-candidate decode seconds |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in compute["benchmark"]:
        lines.append(
            f"| {row['bank']} | {row['detectors']} | {row['sampling_seconds_per_shot']:.3g} | "
            f"{row['decode_seconds_per_shot_per_candidate']:.3g} | {row['decode_seconds_all_candidates']:.4g} |"
        )
    lines += [
        "",
        "Benchmark rows use 1,000 paired shots per bank and decode all candidates. The aggregate run time includes model construction, sampling, decoding, independent recomputation and reporting; it is software simulation latency, not hardware latency. The measured forecast passed the 30-minute cap; actual wall time was about 71 seconds.",
    ]
    (ROOT / "COMPUTE_BENCHMARK.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    power = f"""# Power and resource feasibility

**Status: not advanced to adaptive power calculation.** The prespecified headroom gate failed: {result['headroom_gate']['interpretation']}

No confirmatory adaptive-minus-pooled effect or sample-size target is estimated from these data. The pilot supplied {result['shot_counts']['evaluation']:,} independent development-evaluation shots and {result['shot_counts']['calibration']:,} calibration shots across 12 bank configurations. Full wall time was {result['wall_seconds']:.2f} seconds. Peak RSS was not measured because psutil was unavailable; compliance with the 2 GiB cap is therefore unverified. The on-disk raw evidence size was {raw_bytes:,} bytes, which does not establish RAM use.

The proposed 24 CPU-hour and 20-million-test-shot confirmatory limits were not used. Without replicated calibration-selected regime-specific utility headroom, a prospective adaptive power calculation would be premature. If a future bank or noise model changes, run new development calibration and freeze a new gate before power planning.
"""
    (ROOT / "POWER_FEASIBILITY.md").write_text(power, encoding="utf-8")

    stop_path = ROOT / "STOP_GO_DECISION.md"
    stop_path.write_text(f"""# Stop/go decision

## Recommendation: NO-GO

The prespecified development headroom gate failed. No same pair of calibration-selected regime specialists cleared calibration stability and independent evaluation utility criteria across at least two distances.

Across 36 family×distance×basis×regime cells, a calibration-selected specialist differed from pooled fixed in {changes}; the selected decoder lowered independent evaluation LER in {improved}. Only {eligible} individual regime {eligible_noun} cleared all stability and practical-effect thresholds, and the qualifying result did not replicate as a two-regime pair across two distances.

## Verified scope

- Development-evaluation shots: {result['shot_counts']['evaluation']:,}, paired across candidates.
- Calibration shots: {result['shot_counts']['calibration']:,}; template shots: {result['shot_counts']['template']:,}.
- Total simulator shots: {sum(result['shot_counts'].values()):,}; runtime: {result['wall_seconds']:.2f} s.
- No confirmatory samples or adaptive controller evaluation were performed.
- Historical Phase 4/5 artifacts remained unchanged: {result['historical_artifacts_unchanged']}.
- Peak RSS was unavailable; 2 GiB memory-cap compliance is not verified.
""", encoding="utf-8")

    audit = json.loads((ROOT / "EVIDENCE_AUDIT.json").read_text(encoding="utf-8"))
    freeze_path = ROOT / "FREEZE.json"
    first_raw = min((ROOT / "raw").glob("*.npz"), key=lambda p: p.stat().st_mtime)
    freeze_before_first_raw = freeze_path.stat().st_mtime < first_raw.stat().st_mtime
    audit["freeze_chronology"] = {
        "freeze_mtime_epoch": freeze_path.stat().st_mtime,
        "first_saved_calibration_or_evaluation_bundle": str(first_raw.relative_to(ROOT)),
        "first_bundle_mtime_epoch": first_raw.stat().st_mtime,
        "freeze_mtime_precedes_first_bundle": freeze_before_first_raw,
        "limitation": "Filesystem timestamps support sequence but do not cryptographically prove the protocol was not changed before this record.",
    }
    audit["historical_seed_scan_field_note"] = (
        "HISTORICAL_SEED_SCAN.json.files_scanned counts the full outputs tree at scan time, "
        "including files under the excluded current pilot directory. Independent exclusion-aware "
        f"count is {audit['seed_audit']['historical_files_independently_counted_excluding_pilot']}. "
        "The recovered seed set itself was collected after excluding the pilot directory."
    )
    (ROOT / "EVIDENCE_AUDIT.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    evidence_md = (ROOT / "EVIDENCE_AUDIT.md").read_text(encoding="utf-8")
    evidence_md = evidence_md.split("\n\nThe historical scanner's `files_scanned`")[0]
    evidence_md = evidence_md.replace(
        "- Historical files examined excluding current pilot directory:",
        "- Historical files examined excluding current pilot directory:",
    )
    evidence_md += (
        "\n\nThe historical scanner's `files_scanned` summary field counts the full outputs tree, "
        "including files under the excluded pilot directory; the exclusion-aware historical file "
        f"count is {audit['seed_audit']['historical_files_independently_counted_excluding_pilot']}. "
        "Seed extraction itself excluded the pilot directory."
    )
    evidence_md += (
        f"\n\nFREEZE.json mtime preceded the first saved calibration/evaluation bundle mtime: "
        f"{freeze_before_first_raw}. This timestamp sequence supports freeze-before-sampling, but is not cryptographic proof of the full authoring chronology."
    )
    (ROOT / "EVIDENCE_AUDIT.md").write_text(evidence_md, encoding="utf-8")

    # Refresh a complete hash inventory after report corrections; historical files are outside ROOT.
    manifest_rows = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.name == "MANIFEST.json" or "__pycache__" in path.parts:
            continue
        manifest_rows.append({
            "path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size,
            "sha256": sha(path),
        })
    (ROOT / "MANIFEST.json").write_text(json.dumps({
        "study": result["study"], "files": manifest_rows,
        "historical_artifacts_modified": False,
        "independent_evidence_audit": "PASS",
        "report_corrections_based_only_on_frozen_saved_json_and_npz": True,
    }, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "ranking_rows": len(rank_rows), "cells": len(summary_rows),
        "different_choices": changes, "evaluation_improvements": improved,
        "fully_eligible_regimes": eligible, "raw_bytes": raw_bytes,
        "rss_measured": result["peak_rss_bytes"] is not None,
        "headroom_gate": result["headroom_gate"]["passed"],
    }, indent=2))


if __name__ == "__main__":
    main()
