"""CF1 confirmatory run of W0F (PLAN_CF1.md).

  python cf1_run.py fidelity                          # DB4 dev AA_e3 and BA_e0 re-run: every block equals DB4's record
  python cf1_run.py freeze                            # CF1_FREEZE.json (needs fidelity pass and CF1_SEEDS.json)
  python cf1_run.py run --expected-head <sha> [--workers 8]   # the single confirmatory attempt (needs authorization)

The per-block loop is DB4's episode_job, imported (not copied). The only CF1 addition is the "cf1" seed mode.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from multiprocessing import get_context
from pathlib import Path

import numpy as np

import cf1_config as C  # noqa: I001  (puts DB4, DB3, DB2, DB1 and AD2/AD3 on sys.path first)
import db4_run as R4  # noqa: E402
import studykit as SK  # noqa: E402

WORK = C.ROOT / "work"
FREEZE = C.ROOT / "CF1_FREEZE.json"
FID_EPISODES = (("AA", 3), ("BA", 0))          # the two DB4 dev episodes where W0F and W0 took different keys
JOB_IMPORTS = ("ad2", "ad3", "db_core", "mm_contract", "re1", "outputs.qshift_correlated_decoder_v1_4.model_v14")

_db4_setup = R4._setup


def _setup(mode, s, e):
    """DB4's _setup, plus mode "cf1": CF1_SEEDS.json, DB4's generators unchanged."""
    if mode != "cf1":
        return _db4_setup(mode, s, e)
    sd = json.loads((C.ROOT / "CF1_SEEDS.json").read_text(encoding="utf-8"))["seeds"]
    prm = C.C4.episode_params(s, e, int(sd[f"cf1:params:{s}:e{e}"]))
    return (lambda t: C.C4.block_state(s, t, prm)), (lambda t, p: int(sd[C.block_key(s, e, t, p)])), \
        C.EVAL_PER_BLOCK, prm, C.C4.changes(s, prm)


R4._setup = _setup                              # module import also patches spawned workers (job lives here)


def job(args):
    return R4.episode_job(args)


# ------------------------------------------------------------------ fidelity
def cmd_fidelity():
    run = WORK / "fidelity"
    (run / "records").mkdir(parents=True, exist_ok=False)
    ref_dir, arc_dir = C.DB4 / "results" / "dev" / "records", C.DB4 / "work" / "dev"
    js = [("dev", s, e, str(run)) for s, e in FID_EPISODES]
    with get_context("spawn").Pool(len(js)) as pool:
        pool.map(job, js)
    res = {"episodes": {}}
    for s, e in FID_EPISODES:
        mine = json.loads((run / "records" / f"{s}_e{e}.json").read_text(encoding="utf-8"))
        ref = json.loads((ref_dir / f"{s}_e{e}.json").read_text(encoding="utf-8"))
        z0, z1 = np.load(arc_dir / ref["archive"]), np.load(run / mine["archive"])
        bits = all(np.array_equal(z0[k], z1[k]) for k in z0.files) and set(z0.files) == set(z1.files)
        d = {f: mine[f] == ref[f] for f in ("params", "states", "true_changes", "seeds", "changes_detected", "g",
                                             "arms", "blocks")}
        d["bits"] = bool(bits)
        d["W0F_ne_W0_blocks"] = [b["block"] for b in mine["blocks"] if b["keys"]["W0F"] != b["keys"]["W0"]]
        d["pass"] = all(v for k, v in d.items() if k != "W0F_ne_W0_blocks") and bool(d["W0F_ne_W0_blocks"])
        res["episodes"][f"DB4 dev {s}_e{e}"] = d
    res["all_pass"] = all(v["pass"] for v in res["episodes"].values())
    SK.write_once_json(C.ROOT / "FIDELITY.json", res)
    print(json.dumps(res, indent=1))


# ------------------------------------------------------------------ freeze
def freeze_files():
    """Every .py in DB1-DB5 (tests included), every repo module the episode job imports, and the data inputs."""
    import importlib
    for m in JOB_IMPORTS:
        importlib.import_module(m)
    import cf1_analyze  # noqa: F401
    repo = SK.REPO.resolve()
    fs = set()
    for d in [C.ROOT.parent / f"qshift_decoder_bank_v{i}" for i in range(1, 6)]:
        fs |= {p.resolve() for p in d.rglob("*.py") if "work" not in p.relative_to(d).parts}
    for mod in list(sys.modules.values()):
        f = getattr(mod, "__file__", None)
        if f and f.endswith(".py") and Path(f).resolve().is_relative_to(repo):
            fs.add(Path(f).resolve())
    fs |= {(C.DB1 / "TRAINING.json").resolve()}
    fs |= {(C.ROOT / n).resolve() for n in ("CF1_SEEDS.json", "PLAN_CF1.md", "FIDELITY.json")}
    return sorted(p.relative_to(repo).as_posix() for p in fs)


def cmd_freeze():
    if not json.loads((C.ROOT / "FIDELITY.json").read_text(encoding="utf-8"))["all_pass"]:
        raise SystemExit("fidelity did not pass")
    files = freeze_files()
    hashes = SK.freeze_hashes(files)
    doc = {"schema": "qshift-decoder-bank-cf1-freeze-v1", "study": "CF1", "branch": "claude/qshift-decoder-bank-v5",
           "rule": {"arm": C.TEST_ARM, "gate": list(C.C4.CANDIDATES[C.TEST_ARM]), "fallback_static_key": "A"},
           "episodes": C.EPISODES, "hypotheses": [list(h[:3]) + [list(h[3]), h[4]] for h in C.HYPOTHESES],
           "alpha": C.ALPHA, "multiplicity": "Holm-Bonferroni over H1-H4",
           "n_flips": C.N_FLIPS, "exact_max_n": C.EXACT_MAX_N, "n_boot": C.N_BOOT,
           "perm_seed": C.PERM_SEED, "boot_seed": C.BOOT_SEED,
           "files": hashes, "file_count": len(hashes), "code_head": SK.git_head(),
           "non_circular_binding": "Excludes its own digest and the commit SHA; the run requires --expected-head = "
                                   "the commit containing this file, a clean tree, and every hash above.",
           "sampling_authorization": "None. The owner must separately authorize 'run CF1' on this commit.",
           "study_samples_before_freeze": 0}
    SK.write_once_json(FREEZE, doc)
    print(len(hashes), "files frozen")


# ------------------------------------------------------------------ the confirmatory run
def cmd_run(expected_head, workers):
    SK.require_frozen_head(FREEZE, expected_head)
    if not json.loads((C.ROOT / "FIDELITY.json").read_text(encoding="utf-8"))["all_pass"]:
        raise SystemExit("fidelity did not pass")
    run = WORK / "cf1"
    st = run / "RUN_STATUS.json"
    if st.exists():
        raise SystemExit("RUN_STATUS.json exists; single attempt only")
    (run / "records").mkdir(parents=True, exist_ok=True)
    js = [("cf1", s, e, str(run)) for s in C.SCHEDULES for e in range(C.EPISODES[s])]
    js.sort(key=lambda j: j[1] in C.NULL_SCHED)          # dynamic panels first
    status = {"head": SK.git_head(), "workers": workers, "state": "running", "reruns": {},
              "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "jobs": {}}
    SK.dump_json(st, status)
    t0 = time.perf_counter()
    try:
        failed = []
        with get_context("spawn").Pool(workers) as pool:
            hs = [(j, pool.apply_async(job, (j,))) for j in js]
            for i, (j, h) in enumerate(hs, 1):
                nm = f"{j[1]}_e{j[2]}"
                try:
                    h.get(timeout=20_000)
                    status["jobs"][nm] = {"returncode": 0}
                except Exception as ex:      # noqa: BLE001  (infrastructure failure: one re-run, same seeds)
                    failed.append(j)
                    status["reruns"][nm] = {"first_error": repr(ex)}
                print(nm, f"{i}/{len(js)}", f"{time.perf_counter() - t0:.0f}s", flush=True)
                SK.dump_json(st, status)
        for j in failed:                     # PLAN_CF1.md section 5: logged as a deviation
            nm = f"{j[1]}_e{j[2]}"
            out = run / "records" / f"{nm}.json"
            if out.exists():
                raise SystemExit(f"{nm} failed after writing its record; CF1 stops")
            with get_context("spawn").Pool(1) as pool:
                pool.apply(job, (j,))
            status["jobs"][nm] = {"returncode": 0, "rerun": True}
        status["state"] = "ready_for_analysis"
    except BaseException as ex:      # noqa: BLE001
        status["state"], status["error"] = "failed", repr(ex)
        raise
    finally:
        status.update(finished=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                      wall_seconds=round(time.perf_counter() - t0, 1), n_jobs=len(js))
        SK.dump_json(st, status)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["fidelity", "freeze", "run"])
    ap.add_argument("--expected-head")
    ap.add_argument("--workers", type=int, default=8)
    x = ap.parse_args()
    if x.cmd == "fidelity":
        cmd_fidelity()
    elif x.cmd == "freeze":
        cmd_freeze()
    else:
        if not x.expected_head:
            raise SystemExit("--expected-head is required")
        cmd_run(x.expected_head, x.workers)
