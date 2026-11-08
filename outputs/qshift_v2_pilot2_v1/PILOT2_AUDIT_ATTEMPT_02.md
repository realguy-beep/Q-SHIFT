# Independent audit attempt 2 (preserved)

The second independent-audit pass completed the seed, chronology, flags, pairing, denominator, and bootstrap checks, but reported a false failure for the LER/denominator comparison. The lookup key used the string `"False"` where the parsed results map used Boolean `False`, so metric rows were not found. The failed audit JSON is preserved as `PILOT2_AUDIT_ATTEMPT_02.json`.

Correction: the independent audit now uses the Boolean decoder-mode key. All Pilot 2 outcomes and result files remain unchanged; no new shots were generated or Stage 5/sealed material accessed.
