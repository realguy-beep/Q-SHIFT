"""Deterministic consistency checks for the prospective endpoint review."""
import json
import hashlib
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
data = json.loads((HERE / "POWER_SENSITIVITY.json").read_text(encoding="utf-8"))
assert data["status"].startswith("prospective design calculations only")
assert data["current_candidate_allocation"]["total_shots"] == 2_250_000
assert data["current_candidate_allocation"]["maximum_roots_per_stratum_under_cap"] == 111
assert data["current_candidate_allocation"]["max_allocation_shots"] == 2_497_500
assert math.isclose(data["endpoint_A"]["power_one_sided"], 0.9286760550690758, abs_tol=1e-12)
assert math.isclose(data["endpoint_A"]["power_two_sided_alpha_0_05_sensitivity"], 0.8751116781343911, abs_tol=1e-12)
b = data["endpoint_B"]["power_at_current_100_roots"]
assert [round(x["power_one_sided_alpha_0_05"], 6) for x in b] == [0.464372, 0.928676, 0.998742]
by_gap_q_power = {(x["gap_beyond_margin"], x["sd_inflation_factor"]): x["power_one_sided_alpha_0_05"] for x in data["endpoint_B"]["heterogeneity_sensitivity_at_current_100_roots"]}
assert by_gap_q_power[(0.0001, 1.5)] < by_gap_q_power[(0.0001, 1.0)]
requirements = data["endpoint_B"]["roots_and_shots_for_planning_gaps"]
lookup = {(x["gap_beyond_margin"], x["sd_inflation_factor"], x["target_power"]): x for x in requirements}
assert lookup[(0.0001, 1.0, 0.8)]["roots_per_stratum"] == 256
assert lookup[(0.0001, 1.0, 0.9)]["roots_per_stratum"] == 354
assert lookup[(0.0002, 1.5, 0.8)]["roots_per_stratum"] == 144
assert lookup[(0.0002, 2.0, 0.8)]["roots_per_stratum"] == 256
assert data["endpoint_A"]["probability_point_estimate_at_or_below_minus_0_0002_when_true_effect_is_exactly_minus_0_0002"] == 0.5
manifest_path = HERE / "REVIEW_MANIFEST.json"
if manifest_path.exists():
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for entry in manifest["files"]:
        path = HERE.parents[1] / Path(entry["path"])
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == entry["sha256"], f"Hash mismatch: {entry['path']}"
    assert manifest["stage5_sampling_performed"] is False
    assert manifest["sealed_test_accessed"] is False
print("PASS: endpoint power, heterogeneity and shot-allocation calculations are internally consistent")
