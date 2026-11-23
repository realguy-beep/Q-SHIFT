"""CF2 confirmatory run of LA_W0F (PLAN_CF2.md).

  python cf2_run.py fidelity                                   # DB6 dev BB_e0, U_e0 re-run: every field and bit = DB6's
  python cf2_run.py freeze                                     # CF2_FREEZE.json (portable; needs fidelity + seeds)
  python cf2_run.py run --expected-head <sha> [--workers 8]    # the single confirmatory attempt (separate approval)

The per-block loop is DB6's episode_job, imported (not copied). The only CF2 addition is the "cf2" seed mode.
"""
from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from multiprocessing import get_context
from pathlib import Path

import numpy as np

import cf2_config as C  # noqa: I001  (puts DB6, DB5, DB4, DB3, DB2, DB1 and AD2/AD3 on sys.path first)
import db6_run as R6  # noqa: E402
import studykit as SK  # noqa: E402

WORK = C.ROOT / "work"
FREEZE = C.ROOT / "CF2_FREEZE.json"
FID_EPISODES = (("BB", 0), ("U", 0))    # the largest DB6 LA gain, and the out-of-bank panel where LA2 harmed
INFRA = R6.INFRA                         # (OSError, MemoryError, EOFError, ConnectionError, MPTimeout)
_norm_sha, _blob, TEXT, SEAL_MARKERS = R6._norm_sha, R6._blob, R6.TEXT, R6.SEAL_MARKERS
NOT_COMPARED = ("timing", "seconds", "archive_sha256")   # wall-clock fields; npz bytes carry zip timestamps

_db6_setup = R6._setup


def _setup(mode, s, e):
    """DB6's _setup, plus mode "cf2": CF2_SEEDS.json, DB6's generators unchanged."""
    if mode != "cf2":
        return _db6_setup(mode, s, e)
    sd = json.loads((C.ROOT / "CF2_SEEDS.json").read_text(encoding="utf-8"))["seeds"]
    prm = C.episode_params(s, e, int(sd[f"cf2:params:{s}:e{e}"]))
    return (lambda t: C.block_state(s, t, prm)), (lambda t, p: int(sd[C.block_key(s, e, t, p)])), \
        C.EVAL_PER_BLOCK, prm, C.changes(s, prm)


R6._setup = _setup                       # module import also patches spawned workers (job lives here)
R6.WORK = WORK                           # traced_job excludes this package's work/ from the traced inputs


def job(args):
    return R6.episode_job(args)


def traced(args):
    return R6.traced_job(args)


# ------------------------------------------------------------------ fidelity
def cmd_fidelity():
    run = WORK / "fidelity"
    (run / "records").mkdir(parents=True, exist_ok=False)
    ref_dir, arc_dir = C.DB6 / "results" / "dev" / "records", C.DB6 / "work" / "dev"
    js = [("dev", s, e, str(run)) for s, e in FID_EPISODES]
    with get_context("spawn").Pool(len(js)) as pool:
        tr = pool.map(traced, js)
    res, inputs = {"episodes": {}}, set()
    for (s, e), (_, files) in zip(FID_EPISODES, tr):
        inputs |= set(files)
        mine = json.loads((run / "records" / f"{s}_e{e}.json").read_text(encoding="utf-8"))
        ref = json.loads((ref_dir / f"{s}_e{e}.json").read_text(encoding="utf-8"))
        z0, z1 = np.load(arc_dir / ref["archive"]), np.load(run / mine["archive"])
        d = {f: mine[f] == ref[f] for f in sorted(set(ref) | set(mine)) if f not in NOT_COMPARED}
        d["bits"] = set(z0.files) == set(z1.files) and all(np.array_equal(z0[k], z1[k]) for k in z0.files)
        d["la_uses"] = sum(b["source"]["LA_W0F"] == "lookahead" for b in mine["blocks"])
        d["pass"] = all(v for k, v in d.items() if k != "la_uses") and d["la_uses"] > 0
        res["episodes"][f"DB6 dev {s}_e{e}"] = {k: (bool(v) if k != "la_uses" else v) for k, v in d.items()}
    res["compared"] = "every record field except " + ", ".join(NOT_COMPARED) + "; every archive array bit for bit"
    res["traced_inputs"] = sorted(inputs)
    res["all_pass"] = all(v["pass"] for v in res["episodes"].values())
    SK.write_once_json(C.ROOT / "FIDELITY.json", res)
    print(json.dumps({k: v for k, v in res.items() if k != "traced_inputs"}, indent=1), len(inputs), "inputs traced")


# ------------------------------------------------------------------ portable freeze
def freeze_files():
    import subprocess
    fid = json.loads((C.ROOT / "FIDELITY.json").read_text(encoding="utf-8"))
    ls = subprocess.run(["git", "ls-files"] + [f"outputs/qshift_decoder_bank_v{i}" for i in range(1, 8)],
                        cwd=SK.REPO, capture_output=True, text=True, check=True).stdout.split()
    fs = {f for f in ls if f.endswith(".py")} | set(fid["traced_inputs"])
    fs = {f for f in fs if "/work/" not in f and "__pycache__" not in f and not f.endswith(".pyc")}
    fs |= {f"outputs/qshift_adaptive_robust_v1/{n}_BURSTS.json" for n in ("BRE", "BRS", "BRT")}   # config-named assets
    fs |= {f"outputs/qshift_decoder_bank_v7/{n}" for n in ("CF2_SEEDS.json", "PLAN_CF2.md", "FIDELITY.json")}
    bad = [f for f in fs if any(m in Path(f).name for m in SEAL_MARKERS)]
    if bad:
        raise SystemExit(f"sealed-looking inputs: {bad}")
    return sorted(fs)


def check_freeze(fz):
    """-> files whose working copy or committed HEAD blob (both LF-normalized) differ from the freeze."""
    out = []
    for rel, h in fz["files"].items():
        p = SK.REPO / rel
        if not p.is_file() or _norm_sha(rel, p.read_bytes()) != h or _norm_sha(rel, _blob(rel)) != h:
            out.append(rel)
    return out


def environment():
    import pymatching
    import stim
    return {"python": platform.python_version(), "numpy": np.__version__, "stim": stim.__version__,
            "pymatching": pymatching.__version__, "platform": platform.platform()}


def cmd_freeze():
    if not json.loads((C.ROOT / "FIDELITY.json").read_text(encoding="utf-8"))["all_pass"]:
        raise SystemExit("fidelity did not pass")
    if not SK.tree_clean():
        raise SystemExit("commit FIDELITY.json first")
    hashes = {}
    for rel in freeze_files():
        w, b = _norm_sha(rel, (SK.REPO / rel).read_bytes()), _norm_sha(rel, _blob(rel))
        if w != b:
            raise SystemExit(f"working copy differs from HEAD: {rel}")
        hashes[rel] = b
    dec = {k: getattr(C, k) for k in ("ALPHA", "C1_MEAN", "G1_EPISODE_CAP", "G2_BLOCK_CAP", "G3_HARM_MAX",
                                      "G4_WRONG_CP_MAX", "G5_RX_EPISODE_CAP", "G6_U_EPISODE_CAP",
                                      "BOOT_RESAMPLES", "BOOT_SEED")}
    dec["hypotheses"] = [[n, c, list(p)] for n, c, p in C.HYPOTHESES]
    doc = {"schema": "qshift-decoder-bank-cf2-freeze-v1", "study": "CF2", "files": hashes,
           "file_count": len(hashes), "code_head": SK.git_head(), "environment": environment(),
           "hash_rule": "sha256 of the committed blob with CRLF->LF for text suffixes " + ",".join(sorted(TEXT)),
           "inputs": "tracked .py in decoder_bank v1-v7, every repo file the fidelity jobs opened or imported "
                     "(audit hook), the burst assets, CF2_SEEDS.json, PLAN_CF2.md, FIDELITY.json",
           "non_circular_binding": "Excludes its own digest; the run requires --expected-head = the commit containing "
                                   "this file, a clean tree, and every hash above on both the working copy and HEAD.",
           "decision": dec, "episodes": C.EPISODES, "study_samples_before_freeze": 0}
    SK.write_once_json(FREEZE, doc)
    print(len(hashes), "files frozen")


# ------------------------------------------------------------------ the confirmatory run (separate approval)
def cmd_run(expected_head, workers):
    if SK.git_head() != expected_head:
        raise SystemExit(f"HEAD {SK.git_head()} != expected {expected_head}")
    if not SK.tree_clean():
        raise SystemExit("working tree not clean")
    if not FREEZE.exists():
        raise SystemExit("no CF2_FREEZE.json")
    fz = json.loads(FREEZE.read_text(encoding="utf-8"))
    bad = check_freeze(fz)
    if bad:
        raise SystemExit(f"frozen files changed: {bad}")
    if not json.loads((C.ROOT / "FIDELITY.json").read_text(encoding="utf-8"))["all_pass"]:
        raise SystemExit("fidelity did not pass")
    run = WORK / "cf2"
    st = run / "RUN_STATUS.json"
    if st.exists():
        raise SystemExit("RUN_STATUS.json exists; single attempt only")
    (run / "records").mkdir(parents=True, exist_ok=True)
    js = [("cf2", s, e, str(run)) for s in C.SCHEDULES for e in range(C.EPISODES[s])]
    js.sort(key=lambda j: j[1] in C.NULL_SCHED)
    status = {"head": SK.git_head(), "workers": workers, "state": "running", "reruns": {},
              "environment": environment(),
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
                except INFRA as ex:                       # infrastructure: one re-run with the same seeds
                    failed.append(j)
                    status["reruns"][nm] = {"first_error": repr(ex)}
                print(nm, f"{i}/{len(js)}", f"{time.perf_counter() - t0:.0f}s", flush=True)
                SK.dump_json(st, status)
        for j in failed:
            nm = f"{j[1]}_e{j[2]}"
            if (run / "records" / f"{nm}.json").exists():
                raise SystemExit(f"{nm} failed after writing its record; run stops")
            with get_context("spawn").Pool(1) as pool:
                pool.apply(job, (j,))
            status["jobs"][nm] = {"returncode": 0, "rerun": True}
        status["state"] = "ready_for_analysis"
    except BaseException as ex:      # noqa: BLE001  (code errors are not retried: the run is void)
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
    sys.exit(0)
