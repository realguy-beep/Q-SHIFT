"""Publish lightweight V1.1 result summaries from independently saved-array analysis."""
from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUN = ROOT / "pilot_runs/attempt_001"


def main() -> None:
    result = json.loads((RUN / "analysis.json").read_text(encoding="utf-8"))
    status = json.loads((RUN / "status.json").read_text(encoding="utf-8"))
    identity = json.loads((RUN / "execution_identity.json").read_text(encoding="utf-8"))
    if status.get("state") != "completed" or result.get("evaluation_shots") != 60000:
        raise RuntimeError("cannot publish incomplete V1.1 results")
    shutil.copyfile(RUN / "paired_results.csv", ROOT / "PAIRED_RESULTS.csv")
    (ROOT / "RESULTS_SUMMARY.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                                                encoding="utf-8", newline="\n")

    lines = [
        "# Q-SHIFT correlated decoder feasibility V1.1 — performance report",
        "",
        f"**Decision:** {result['decision']}  ",
        "**Classification:** one exploratory development evaluation; not independent confirmation.",
        "",
        "## Execution identity and evidence",
        "",
        f"- Frozen source commit: `{identity['git_head']}`",
        f"- Pretest freeze SHA-256: `{identity['pretest_freeze_sha256']}`",
        f"- New paired evaluation: {status['shots_committed']:,} shots across 30 roots and 30 sampler calls.",
        "- Reused V1 development evidence: 3,000 training + 15,000 calibration detector rows from 33 SHA-256-verified archives.",
        "- The V1.1 setup loaded only detector arrays from those archives; the stored V1 observable arrays were not read or copied.",
        "- V1.1 generated fresh evaluation samples; all four decoders received the same detector rows, and labels were inspected only after prediction completion.",
        "- No Stage 5, sealed-test, or independent-test data were accessed.",
        "",
        "## Paired error rates",
        "",
        "| Condition q | Arm A fixed PM | Arm A2 root PM | Arm B calibrated factor | Arm C true-q reference |",
        "|---:|---:|---:|---:|---:|",
    ]
    for q in ("0.0", "0.01", "0.02"):
        roots = result["root_results"][q]
        total = {arm: sum(row[f"{arm}_errors"] for row in roots) for arm in ("A", "A2", "B", "C")}
        shots = sum(row["shots"] for row in roots)
        lines.append(f"| {q} | " + " | ".join(f"{total[arm]}/{shots} ({total[arm]/shots:.6f})" for arm in ("A", "A2", "B", "C")) + " |")
    lines += [
        "",
        "## Primary and safety results",
        "",
        f"- Primary estimand, equal-weight nonzero-q `LER(B)-LER(A)`: `{result['primary_estimand_B_minus_A_equal_weight_q0_01_q0_02']:.8f}`.",
        f"- Root-stratified paired percentile 95% interval: `{result['primary_two_sided_95_percentile_ci']}`.",
        f"- Zero-burst q=0 B-minus-A bootstrap 5th/95th percentiles: `{result['q0_B_minus_A_bootstrap_5th_95th_percentiles']}`; harm tolerance `+0.0005`.",
        f"- Equal-weight nonzero-condition LERs: `{json.dumps(result['equal_weight_nonzero_condition_ler'], sort_keys=True)}`.",
        f"- Descriptive relative reduction B vs A: `{result['relative_reduction_B_vs_A_descriptive']}`.",
        f"- B-only errors vs A: `{sum(row['B_only_errors_vs_A'] for rows in result['root_results'].values() for row in rows)}`; A-only errors vs B: `{sum(row['A_only_errors_vs_B'] for rows in result['root_results'].values() for row in rows)}`.",
        "- B versus A2 is the exploratory representation contrast; B versus A combines representation and calibration scope.",
        "",
        "## Limits and interpretation",
        "",
        "This is one small development evaluation with ten roots per condition, one synthetic common-cause noise construction, a small calibration set, and an exploratory root bootstrap. The finite-factor method is not exact whole-circuit maximum likelihood. C is a privileged true-q reference. The study cannot establish broad decoder superiority or independent confirmation. No follow-up sampling is authorized by the result.",
        "",
        f"- Runner-observed runtime: `{status.get('runtime_seconds_before_final_status')}` seconds.",
        f"- Sampled current-process RSS high-water: `{status.get('sampled_current_rss_high_water_bytes')}` bytes; this is not a hard process-tree memory cap.",
        f"- Decoder/inference timing record: `{json.dumps(status.get('timings', {}), sort_keys=True)}`.",
        f"- Analysis/recovery evidence: local run directory `pilot_runs/attempt_001/`; raw per-shot archives remain ignored and are not committed.",
        "",
    ]
    (ROOT / "PERFORMANCE_REPORT.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(json.dumps({"decision": result["decision"],
                      "report": str(ROOT / "PERFORMANCE_REPORT.md"),
                      "paired_rows": len(result["root_results"]["0.0"]) + len(result["root_results"]["0.01"]) + len(result["root_results"]["0.02"])}, indent=2))


if __name__ == "__main__":
    main()
