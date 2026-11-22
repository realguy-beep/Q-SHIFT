# CF1 erratum (after independent review)

This addendum responds to the review in `TODAY_INDEPENDENT_REVIEW.md` (branch
`codex/qshift-nov22-independent-review`, commit `82a37ab10`), which returned **PASS WITH CONCERNS**.

`CF1_RESULTS.md`, `CF1_FREEZE.json`, the records and every DB4 file are left unchanged. Where this erratum
disagrees with them, this erratum wins. No new simulation was run. Every number below is computed from the saved
CF1 records.

## What stands

- **DB4:** G1–G6 pass.
- **CF1:** the four frozen Holm decisions (H1–H4 reject H0) reproduce under the frozen procedure.
- **Integrity:** the review found no data leak, no post-result tuning and no arithmetic defect. Seeds, fidelity
  and every archive count were independently re-derived.

## Corrections

### 1. H3 and H4 do not establish *mean* non-inferiority (major)

**The claim in `PLAN_CF1.md` §2 was wrong.** It said the shifted sign-flip test checks "H0: mean d ≥ margin".
It doesn't. The test checks a null in which d − margin is *symmetric about 0*. Rare, skewed harms break that
assumption.

**The review's counter-example** (checked here) shows how. Suppose:
- d = 0 in 99% of episodes;
- d = +200 in the other 1%.

The mean is +2, exactly at the H4 margin. Yet all 48 episodes come out 0 with probability 0.99⁴⁸ = 0.617. When
that happens, the test returns p ≈ 5e−6 and the bootstrap bound is 0. So H4's p value says nothing about rare
large harms. The same applies to H3. Holm cannot repair invalid input p values.

**H3 and H4 are therefore re-labelled** as *conditional decisions under the frozen procedure* (the
symmetric-null assumption), not statistical guarantees on the mean. "No measurable harm" in `CF1_RESULTS.md`
§4 is withdrawn. What the data do support, distribution-free:

| | Observed | One-sided 95% Clopper–Pearson upper bound on P(event) per episode |
|---|---|---|
| H4: W0F − W0 > 0 | 1 of 48 episodes (+2) | 9.5% |
| H4: W0F − W0 > +2 | 0 of 48 | 6.1% |
| H3: W0F − AD3 > 0 | 3 of 6 (+2, +4, +6) | 84.7% |
| H3: W0F − AD3 > +24 | 0 of 6 | 39.3% |

These bound how *often* a harm happens, not how *large* one can be. A bound on the mean would need a bound on
the size of a single harm, and none is pre-registered.

**H1 and H2 are not affected in substance.** Every one of their episodes has d < 0: 37 of 37 for H1 and 18 of
18 for H2. A sign test, which assumes no symmetry, gives p = 2⁻³⁷ ≈ 7e−12 and 2⁻¹⁸ ≈ 4e−6. So the median
difference is negative under either test.

### 2. Freeze hash does not match the committed bytes for one file (major, reproducibility)

`CF1_FREEZE.json` lists `outputs/qshift_adaptive_robust_v1/ad3.py` with SHA-256 `98f5a62b…`. That is the hash
of the local Windows working copy, which has **CRLF** line endings. The committed blob is **LF**
(`.gitattributes` sets `eol=lf`) and hashes to `febfd055…`.

Checked here:
- 53 of 54 freeze hashes match the committed blobs at `d50d522df`; `ad3.py` is the only exception.
- Converting the local file to LF gives exactly the committed blob, so the code that ran is the committed code.
- On a fresh LF checkout, the CF1 run guard would refuse to start.

The existing hash is kept as historical evidence, not rewritten.

**The freeze also missed some inputs.** It omitted lazily imported estimator sources (`ad1.py`, `brt.py`,
`estimate2`–`5.py`) and runtime data files (`BRS_BURSTS.json`, `BRT_BURSTS.json`, `CLASSES_D5.json`,
`NULL_THRESHOLD.json`). The cause: `freeze_files()` collected only modules imported at freeze time in the
parent process. None of these files changed between the DB4 code commit `089a94741` and the CF1 results commit
`04b60cbee`, and the working tree had no local edits.

### 3. Scope of each claim (major)

- **H1** compares W0F against one pre-selected fixed decoder: BP+OSD with key A, the lowest training risk among
  the five bank keys. It does not compare against the best fixed decoder for each panel. On N_C the C key would
  tie W0F; A has 544 errors to W0F's 92.
- **H2** compares whole policies, W0's gate against DB1's BANK. These differ in next-state risk handling and
  hysteresis, so CF1 does not isolate which part produces the gain.
- **H3** is one A→E challenge, U. E lies outside the bank but inside the learner's class catalog, so this is not
  evidence of open-set generalization. On U, 113 blocks had an empty plausible set: the learner was used 109
  times and the fallback 4 times. All 12 net excess errors against AD3 came after the switch.
- **Calibration:** every adaptive arm uses 2,000 unlabelled detector rows and 250 labelled calibration rows per
  block.

### 4. The fallback's benefit remains unproven (major)

| Study | Fallback visits | Key changes vs W0 | W0F-only errors | W0-only errors |
|---|---|---|---|---|
| DB4 | 6 | 2 | 1 | 0 |
| CF1 | 11 | 7 | 2 (U_e2, block 18) | 0 |

The fallback has shown no paired gain on any fresh episode. Its one demonstrated improvement, DB3 AA_e1
(132 → 35 errors), is retrospective development evidence: that episode was used to design the rule.

### 5. Minor corrections

- **Episode count.** `PLAN_CF1.md` §1 says the development table pools "41 stored DB3 and DB4 episodes". DB3
  has 18 and DB4 has 21, so the correct number is **39**. The 41 is the DB2 + DB3 replay set used in DB4.
- **Retry rule.** `cf1_run.py` treats every worker exception as retriable, but the protocol allows a retry only
  for infrastructure failures. No retry happened in CF1, so the results are unaffected.
- **Archive checks.** The analyzers check archive hashes and error sums, but not the exact packed-array width or
  the set of keys. This had no effect on the saved results.
- **Wording.** `CF1_RESULTS.md` §3 says "every changing-noise panel". The correct scope is the seven pre-specified
  H1 panels, which include the constant-noise panel N_C.

## Before any further frozen run

1. Build a portable manifest: hash committed blobs (or LF-normalized bytes), bind transitive and lazy inputs and
   data files, and record the environment. Test the guard on a fresh LF checkout.
2. Validate archives strictly, checking exact width and key set.
3. Handle retries by type: an infrastructure failure gets a retry; a code error stops the run.
4. Add a mocked truth-invariance test. Perturbing truth metadata, current-block calibration and evaluation labels
   must leave adaptive decisions unchanged.
5. Pre-register inference that stays valid for sparse, skewed harms, for example a bounded-harm mean bound or a
   harm-rate criterion.

## Needs a new experiment (not done here)

- **Fallback utility and safety:** a pre-registered paired W0F/W0 study. It needs a stale-key challenge panel
  that creates enough trigger opportunities, with opportunity defined before scoring.
- **Broader decoder or open-set claims:** an independently tuned static comparator, a same-hysteresis gate
  ablation, and noise classes outside both the bank and the learner catalog.
