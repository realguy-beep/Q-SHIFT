# Preserved third independent-audit failure

The independent v3 process completed its full reference and validation replay but then raised `KeyError: 'scenario'` while matching marginal results. The candidate simulator's frozen serializer records 192 marginal rows in deterministic scenario → condition → Holm-threshold order but does not repeat the scenario string on each row. The audit incorrectly expected a scenario field.

`audit_secondary_v4.py` keeps the same independent seeded computation and now checks the saved rows by that frozen order plus condition, threshold and rejection count. This is a comparison-schema correction only. The full v4 replay must finish and match the counts before a GO decision.
