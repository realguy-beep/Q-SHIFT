"""Read-only check: fixed analyzer vs saved V1.1 attempt_001, on a scratch copy."""
import hashlib, json, shutil, sys
from pathlib import Path

fix_repo, orig_run, scratch = map(Path, sys.argv[1:4])
sys.path.insert(0, str(fix_repo))
from outputs.qshift_correlated_decoder_v1_1_analyzer_fix_v1.analyze_saved_fixed import analyze


def tree_hash(root: Path) -> dict:
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file()}


before = tree_hash(orig_run)
copy = scratch / "attempt_001_copy"
out = scratch / "fixed_analysis_out"
for d in (copy, out):
    if d.exists():
        shutil.rmtree(d)
shutil.copytree(orig_run, copy)
status = json.loads((copy / "status.json").read_text(encoding="utf-8"))
print("original status:", status["state"], "/", status.get("phase"))
# Only in the scratch copy: restore the pre-analysis state the frozen analyzer expects.
status["state"] = "evaluation_complete_pending_independent_analysis"
(copy / "status.json").write_text(json.dumps(status), encoding="utf-8")

r = analyze(copy, out)
after = tree_hash(orig_run)
print("original run unchanged:", before == after, f"({len(before)} files)")

csv_same = (out / "paired_results.csv").read_bytes() == (orig_run / "paired_results.csv").read_bytes()
print("paired_results.csv byte-identical to frozen pre-failure CSV:", csv_same)

audit = json.loads((fix_repo / "outputs/qshift_correlated_decoder_feasibility_v1_1/postrun_audit_v1/recovered_outputs/independent_audit.json").read_text(encoding="utf-8"))
print("decision:", r["decision"])
print("primary:", r["primary_estimand_B_minus_A_equal_weight_q0_01_q0_02"], r["primary_two_sided_95_percentile_ci"])
print("q0 5/95:", r["q0_B_minus_A_bootstrap_5th_95th_percentiles"])
print("arm errors:", {a: v["errors"] for a, v in r["arm_totals"].items()})
print("A_global_qhat:", r["A_global_qhat"], "audit:", audit.get("global_A_qhat"))
print("audit keys:", sorted(audit)[:40])
