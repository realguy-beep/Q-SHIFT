# Fusion Blossom d3 graph interface and decoder screen

## Question

Can Fusion Blossom's custom-graph Python interface reproduce ordinary PyMatching MWPM predictions from the same Stim detector model, and does a serial Python integration offer a throughput advantage on a small fixed screen?

## Frozen screen

Use CSS and native-XCX XZZX, each in X and Z memory, at d3 / 5 rounds, X-bias 10:1 and p=.003, matching the existing d3 balanced-basis circuit family. Run 250 fresh detector samples per cell at seeds 2026115201–2026115204 (1,000 total). Build both decoders from the same decomposed Stim DEM with PyMatching correlations disabled. Export PyMatching's merged graph, preserve each edge's fault IDs, map its boundary nodes as Fusion Blossom virtual vertices, and scale log-odds to nearest even integer with scale 1e6 (Fusion Blossom rejects odd edge weights). Fusion Blossom's returned subgraph selects graph edges; reconstruct its logical prediction by XORing selected edge fault IDs.

## Stop rules and scope

Stop on any graph construction failure, invalid syndrome, or nonzero prediction mismatch. Save graph vertex/edge counts, conversion and per-shot decode times, total wall time, and peak RSS. This is only a d3 API/decision-equivalence feasibility screen; do not infer large-distance scaling, correlated-decoding equivalence, or production speed from it. No follow-on sample run is planned from this screen.
