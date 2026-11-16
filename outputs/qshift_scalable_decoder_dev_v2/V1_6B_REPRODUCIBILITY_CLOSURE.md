# V1.6b reproducibility closure (record review only)

## Scope

This note consolidates the already committed replay and calibration reports for
handoff. It does not reopen or recompute evaluation outcomes, and it does not
close the remaining provenance gaps. This V2 task did not load saved detector
or observable arrays from V1.6b.

## Verified from the existing records

- `outputs/qshift_v1_6b_replay_verification_v1/REPLAY_REPORT.md` reports a
  preregistered replay of 900 saved detector rows across 18 archives and six
  decoder arms. It reports 5,400 prediction bits compared with zero
  disagreements, after verifying 38 frozen source/configuration identities
  and 300 archive hash/size records. The report states that archived
  predictions were loaded only after replay predictions and that no evaluation
  observables were loaded.
- `outputs/qshift_v1_6b_calibration_reconstruction_v1/REPORT.md` reports 340
  calibration comparisons with no mismatch at the documented tolerances,
  covering 144 roots. It describes independently reconstructed arithmetic,
  but shares the frozen class signatures, circuit builder, base DEM and exact
  decoder; it is not an independent decoder implementation.
- The replay is same-implementation deterministic reproduction, not an
  independent algorithm. The full 576,000-shot prediction archive has not
  been replayed. A full replay is therefore not verified here.

## Metadata provenance limitation

The calibration report supplies hashes of current `device_learning.json` and
`models_frozen.json` bytes:

| Condition | Device metadata SHA-256 | Model metadata SHA-256 |
|---|---|---|
| Known | `848173f0ee9e1701147c18c6ebb8fa973836c7e116c27d6a6232f27985cc0c7c` | `ceeeffcf12cd0af0a7c6658525f8df07a2d696c2a940388e5bc7fdef5eead03c` |
| Hidden | `b9e7dd78353f70d82e4f87f17559bc715e69b309f41fe6a39634b7bc9d9683bb` | `a7a7cb732fa640e3b1de15ca7c763054fe9f451cd240de8a2e5217d7b1d58bd0` |

Those files were not separately listed in the original archive manifest. A
hash calculated later on current bytes cannot establish that the same bytes
were used historically. The reports also identify the missing independent
decoder replay as an open gap. No claim here upgrades V1.6b from development
evidence to independent confirmation.

## Assessment

The existing evidence supports reproducibility of the preregistered 900-row
subset under the frozen implementation and reconstruction of the recorded
calibration arithmetic. It does not establish full-run prediction replay,
historical binding of the model/device metadata, or independent decoder
implementation agreement. Any larger replay requires separate authorization,
an explicit output location that preserves current evidence, and adequate
process-tree deadline supervision. This V2 work performed none of those
actions.
