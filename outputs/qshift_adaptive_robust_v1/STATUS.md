# qshift_adaptive_robust_v1: program status (as of 2026-11-20)

This page is the one-page view of the program. Each study's full report is its `*_RESULTS.md`, and `DECISION_REPORT.md` holds the dated addenda. Everything here is simulation at d=5 (rotated Z-memory, 5 rounds) with synthetic weight-3 X-bursts. Nothing has been run on hardware.

## Where things stand

| Question | Answer so far |
|---|---|
| Can the burst-aware decoder (BP+OSD with a learned burst support) beat the strongest deployable matcher when the base noise model is wrong? | **Yes, on development data and on a frozen evaluation for known-family bursts.** In RE1 R1–R5 it was 59–88% below the matcher and matched the oracle. |
| Does it survive a burst it has never seen? | **Not in RE1.** The sealed hidden burst (R6) was never learned, because the estimator flagged every root. The estimator was then rebuilt (BRE → BRS → BRT). **In RE2 (frozen, two new sealed bursts), the result was mixed.** E1T learned the large-footprint sealed burst H3 in 24/24 roots and matched the oracle. It learned H4 in 11/12; the one flagged root failed NI for G5, so the verdict is NOT_CONFIRMED. |
| Does continuous adaptation beat estimating once? | **Not for smooth background drift (AD1).** AD and a single early estimate were both within 1–6% of the oracle. **Yes for a burst that appears and disappears** (AD1 D3: 117 vs 156 errors), but that was not a pre-registered tracking endpoint. |
| Is the 95% LER-reduction target reachable? | **No, with current methods at p = 0.003.** The background floor caps the gain. R stays at about 59–88%. |

## Study ledger

Every row was pre-registered, frozen and run once, with byte-identical analyses and bit-identical replays where a replay was defined.

| Study | Question | Freeze → results | Verdict | Report |
|---|---|---|---|---|
| Step 1 re-decode | Do cheaper BP+OSD search variants lower the background floor? | `600551456` → `6e10de769` | H-F2_FLOOR_DEGENERACY_DOMINATED (no variant advances) | `REDECODE_RESULTS.md` |
| H-E1 | Does re-basing the learner on a detector-estimated p repair mismatch? | `fcd9b8834` | H-E1_PARTIAL (repairs p-scale, not Z-bias) | `HE1_RESULTS.md` |
| H-E1b | Does a joint (p, bias) fit repair Z-bias too? | `6169c6656` | H-E1b_SUPPORTED | `HE1B_RESULTS.md` |
| OG (DEV2) | Off-grid and out-of-family screen of that learner | `fe035cde7` | OG_SUPPORTED | `OG_RESULTS.md` |
| E2E (DEV2) | End-to-end decoding under mismatch | `fe035cde7` | E2E_SUPPORTED (within 1 error of the oracle) | `E2E_RESULTS.md` |
| **RE1** | **Frozen evaluation, including a sealed hidden burst** | `fe4471fff` → `89c2465c3` | **NOT_CONFIRMED** (R1–R5 pass; R6 fails) | `RE1_RESULTS.md` |
| BRE | Burst-robust estimator E1 | `d15e5f47e` → `8e43cca87` | BRE_PARTIAL (240/240 learned; 3/24 out-of-family false accepts) | `BRE_RESULTS.md` |
| BRS | Structural misfit check (subset rule) | `4967cd7d9` → `e89d87a51` | BRS_NOT_SUPPORTED (E1's own threshold flagged 2/32) | `BRS_RESULTS.md` |
| **BRT** | **Threshold-free flag E1T** | `de41bf056` → `551143886` | **BRT_SUPPORTED** (126/128 learned, 0 false accepts in family) | `BRT_RESULTS.md` |
| **AD1** | **Rolling-window adaptive decoding under drift** | `3a2d0209a` → `e6310724d` | **AD1_NOT_SUPPORTED** (tracking: no gain over ONCE) | `AD1_RESULTS.md` |
| **RE2** | **Frozen evaluation of E1T with two new sealed bursts (H3, H4)** | `67ed86c6a` → this commit | **NOT_CONFIRMED** (G1–G4 pass; G5 fails NI on one flagged root) | `RE2_RESULTS.md` |

## What is established (development unless stated)

- **Mismatch repair:** a detector-estimated (p, bias) base model repairs the learner under p-scale and Z-bias mismatch. This is confirmed on a frozen evaluation (RE1 R1–R5).
- **Estimator:** E1T learns bursts of 5–30 detectors across p 0.0020–0.0040 and Z-bias 3–12 without false bursts in family. Out-of-family false bursts are at most 1/32.
- **Sealed burst (frozen, RE2):** E1T → learn → BP+OSD learned a sealed, never-seen ≥ 25-detector burst (H3) in 24/24 roots, under R6's base model and at p 0.00335, matching the oracle. RE1's estimator flagged 10/24 of those roots. This is conditional on H3's independence from RE1's H2, which is untested.
- **Adaptive loop:** the causal rolling-window decoder never harmed a static stream and never learned a wrong burst. It acquired a transient burst within one window (median 5 blocks), released it in a median of 2.5, and stayed within 6% of the oracle under every drift tested.

## What is not established

- **Sealed burst, in full:** RE2's pre-registered claim across all five gated conditions. G5 (H4) failed NI because a single flagged root, decoded nominally, cost 12 errors against a 10-error floor.
- **Background tracking:** that tracking the background rate is worth anything under mild drift (AD1).
- **Scope:** anything at d ≥ 7, on non-synthetic noise, or on hardware.
- **The target:** the 95% target.

## Next decisions (each needs its own owner approval)

1. **Seals:** "Open the RE2 seal" (publish H3/H4) and/or "Open the RE1 seal". The second also runs `re2_contamination.py`, which tests H3/H4's independence from H2. The RE1 record-hygiene note in `RE2_PROTOCOL.md` is still open.
2. **Fallback study (development):** whether a cheaper flag fallback than the nominal model (for example S\*), or more roots, removes the single-flag NI sensitivity RE2 exposed. RE2 is not re-scored.
3. **AD2 (optional, development):** an adaptive study whose drift changes the burst support, such as bursts that switch or move, which is where AD1 showed adaptation pays. AD1's endpoints are not redefined.

## Sealed material (stays closed)

- **RE1 hidden burst H2:** sealed. Publishing anything about it requires the owner's "Open the RE1 seal".
- **RE2 hidden bursts H3, H4:** sealed. The plaintext is outside git, and the commitment is `HIDDEN_COMMITMENT_RE2.json`. Publishing them requires "Open the RE2 seal".
- **V1.6 d=3 seal:** closed.

## Checking the package

```
python outputs/qshift_adaptive_robust_v1/check_package.py
```

This verifies every `*_FREEZE.json` against the tree and runs each test file in its own process. It takes about 2 minutes and does no sampling.
