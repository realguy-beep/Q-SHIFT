# V2.4 runtime provenance and audit compatibility

V2.4 retains V2.3's approval-bound execution identity and exact approval receipt. It adds a status gate before provenance handling. Rejected terminal, malformed, unknown, expired, inconsistent, or complete-progress states are read-only failures. Valid resumes require a pre-existing matching identity and receipt; the resume path has no create/repair behavior. Fresh runs create provenance exclusively before dispatch.

The auditor adapter verifies the execution identity/receipt and V2.4→V2.3→V2.2→V2.1 freeze chain, then delegates metric reconstruction to the unchanged V2 saved-array auditor. Fixture tests verify this integration without real run arrays. No independent replay of a real V2 run is possible because no V2 sampling has occurred. Runtime dependency versions remain recorded and hash-bound by the approval as in V2.3; no software is installed by these scripts.

Residual limitations: owner approval is an editable procedural JSON record rather than a digital signature; recorded historical seed coverage is incomplete; no real run or real-array audit has been conducted; and the development study does not establish confirmatory statistical superiority.
