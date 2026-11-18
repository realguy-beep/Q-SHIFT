# Independent replication: d5 CSS/XZZX basis workload

## Purpose and status

This is a fresh-seed development replication of the d5 four-cell code/memory screen. It challenges two observations from the initial 2x2 stream: (1) XZZX had lower LER than CSS on an equal-weight average of separate X- and Z-memory tasks, and (2) CSS-X strongly outperformed XZZX-X for known X-memory workloads. The equal-weight endpoint is now fixed before this independent stream; it was post hoc in the discovery stream and is not confirmatory evidence.

## Fixed design

Use the same d5/9-round X-biased ratio-10, gate/measurement p=.003 conditions and circuit constructors as the first screen: CSS-X, CSS-Z, native-XCX XZZX-X, native-XCX XZZX-Z. Run 10,000 shots/cell preflight using seeds 2026114201–2026114204, then 500,000 independent shots/cell using seeds 2026114211–2026114214. Require the same equal-resource, channel-vector, noiseless, DEM, and scalar/batch decoder checks as the original protocol; stop if projected main runtime exceeds 300 seconds.

## Endpoints

Primary: equal-weight separate-memory task average, calculated as the pooled X and Z failure rates per code (each basis has equal shots). Compare XZZX/CSS with the exact conditional independent-rate-ratio interval. Secondary: XZZX-X/CSS-X rate ratio and XZZX-Z/CSS-Z rate ratio; report basis-specific intervals, all four LERs, Wilson intervals, resources, and runtime. Do not call the equally weighted separate-memory workload an arbitrary-state logical channel. The streams are independent, not paired.

Maintain the explicit assumption that native CX, XCX, and CZ have equal duration and identical `PAULI_CHANNEL_2` distributions; this is not hardware-calibrated. No sealed or confirmatory evaluation data are accessed.
