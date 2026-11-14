# Prospective controller state-machine specification (not production code)

## Time and information boundary

Let `t` index completed independent shots, not detector rounds inside one circuit. The detector vector from completed shot `t` may update a statistic only after its full detector record has been finalized. A choice made at that point can first affect shot `t+1`. No current-shot detector events, logical label, generating noise label, or future detector vector may be used to select the decoder for shot `t`.

The existing mathematical evidence concerns an exact synthetic circuit with independent per-shot fault sites. It does not establish detector-loop latency, actual decoder rebuild time, or whether recalibration finishes before the next live block. A deployable design needs an explicit buffered boundary: while candidate calibration/reconstruction runs, a validated fixed decoder handles every shot; the new decoder can activate only at a later boundary after model checks succeed.

## Required state data

Any implementation would need a trusted starting-state record, model identity, detector/circuit identity, selected direction, e-process state, alpha ledger, evidence timestamp, last completed shot index, pending recalibration ID, and active decoder hash. State recovery must validate these fields atomically. An alarm is evidence against one null, not proof of the alternative cause or a physical noise estimate.

## Design comparison

| Design | Permitted transition | Statistical premise | Safe behavior | Assessment |
|---|---|---|---|---|
| A. One-sided alarm with static fallback | Trusted initial low state; one preselected upward process; upon alarm move to `ABSTAIN_STATIC` and remain there | The low-regime conditional mean envelope remains valid until the one alarm; one process at threshold `1/alpha` | Keep the robust fixed PyMatching decoder. Do not infer a new p or turn on a high-p graph from the alarm alone | Mathematically defensible as a one-shot alarm/fallback policy if the conditional model holds; not evidence of LER improvement |
| B. Event-triggered recalibration with external verified reset | Alarm enters `RECALIBRATING`; update decoder remains inactive; an independent authorized calibration procedure validates a new state and establishes a fresh epoch | External reset verifies the post-calibration state; each epoch has a valid null and a non-reused alpha allocation | Keep static decoder until validation, identity and latency checks pass; otherwise remain fallback | Plausible architecture, but reset authority, calibration protocol, alpha spending and stopping rules are unspecified. Not ready |
| C. Bidirectional switching with explicit uncertainty | `LOW`, `HIGH`, `UNCERTAIN`, `RECALIBRATING`, `STATIC_FALLBACK`; permit a switch only from a valid state-specific test or verified reset | Both direction-specific nulls must remain valid in their states; switch multiplicity and post-false-alarm state must be controlled | In `UNCERTAIN` or middle band, abstain to fixed decoder; no automatic reverse based solely on the opposing process | **Not supported yet.** The opposite directional null can be false after a false switch; no repeated-switch guarantee or valid reset is established |

## Activation contract

1. Initialize only from an externally trusted regime or choose a policy with a common null valid for all allowed states.
2. Accumulate detector-only statistics from complete shots; labels and hidden simulator regime are never runtime inputs.
3. Validate `alpha∈(0,1]`, exact model identity, counter range, and process-state integrity.
4. Use the exact threshold `1/alpha`, with an outward-safe representation.
5. On an alarm, change to uncertainty/fallback state only. Recalibration is a separate action.
6. Activate new weights only after external calibration verification, DEM construction, compatibility checks, and a future block boundary.
7. If any assumption, state, or latency check is uncertain, use static PyMatching and log abstention.

This is a mathematical architecture specification only. No runtime controller or decoder switching is implemented.
