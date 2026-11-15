# V2 seed-collision audit — metadata-only, no sampling

**Disposition:** no collision found among the recorded and recoverable metadata screened. Historical coverage remains explicitly incomplete for undocumented RNG use. This is a prospective seed allocation, not evidence of a run.

## Reproducible input scope

The builder reads the exact 25 source records named in the preserved `outputs/stage5_secondary_inference_repair_v1/STAGE5_SAMPLE_SEED_INVENTORY.json` allowlist. It verified each allowlisted file's byte-level SHA-256 against that inventory using the prior Q-SHIFT workspace at `C:/Users/LENOVO/Documents/Codex/2026-11-03/referenced-chatgpt-conversation-this-is-an`. It also screened 48 additional tracked JSON/CSV files whose names identify seed inventories, seed audits, or seed manifests in the current research checkout. The generated `seed_inventory_v2_r2.json` records every relative path, observed SHA-256, source class, and metadata count. The earlier `seed_inventory_v2.json` candidate is preserved as a no-sample preparation record and excluded from historical collision inputs because it was never executed.

The scanner conservatively collects large integer tokens (including possible non-seed counters) from those allowlisted metadata files. It does not open NPZ/NPY archives, training/evaluation arrays, predictions, checkpoints, or Stage 5 outcome files. No simulator or decoder was run by inventory preparation. The 25 source records and current tracked metadata are available for independent review in the machine-readable inventory.

## Results

- Historical allowlisted files verified: **25/25**.
- Additional tracked seed/manifest metadata files screened: **48**.
- Large integer tokens screened (conservative superset, not a count of RNG seeds): **29,128**.
- Proposed V2 streams: **1,610**; unique candidate seeds: **1,610**.
- Candidate-internal collisions: **0**; historical metadata collisions: **0**.
- Planned sample allocation represented by included streams: **3,660,000 shots**, matching the V2 configuration.
- Candidate namespace starts at `19,000,000,001`; its exact ending value and each prospective stream mapping are recorded in `seed_inventory_v2_r2.json`.
- `sampling_performed=false`; `sealed_test_access=false`; `historical_coverage_complete=false`.
- Preserved Stage 5 seed-metadata inventory SHA-256: `49fa7027c29cc1877eb88a590b72790d08f7dc95e187003acbb65f633dbea2a9`. Final candidate inventory SHA-256: `9f38d03d3315bf74e33e2a994446bc1e103b9e08827d8b1cc8553516fbdc72c7`. Preserved superseded no-sample candidate inventory SHA-256: `c23e451f9d4fe835c163c81cee247cbd126069447629cfda41bfab5fe5fd7374`.

## Interpretation and limit

This establishes disjointness from every recorded integer token in the verified metadata scope, not from RNG use that was never recorded or from inaccessible historical material. The Stage 5 source inventory itself documents incomplete historical coverage. This report therefore does not claim exhaustive historical seed uniqueness. It is a collision screen using seed/allocation metadata only; it is not an evaluation-data audit and makes no scientific performance claim.

During preparation, two preliminary no-sample candidate inventory writes were superseded before the create-only safeguard was added; their console-reported hashes were `691d0492b3ede391700977248445c33feeebe3c7ce085341023e33105f767de0` and `42f72cadaf49957d636113f3185829763e77d9330ef873140048e10bf811443f`. Their bytes were not retained and are not treated as frozen inventories. The `c23e...` candidate is preserved; the final freeze uses only `seed_inventory_v2_r2.json`. No samples were generated from any of these candidate inventories.
