# Independent seed replication of biased code-capacity MPS screen

## Purpose

Challenge the positive fixed-chi=16 MPS result under X-biased code-capacity noise using a wholly separate NumPy RNG stream. This is a development replication, not confirmatory evaluation.

## Frozen design

Repeat the exact prior configuration: qecsim 1.0b9 `PlanarCode(d,d)`, d=3/5, p=.05, `BiasedDepolarizingErrorModel(bias=5, axis='X')` (10:1:1 X:Y:Z), `PlanarMPSDecoder(chi=16, mode='c')` versus bias-aware `PlanarMWPMDecoder`, identical errors/syndromes per arm, and 5,000 paired samples/distance. Preflight uses 100 samples/distance. Seeds: preflight 2026113321/3322 and main 2026113331/3332. No parameter changes or additional decoder arms.

Report both LERs, paired difference and 95% shot-level interval, discordant outcomes, exact McNemar p, recovery validity, runtime and peak RSS. The replication is directionally consistent only if MPS has fewer failures at both distances. This criterion does not establish independent-root population significance. If consistent, the only next step is a circuit-compatibility feasibility audit under a separately declared, resource-bounded model; it does not authorize circuit integration or a Q-SHIFT performance claim.

## Stop rule and scope

Abort main if either recovery is invalid or the preflight projection exceeds 300 seconds. This remains perfect-syndrome code-capacity evidence. No Q-SHIFT circuit samples, Stage S/sealed data, or confirmatory data are used.
