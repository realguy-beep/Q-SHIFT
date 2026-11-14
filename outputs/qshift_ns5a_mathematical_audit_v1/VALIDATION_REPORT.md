# Validation report

## Environment and scope

- Worktree: separate from the main development checkout; branch `codex/ns5a-mathematical-audit-v1`
- Branch base: `cae447e30d3179ac40586471ee80f535c3c21f87`
- Python used for the deterministic audit: 3.12.10
- New audit module imports only Python standard-library arithmetic/JSON/path modules.
- No Stim sampler, detector-shot generation, random generator, PyMatching decode, training, production seed allocation, or protected outcome access was used.

## Commands and results

```powershell
python -m unittest outputs/qshift_ns5a_mathematical_audit_v1/test_efactor_threshold_audit_v1.py -v
python outputs/qshift_ns5a_mathematical_audit_v1/efactor_threshold_audit_v1.py
```

The final focused suite has 13 tests covering threshold below/equality/above at alpha .05, a second alpha, invalid inputs, corrected-vs-historical predicate behavior, the complete six-category factor-sequence enumeration through length four in both directions, recurrence/direct-sum identity, pointwise fixed-point lower-bound dominance, corrected crossing counts, historical-loop duplicate-prefix accounting, an exact categorical parity identity against toy exhaustive XOR enumeration, edge-inversion boundaries, e-factor nonnegativity/null expectation, saved envelope separation, one saved delay row independently recomputed at `n` and `n-1`, and a no-sampler-import AST check. All 13 passed on the final test invocation. One initial test expectation incorrectly equated the distinct crossing-prefix count (239) with the number of complete paths that cross (238); exact enumeration exposed the mismatch, the assertion was corrected, and no scientific or historical artifact was involved.

## Deterministic arithmetic outcome

- Per direction: 1,554 distinct prefixes and 1,554 exact-vs-recurrence plus lower-bound checks.
- Equivalent historical loop: 5,184 prefix comparisons per direction, with suffix repetition.
- Upward: 239 distinct crossing prefixes; 244 repeated-loop prefix hits; 238 of 1,296 complete length-four sequences cross at least once.
- Downward on complement: zero crossings in all three corrected counts.
- Boundary: 19 does not alarm, 20 alarms, 21 alarms at alpha .05.
- Every fixed-point lower value is no greater than its exact rational mixture in the tested enumeration.
- The largest observed recurrence multiplication is 199 bits upward / 192 bits downward on this bounded fixture; 128-bit multiplication is insufficient. Python's arbitrary precision is why this audit does not overflow.

These counts are deterministic properties of the selected abstract factors and short horizon. They are not empirical false-alarm probabilities or a sequential controller test.

An earlier invocation before the final test suite had 12 passing tests and one AST-check error caused by the test's import-node parser. That test code was corrected; the final 13-test run passed. No historical research test suite was rerun because it was not necessary for this bounded mathematical correction.

## Historical integrity

The pre-existing research package was only read. The correction source and generated JSON are in the new NS-5A directory. The original `EFACTOR_FIXEDPOINT_MIXTURE_AUDIT_PRE_THRESHOLD_FIX.json`, checkpoint-133 source, and original log remain unchanged. A source hash manifest records the input certificate, original source, original artifact, test, corrected source, reports, and corrected audit JSON.

## Decision

Mathematical package: **CORRECTIONS_REQUIRED** (checkpoint-133 historical result corrected in a new version; other numeric certificates retain listed limitations). Controller: **HOLD**. No sampling or further experiment is authorized.
