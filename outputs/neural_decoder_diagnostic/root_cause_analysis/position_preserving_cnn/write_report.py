"""Render the report from independently verified saved evidence."""
import json
import math
from pathlib import Path
import numpy as np

OUT = Path(__file__).resolve().parent
REGIMES = ("x_biased", "balanced", "z_biased")
ARCHS = ("pooled_cnn8", "pooled_cnn16_capacity_control", "position_flat_cnn",
         "coordinate_channel_cnn", "balanced_mlp")
STRATEGIES = ("balanced_minibatches", "weighted_bce")


def pct(x): return f"{100*x:.3f}%"
def pp(x): return f"{100*x:+.3f} pp"


def main():
    result = json.loads((OUT / "VERIFIED_RESULTS.json").read_text(encoding="utf-8"))
    raw = json.loads((OUT / "results.json").read_text(encoding="utf-8"))
    inventory = json.loads((OUT / "seed_inventory.json").read_text(encoding="utf-8"))
    agg = result["aggregate"]
    lines = [
        "# Q-SHIFT Position-Preserving CNN Diagnostic",
        "",
        "## Decision",
        "",
        "**GO for a larger, separately frozen development study of spatially preserving decoders; NO-GO for the prepared 100K run and for any claim of neural superiority.** The results strongly support that global average pooling is a major limitation in this small CNN pilot: position-preserving CNNs were consistently much better than the original pooled CNN on matched samples, including a pooled CNN with a similar parameter count. However, the position CNN did not beat the balanced MLP and all neural models remained worse than frozen PyMatching. The study has only three independent roots, and the reported thresholds were selected on the same validation partition used for the displayed logical-error rates, so those rates are optimistic development metrics.",
        "",
        "## Question and implementation",
        "",
        "The previous geometry-aware CNN used global average pooling. Pooling combines feature responses across grid locations, which can erase *where* a detector pattern occurred. This diagnostic adds two models while preserving the old CNN: (1) `PositionPreservingConv3DDecoder`, which flattens the 3-D feature map into a compact dense head, and (2) `CoordinateChannelConv3DDecoder`, which supplies normalized time, y, and x detector-coordinate channels alongside syndrome and occupancy channels. Both use the actual Stim mapping `(time=6, y=4, x=4)` with 40 occupied detector sites. A wider pooled CNN is included as a capacity control.",
        "",
        "The compared models were the original pooled CNN (8 channels), pooled CNN (16 channels; capacity control), flattened position CNN, coordinate-channel CNN, and the existing direct MLP. Each used either balanced minibatches or weighted BCE. The weighted model logits were corrected by subtracting `log(pos_weight)`; balanced-minibatch logits were shifted back to the natural training prevalence. A temperature grid was fit on a separate validation calibration partition. This calibration correction is not a guarantee of calibrated posterior probabilities.",
        "",
        "## Frozen development design",
        "",
        f"Three independent roots each generated {3*3000:,} training and {3*3000:,} validation shots across X-biased, balanced, and Z-biased regimes: **{3*3*3000:,} training + {3*3*3000:,} validation shots**, plus 96 noiseless structural-check shots. Every model and training strategy used the same detector, observable, and PyMatching arrays within a root. All model families received the same epoch limit and optimizer-step count within a strategy. Balanced minibatching used twelve full 256-example batches per regime per epoch (3,072 presentations versus 3,000 unique examples; 2.4% oversampling), while weighted BCE traversed the 3,000 unique examples. Validation roots were split into equal monitor, calibration, and threshold-selection partitions. The threshold was selected on the threshold partition and evaluated there as well; therefore thresholded logical-error rates are selection-biased and are presented only as development diagnostics. No test samples were generated or accessed.",
        "",
        f"The 30 fits completed in **{raw['runtime_seconds']:.1f} seconds** on **{raw['cuda_device']}**. Peak CUDA allocated/reserved memory was {raw['resources']['cuda_peak_allocated_bytes']/1024**2:.1f}/{raw['resources']['cuda_peak_reserved_bytes']/1024**2:.1f} MiB; end-of-run host RSS was {raw['resources']['host_peak_rss_bytes']/1024**3:.2f} GiB (peak host RSS was not monitored). All 30 fits verified CUDA forward/backward training. The seed inventory reports {inventory['unique_seed_count']} unique streams and no collisions against {inventory['recoverable_historical_seed_values_checked']:,} recoverable historical seed values and the prepared protocol allocation.",
        "",
        "### Aggregate paired validation results",
        "",
        "LER and recall are equal-regime means over three roots. The 95% intervals are paired root-level t intervals with 2 degrees of freedom; they are descriptive, very low-powered intervals, not confirmatory tests. Candidate-only / PM-only are summed shot-level paired failures across 9,000 matched threshold-partition shots.",
        "",
        "| Model | Training | Parameters | LER | PyMatching LER | Neural − PM (95% root CI) | Positive recall | Candidate-only / PM-only |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for arch in ARCHS:
        for strategy in STRATEGIES:
            name = f"{arch}__{strategy}"; row = agg[name]; ci = row["root_t_95ci_paired_difference"]
            title = arch.replace("_", " ")
            train = "balanced" if strategy == "balanced_minibatches" else "weighted BCE"
            lines.append(f"| {title} | {train} | {row['parameter_count']:,} | {pct(row['mean_ler'])} | {pct(row['mean_pymatching_ler'])} | {pp(row['mean_paired_ler_difference'])} ({pp(ci[0])}, {pp(ci[1])}) | {pct(row['mean_positive_recall'])} | {row['candidate_only']} / {row['pymatching_only']} |")
    lines += [
        "",
        "The balanced position CNN matched the balanced MLP on mean LER (1.267%) and was markedly better than the original CNN (5.244%). The coordinate-channel CNN reached 1.689%. PyMatching remained best at 0.411%. For the flattened balanced CNN, paired candidate-only and PM-only failures were 87 and 10; its neural-minus-PM difference was +0.856 percentage points (root t interval +0.511 to +1.200 pp). Thus this diagnostic supports a CNN representation improvement, not an improved decoder over PyMatching.",
        "",
        "### Balanced-minibatch results by generating regime",
        "",
        "Counts pool the three independent roots (3,000 threshold-partition shots per regime). Confusion is shown as TN/FP/FN/TP for predicting the observable-flip label. `paired-only` counts compare logical failures against PyMatching.",
        "",
        "| Model | Regime | Neural LER | Positive recall | TN/FP/FN/TP | Neural-only / PM-only | PM LER |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for arch in ARCHS:
        row = agg[f"{arch}__balanced_minibatches"]
        for regime in REGIMES:
            c = row["by_regime"][regime]
            lines.append(f"| {arch.replace('_',' ')} | {regime} | {pct(c['mean_ler'])} | {pct(c['mean_positive_recall'])} | {c['tn']}/{c['fp']}/{c['fn']}/{c['tp']} | {c['candidate_only']} / {c['pymatching_only']} | {pct(c['mean_pymatching_ler'])} |")
    lines += [
        "",
        "Positive recall improved strongly for both position-aware CNNs relative to pooled CNN8. The false-positive cost is visible in the X-biased and balanced conditions. Regime differences should not be generalized beyond these simulated distance-3, five-round Z-memory settings.",
        "",
        "### Position versus capacity",
        "",
        "The flattened and coordinate-channel models each have parameter counts close to the MLP and the wider pooled control: 13,413; 13,737; 13,569; and 14,769, respectively. The original pooled CNN has 3,929 parameters. Increasing pooled width improved balanced-minibatch LER from 5.244% to 3.889%, but the pooled capacity control remained worse than the flattened CNN. Under balanced minibatches, flattened CNN minus pooled CNN16 was −2.622 pp (root t interval −4.586 to −0.659 pp); coordinate-channel minus pooled CNN16 was −2.200 pp (−4.427 to +0.027 pp). Flattened CNN minus pooled CNN8 was −3.978 pp (−5.367 to −2.589 pp). These comparisons make parameter count alone an unlikely explanation, but do not isolate pooling from all other architectural differences.",
        "",
        "The flattened CNN and balanced MLP had essentially identical average LER; per-root flattened-minus-MLP differences were +0.10, −0.13, and +0.03 percentage points. The coordinate-channel model did not improve on the flattened model in this pilot. Explicit coordinates may be redundant when flattening already preserves location.",
        "",
        "### Sampling strategy and probability calibration",
        "",
        "Balanced minibatches had lower mean threshold-partition LER than weighted BCE for all five model families in these three roots. The weighted approach used the training-only class prevalence to compute `pos_weight`, then applied the appropriate logit offset before temperature calibration. Temperature fitting used only the separate calibration partition. Calibration metrics (Brier score, NLL, and 10-bin ECE) are retained per root in `VERIFIED_RESULTS.json`; root means are summarized below. The threshold partition was then used to choose an LER threshold, so its LER is not an unbiased estimate. Calibration is exploratory and does not justify a probability claim for deployment.",
        "",
        "| Model | Training | Brier raw → temp (calibration split) | ECE raw → temp (calibration split) | Temp Brier / ECE (threshold split) |",
        "|---|---|---:|---:|---:|",
    ]
    for arch in ARCHS:
        for strategy in STRATEGIES:
            rows = [r for r in result["records"] if r["architecture"] == arch and r["strategy"] == strategy]
            cm = [r["probability_calibration"] for r in rows]
            raw_b = np.mean([x["uncalibrated_on_calibration_partition"]["brier"] for x in cm])
            cal_b = np.mean([x["temperature_calibrated_on_calibration_partition"]["brier"] for x in cm])
            raw_e = np.mean([x["uncalibrated_on_calibration_partition"]["ece_10bin"] for x in cm])
            cal_e = np.mean([x["temperature_calibrated_on_calibration_partition"]["ece_10bin"] for x in cm])
            test_b = np.mean([x["temperature_calibrated_on_threshold_partition"]["brier"] for x in cm])
            test_e = np.mean([x["temperature_calibrated_on_threshold_partition"]["ece_10bin"] for x in cm])
            train = "balanced" if strategy == "balanced_minibatches" else "weighted BCE"
            lines.append(f"| {arch.replace('_',' ')} | {train} | {raw_b:.4f} → {cal_b:.4f} | {raw_e:.4f} → {cal_e:.4f} | {test_b:.4f} / {test_e:.4f} |")
    lines += [
        "",
        "## Root cause assessment",
        "",
        "**Supported:** the original pooled CNN’s translation-invariant global pooling is a substantial candidate cause of its poor positive recall in this geometry. The position-aware CNNs improved over both the 8-channel original and the similarly sized 16-channel pooled control on every development root under balanced sampling. Since a similarly parameterized pooled model did not reproduce the improvement, increased parameter count alone is insufficient to explain it.",
        "",
        "**Not established:** this is not a clean causal ablation of absolute position alone. The flattened head changes feature interactions as well as retaining coordinates; the coordinate-channel model also changes its input representation. Only three roots were run, threshold selection and displayed LER share one partition, several model/strategy comparisons were made, and no independent test set was opened. No neural model beat PyMatching. The large LER differences versus PM are all in the wrong direction.",
        "",
        "## Validation, artifacts, and reproducibility",
        "",
        "The Stim geometry and label tests passed; the full dashboard suite passed **47/47** before sampling. A further exact coordinate-ID regression test was added after the run, and the final full suite passed **48/48**. The independent saved-run audit then loaded every best checkpoint, re-evaluated all 30 models, re-selected all temperatures and thresholds from the saved validation partitions, and exactly reproduced 90 model-by-regime prediction arrays and all paired counts. It also checked the saved validation detector/label arrays against each prediction archive. No simulator call was made by the independent audit. The frozen runner's final CSV export had a derived-field naming bug after all results had been saved; `RUNNER_PARTIAL_PER_ROOT.csv` preserves that header-only partial output. The exact frozen runner is retained, and a documented export-only patch fixes future CSV serialization; completed CSVs here were reconstructed independently.",
        "",
        "From the repository root, verify the saved run without sampling:",
        "",
        "```powershell",
        "python outputs/neural_decoder_diagnostic/root_cause_analysis/position_preserving_cnn/audit_saved_run.py",
        "python -m unittest discover -s dashboard/tests -v",
        "python -m compileall -q dashboard outputs/neural_decoder_diagnostic/root_cause_analysis/position_preserving_cnn",
        "```",
        "",
        "For an exact replay, use a clean copy of the repository with the same relative directory structure; the runner refuses to overwrite its existing frozen output. Replaying the same seed inventory is reproducibility, not an independent replication. The independent test allocation remains sealed.",
        "",
        "## Recommendation",
        "",
        "**GO** to a larger development-only replication focused on the flattened position-preserving CNN, balanced MLP, and a strict parameter-matched pooled control; include more independent roots and a separate final evaluation partition with thresholds frozen before evaluation. Do not run the prepared 100K training protocol yet. The current evidence indicates position preservation addresses much of the CNN collapse, but does not establish a useful quantum decoder or an advantage over PyMatching.",
        "",
        "See `VERIFIED_RESULTS.json`, `per_root_results.csv`, `per_regime_results.csv`, `aggregate_results.csv`, `development_samples.npz`, `predictions_rep*.npz`, and the per-fit checkpoints for complete evidence.",
    ]
    report = "\n".join(lines) + "\n"
    (OUT / "POSITIONAL_CNN_REPORT.md").write_text(report, encoding="utf-8")
    (OUT.parent / "POSITIONAL_CNN_REPORT.md").write_text(report, encoding="utf-8")
    print(f"Wrote {OUT / 'POSITIONAL_CNN_REPORT.md'}")


if __name__ == "__main__":
    main()
