# Q-SHIFT Stage 4 — Feasibility Review

## Scope and decision boundary

This review audits the existing correlated-noise implementation and defines a 48,000-shot detector-only feasibility pilot. It is not the full Stage 4 experiment, does not use Stage 2/3 final-development labels for fitting, and does not access or enumerate independent-test material. The Stage 4 architecture changes PyMatching's assumed noise model using a calibration batch; it does not ask a CNN to flip the decoder's logical output.

## Historical evidence reviewed

- `outputs/cnn_architecture_stage2_v1/CNN_STAGE2_RESULTS.md` and `CNN_STAGE2_INDEPENDENT_AUDIT.md`: five roots and 260,000 shots independently accounted. On 50,000 synthetic-burst shots, nominal PyMatching made 386 errors, the three CNNs made 389, 395, and 402, while privileged burst-informed PyMatching made 301. The primary V2 equal-condition difference was +0.000090 LER, descriptive 95% root interval [-0.0000294, +0.0002094], and the development gate failed.
- `outputs/cnn_stage3_residual_gate_v1/CNN_STAGE3_RESULTS.md`, `CNN_STAGE3_AUDIT_RESULTS.json`, and `CNN_STAGE3_INDEPENDENT_AUDIT.md`: 200,000 new development shots were independently rescored from 30 saved partitions. The burst-focused residual CNN made exactly the same predictions as nominal PyMatching on the 50,000 burst and 25,000 nominal final-development shots. Its primary burst difference was zero, favorable roots 0/5, and the frozen gate failed. The burst-informed matcher made 273/50,000 burst errors versus 344/50,000 nominal matcher errors. The controller's historical `failed` status records a finalizer import error; it remains unchanged while the audit recovery is separately documented.
- `outputs/phase3a_correlated_noise_preflight/PREFLIGHT_RESULTS.md` and `PHASE3A_FINAL_REPORT.md`: the selected `(8,10)` pair produced a graphlike event record in the DEM; the `enable_correlations` toggle alone changed no predictions in the 256-shot smoke sample. The observed specialist difference came from including the burst event in the DEM, not from evidence that the toggle itself helps.

These are development observations from one distance-3 Z-memory circuit and a synthetic event. They establish neither detector-only probability identifiability nor a hardware-realistic burst rate.

## Exact existing mechanism

`outputs/phase3a_correlated_noise_preflight/simulator.py::build_spatial_burst_circuit` wraps the frozen Phase 2B circuit from `outputs/phase2b_pauli_bias/noise_model.py`. The base circuit uses balanced categorical `PAULI_CHANNEL_1/2` gate noise with per-instruction total probability 0.003, basis-appropriate measurement flips at 0.003, and the recorded bias parameter 10.0. The new event is inserted immediately after each of five `MR` boundaries as a Stim `CORRELATED_ERROR(p) X8 X10`. A triggered event applies X to both data qubits 8 and 10 at that one location; the five round locations are independent Bernoulli sites. This is a synthetic spatial common-cause proxy. It is not a persistent hidden state, coherent crosstalk model, or measured device process.

Stim DEM conversion is fixed at `decompose_errors=True, approximate_disjoint_errors=True`; PyMatching 2.4.0 is built with `enable_correlations=True`. Phase 3A no-shot inspection found five added records, `error(p) D8 D10`, `D16 D18`, `D24 D26`, `D32 D34`, and `D36 D38`, while keeping 40 detectors and one observable. At p=0.01 the graph had five extra edges relative to the no-burst model. Changing p changes those DEM probabilities and thus matching weights. The conversion still approximates the base categorical two-qubit Pauli channels; the synthetic burst itself is graphlike for this selected pair.

## Feasibility conclusion before the pilot

Parameter estimation is plausible but unproven. A triggered event has a detector signature, but ordinary circuit-level faults can produce overlapping signatures and detector bits reveal only the net parity. At p=0.01, the expected burst count is 0.05 events per shot across five sites before cancellation/overlap, so a 2,000-shot calibration batch has limited information. This motivates a small test on unseen intermediate probabilities and several independent seeds.

Rebuilding a valid decoder is technically straightforward: build the unchanged circuit with estimated p, ask Stim for the same configured DEM conversion, then construct a new PyMatching instance. This is safer than assigning arbitrary estimator outputs to matching edges. Validate detector IDs, observable IDs, error records and prediction shapes on every rebuild. The model-informed true-p arm is a privileged ceiling diagnostic, not deployable.

The included scalar profile estimator is intentionally interpretable: it compares detector marginal rates and co-occurrence of the five DEM-identified detector pairs against means generated at three development probabilities. The true probability is used only as a profile-training label and for offline evaluation of estimation error / oracle decoding. `estimate()` accepts only calibration detectors. A neural estimator is not justified unless this small model identifies the parameter but fails for a demonstrated decoder-relevant reason.

The bounded pilot will determine only whether the parameter is distinguishable enough to justify designing a larger, separately frozen development study. Its paired LER results are descriptive (three roots per unseen probability) and cannot establish an adaptive advantage.
