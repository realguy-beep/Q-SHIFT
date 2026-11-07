"""Prospectively supersede a zero-test pretest freeze after a metadata-only fix."""
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
freeze_path = P / "PRETEST_FREEZE.json"
old = json.loads(freeze_path.read_text(encoding="utf-8"))
assert old["heldout_shots_generated_at_freeze"] == 0
assert not list((P / "data" / "heldout").glob("*.npz")), "cannot supersede after any held-out sample"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


old_bytes_sha = sha(freeze_path)
superseded_path = P / "PRETEST_FREEZE_SUPERSEDED_1.json"
if superseded_path.exists():
    raise RuntimeError("superseded freeze file already exists; refusing to overwrite it")
shutil.copyfile(freeze_path, superseded_path)
assert sha(superseded_path) == old_bytes_sha

# All prior frozen inputs except the corrected runner must still match exactly.
mismatches = []
for rel, expected in old["files_sha256"].items():
    actual = sha(ROOT / rel) if (ROOT / rel).is_file() else None
    if actual != expected:
        mismatches.append((rel, expected, actual))
if [x[0] for x in mismatches] != ["outputs/phase2b_pauli_bias/run_phase2b.py"]:
    raise RuntimeError(f"unexpected pretest input changes: {mismatches}")

files = dict(old["files_sha256"])
runner_rel = "outputs/phase2b_pauli_bias/run_phase2b.py"
files[runner_rel] = sha(ROOT / runner_rel)
for path in [P / "FREEZE_CHANGELOG.md", P / "supersede_pretest_freeze.py", superseded_path]:
    files[path.relative_to(ROOT).as_posix()] = sha(path)
new = dict(old)
new["revision"] = 2
new["created_utc"] = datetime.now(timezone.utc).isoformat()
new["supersedes"] = {"file": "PRETEST_FREEZE_SUPERSEDED_1.json", "sha256": old_bytes_sha,
                     "reason": "Corrected reporting metadata classification before any held-out shots; no scientific protocol or pretest evidence changed."}
new["files_sha256"] = files
new["heldout_shots_generated_at_freeze"] = 0
freeze_path.write_text(json.dumps(new, indent=2) + "\n", encoding="utf-8")
print(f"Active pretest freeze revision 2; preserved revision 1 sha256={old_bytes_sha}; held-out shots=0")
