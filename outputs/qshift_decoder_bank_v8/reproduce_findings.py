"""Reproduce the CF2 audit's code findings against the ORIGINAL v6/v7 code, read-only, and show the v8 fix.

  python reproduce_findings.py        # writes REPRODUCTION.json; launches no job, samples nothing

F3: cf2_run.cmd_run accepts any caller-supplied HEAD (mocked at a later commit) and records no scipy/ldpc.
F4: db6_run.load_checked accepts a duplicated episode, a shared archive and eval_per_block = 1001.
F5: cf2_run.cmd_run reserves with a check-then-write (source evidence).
F6: v7 TruthInvarianceTests calls the real sampler (source evidence).
F7: the 1-in-93 G4 boundary.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import sys
import tempfile
from pathlib import Path

import numpy as np

V8 = Path(__file__).resolve().parent
sys.path.insert(0, str(V8.parent / "qshift_decoder_bank_v7"))
sys.path.insert(0, str(V8))
import cf2_run as R7  # noqa: E402  (imports DB6 and everything below it)
import db6_run as R6  # noqa: E402
import runkit as K  # noqa: E402


def f4_inputs(d, mutate):
    d = Path(d)
    (d / "records").mkdir(parents=True)
    (d / "archives").mkdir()
    for e in (0, 1):
        bits, blocks = {}, []
        for t in R6.C.SCORED:
            v = np.zeros(1000, bool)
            v[:2] = True
            bits[f"b{t:02d}_W0F"] = np.packbits(v)
            blocks.append({"block": t, "errors": {"W0F": 2}})
        np.savez_compressed(d / "archives" / f"X_e{e}.npz", **bits)
    recs = {e: {"schedule": "X", "episode": e, "arms": ["W0F"], "eval_per_block": 1000,
                "blocks": blocks, "archive": f"archives/X_e{e}.npz", "seeds": {}} for e in (0, 1)}
    mutate(recs)
    for e, r in recs.items():
        r["archive_sha256"] = hashlib.sha256((d / r["archive"]).read_bytes()).hexdigest()
        (d / "records" / f"X_e{e}.json").write_text(json.dumps(r), encoding="utf-8")
    (d / "RUN_STATUS.json").write_text(json.dumps({"state": "ready_for_analysis", "n_jobs": 2,
                                                   "jobs": {"X_e0": {"returncode": 0}, "X_e1": {"returncode": 0}}}),
                                       encoding="utf-8")
    return d


def accepts(fn, *a):
    try:
        fn(*a)
        return True
    except (ValueError, SystemExit):
        return False


def main():
    out = {}
    # F4
    muts = {"duplicate_episode_0": lambda r: r[1].update(episode=0),
            "shared_archive": lambda r: r[1].update(archive="archives/X_e0.npz"),
            "eval_per_block_1001": lambda r: r[0].update(eval_per_block=1001)}
    f4 = {}
    for name, m in muts.items():
        old = accepts(R6.load_checked, f4_inputs(tempfile.mkdtemp(), m), {"X": 2}, ("W0F",))
        new = accepts(K.load_strict, f4_inputs(tempfile.mkdtemp(), m), {"X": 2}, ("W0F",), 1000, R6.C.SCORED,
                      lambda s, e: {})
        f4[name] = {"v6_load_checked_accepts": old, "v8_load_strict_accepts": new}
    out["F4"] = f4
    # F3: mocked HEAD at a later commit; intercept pool creation so no job can start
    ctx, work, cf = R7.get_context, R7.WORK, R7.check_freeze
    gh, tc = R7.SK.git_head, R7.SK.tree_clean
    reached = {"pool": False}

    class Stop(Exception):
        pass

    def fake_ctx(*a):
        reached["pool"] = True
        raise Stop
    fz = json.loads(R7.FREEZE.read_text(encoding="utf-8"))
    later = "6bd35b7520736223b6ad950f342df09450c6552c"          # the CF2 result commit
    try:
        R7.SK.git_head, R7.SK.tree_clean = (lambda: later), (lambda: True)
        R7.check_freeze, R7.get_context, R7.WORK = (lambda fz: []), fake_ctx, Path(tempfile.mkdtemp())
        try:
            R7.cmd_run(later, 1)
        except Stop:
            pass
    finally:
        R7.get_context, R7.WORK, R7.check_freeze = ctx, work, cf
        R7.SK.git_head, R7.SK.tree_clean = gh, tc
    out["F3"] = {"v7_cmd_run_reached_pool_at_result_commit": reached["pool"],
                 "v7_frozen_environment_fields": sorted(fz["environment"]),
                 "missing_from_v7_freeze": sorted(set(K.RUNTIME_PACKAGES) - set(fz["environment"])),
                 "v8_runtime_mismatches_vs_v7_freeze": K.check_runtime(fz["environment"])}
    # F5, F6: source evidence
    src = inspect.getsource(R7.cmd_run)
    out["F5"] = {"check_then_write": "if st.exists():" in src and "SK.dump_json(st, status)" in src,
                 "exclusive_create": "O_EXCL" in src,
                 "retry_has_timeout": "pool.apply(job, (j,))" not in src}
    t7 = (V8.parent / "qshift_decoder_bank_v7" / "tests" / "test_cf2.py").read_text(encoding="utf-8")
    body = t7[t7.index("def _mini"):t7.index("def _decisions")]
    out["F6"] = {"v7_mini_wraps_real_sampler": "sample(st, n, sd)" in body and "sample, estimate = D.sample" in body}
    # F7
    out["F7"] = {"cp_upper_1_of_93": K.cp_upper(1, 93), "cp_upper_1_of_92": K.cp_upper(1, 92),
                 "cp_upper_3_of_96": K.cp_upper(3, 96), "min_n_for_0_1_2_3": [K.cp_min_n(k) for k in range(4)]}
    (V8 / "REPRODUCTION.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8",
                                          newline="\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
