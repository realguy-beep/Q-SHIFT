# DEM approximation and what the pilot can identify

## What was sampled and what was decoded

Stim samples the saved Phase 2B circuit's categorical one- and two-qubit Pauli channels. A gate event draws one outcome from mutually exclusive alternatives; for two-qubit gates the 15 non-identity Pauli-pair alternatives have probabilities summing to the configured total 0.003. Measurement flips are separately injected with probability 0.003.

The matching model is derived using `decompose_errors=True` and `approximate_disjoint_errors=True`. The latter permits Stim to approximate disjoint alternatives in the categorical error model as separate mechanisms. The approximation affects the detector error model (DEM), not the stored Stim detector/observable samples. Both members of each off/on comparison are constructed from the same already-converted DEM.

## Direct audit of saved DEM metadata

| Memory basis | Regime | Error records | Records containing `^` | Separator count | Separator records containing `L0` |
|---|---|---:|---:|---:|---:|
| X | X-biased / balanced / Z-biased | 578 each | 436 each | 564 each | 121 each |
| Z | X-biased / balanced / Z-biased | 586 each | 444 each | 572 each | 118 each |

The decomposition topology/counts are invariant across the three Pauli regimes within a memory basis; the DEM probability parameters differ with the configured Pauli weights. These counts alone therefore do not explain why the effect direction changes across conditions. A separator count does not reveal which correlation groups are relevant to a particular sampled syndrome.

The pilot preflight independently verified that for a fixed model, the correlation-disabled and correlation-enabled PyMatching objects preserve the same graph edges, edge weights, detector IDs, and logical fault IDs. Enabling correlations changed the decode path/output for 1,343 paired test shots. The flag did not change DEM construction or add new physical noise information.

## Why attribution is unavailable

Saved raw bundles contain packed detector samples, observable labels, four predicted logical bits, and root metadata. They do not include latent gate-level Pauli outcomes, matching edges/paths, the correlation group selected during decoding, or per-shot posterior likelihoods. Since Stim sampling does not save which categorical branch fired at each location in these bundles, the physical fault history cannot be recovered from syndrome and logical label alone.

Thus the audit can conclude that enabling correlation-aware decoding on the approximate DEM changed a sparse set of predictions and that those changes had different net utility by condition. It cannot identify a named DEM separator, particular two-qubit Pauli fault, or exact logical chain as the cause.

## What remains uncertain

1. Whether the harmful two conditions persist when disjoint categorical alternatives are represented without the current approximation.
2. Whether PyMatching's correlation-enabled procedure is suboptimal for those syndromes even under a faithful DEM.
3. Whether the effect is specific to distance 3/five rounds.
4. Whether underlying axis-dependent noise, stabilizer geometry, and temporal boundary structure jointly create the observed pattern.

A follow-up should not label a `approximate_disjoint_errors=False` DEM “exact” until its conversion succeeds and its detector/observable semantics and channel treatment are independently checked. See the strict preflight and stop rule in `FOLLOWUP_PROTOCOL.md`.
