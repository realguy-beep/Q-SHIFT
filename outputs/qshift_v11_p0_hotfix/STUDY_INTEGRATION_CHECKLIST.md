# Study integration checklist (P1: all OPEN)

None of this is done or closed by the P0 hotfix. Each item must be resolved and independently checked before the relevant study freeze. It restates Codex's `REAL_RUNNER_INTEGRATION_CHECKLIST.md` and `MINIMUM_EVIDENCE_SCHEMA.md` (abc1ae474); those are authoritative.

## Canonical callback, preflight and import binding (NEW-3)
- [ ] One study launcher that fixes the job, preflight, decoder factory, sampler and analyser. No caller-supplied callback, pool or hook on the execution path.
- [ ] Preflight builds every declared fixed key with the real factory. A rule for learned keys that do not build is declared in advance.
- [ ] A fresh interpreter with declared import roots and no stale bytecode. Module origins outside the repository are checked too.
- [ ] Imports, inputs and seeds are verified before the first draw, not only at commit, and on the bytes actually used.

## Replayable controller evidence (NEW-4, NEW-5)
- [ ] Estimator values are checked against the fitter's real bounds, and fit mask, residual set, S1/S2 and finite values against the fit's own outputs. The out-of-grid `p_hat`/`b_hat` probe still passes admission today.
- [ ] The final block's lookahead score is validated.
- [ ] Ordered detector marginals, source windows and library state are saved wherever a claim depends on g, fit or AD3 matching.

## Paired scoring and input-role separation (NEW-5)
- [ ] Detector-only, labelled-calibration and evaluation rows are in separate, role-labelled archives; labels are unreachable by policy and decoders.
- [ ] Row identity and order are common to all arms. An independent scorer can rebuild paired errors.
- [ ] The evidence tier matches the claims frozen. Anything less is stated as conditional on summaries.

## Seed screening and sampler-call provenance
- [ ] The screening list is complete for the study and frozen.
- [ ] Each real sampler call is bound to its stream, seed and row count: durable intent before, returned shape and unique row identity checked before confirmation.
- [ ] A seed cannot be consumed twice. Possible sampling is never retried.

## Whole-run deadlines and resource caps (NEW-6, remaining part)
- [ ] A wall-clock limit for the whole lifecycle, enforced from outside. The current timeout only covers a stall between completions.
- [ ] Memory and disk limits measured in advance, with room for staging and retained failures.
- [ ] Process-tree cleanup by the operating system (for example a Windows job object).
