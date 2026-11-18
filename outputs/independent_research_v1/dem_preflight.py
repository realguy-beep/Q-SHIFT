"""Check whether Phase 2B categorical circuits admit non-approximate DEMs."""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PHASE2B = REPO / "outputs" / "phase2b_pauli_bias"
sys.path.insert(0, str(PHASE2B))

from noise_model import MEMORY_BASES, REGIMES, build_circuit  # noqa: E402


def main() -> int:
    outcomes = []
    for basis in MEMORY_BASES:
        for regime in REGIMES:
            circuit = build_circuit(basis, regime)
            try:
                circuit.detector_error_model(
                    decompose_errors=True,
                    approximate_disjoint_errors=False,
                )
            except ValueError as exc:
                expected = "PAULI_CHANNEL_2" in str(exc) and "approximate_disjoint_errors" in str(exc)
                outcomes.append((basis, regime, "blocked-as-expected" if expected else "unexpected-error"))
                print(f"{basis} {regime}: {outcomes[-1][2]}: {exc}")
            else:
                outcomes.append((basis, regime, "converted"))
                print(f"{basis} {regime}: converted")
    expected_count = sum(result == "blocked-as-expected" for _, _, result in outcomes)
    if len(outcomes) != 6 or expected_count != 6:
        print(f"Preflight outcome needs review: {expected_count}/6 expected conversion blockers")
        return 1
    print("All six conditions require approximate_disjoint_errors=True.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
