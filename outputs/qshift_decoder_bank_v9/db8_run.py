"""DB8 development run: fit-capped lookahead (LA_R1, LA_R2), the CB current-block baseline and fixed keys, with
unknown-state panels (PROTOCOL_DB8.md). Development only.

  python db8_run.py fidelity                          # DB6 dev BB_e0, U_e0 re-run: every DB6 field and DB6-arm bit equal
  python db8_run.py freeze                            # DB8_FREEZE_A3.json (attempt 3; see RUN_ATTEMPT2.md, see RUN_ATTEMPT1.md) (portable; runtime identity; selection table)
  python db8_run.py run --expected-head <sha> [--workers 8]   # the single DB8 attempt (separate approval)

The per-block loop is DB6's episode_job plus the DB8 overlay lines only (tested). Run protections are v8 runkit's.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from multiprocessing import get_context
from pathlib import Path

import numpy as np

import db8_config as C  # noqa: I001  (puts DB6, DB5-DB1, AD2/AD3 and v8 on sys.path; installs the support/truth extensions)
import db2_core as G  # noqa: E402
import db4_core as F  # noqa: E402
import db6_core as L6  # noqa: E402
import db8_core as L8  # noqa: E402
import runkit as RK  # noqa: E402

WORK = C.ROOT / "work"
FREEZE = C.ROOT / "DB8_FREEZE_A3.json"
FREEZE_REL = "outputs/qshift_decoder_bank_v9/DB8_FREEZE_A3.json"
RUN_DIR = WORK / "dev_a3"          # attempts 1-2 (work/dev, work/dev_a2) stopped; see RUN_ATTEMPT1.md, RUN_ATTEMPT2.md
RESULTS_REL = "outputs/qshift_decoder_bank_v9/results"
FID_EPISODES = (("BB", 0), ("U", 0))
FID_REQUIRE = {("BB", 0): "LA_R2"}          # must exercise the primary rule


def _training():
    return json.loads((C.DB1 / "TRAINING.json").read_text(encoding="utf-8"))


def _setup(mode, s, e):
    """-> (truth(t), seed(t, part), n_eval, params, true_changes)."""
    if mode == "fidelity":
        C6 = C.C6
        sd = json.loads((C.DB6 / "DB6_SEEDS.json").read_text(encoding="utf-8"))["seeds"]
        prm = C6.episode_params(s, e, int(sd[f"db6:params:{s}:e{e}"]))
        return (lambda t: C6.block_state(s, t, prm)), (lambda t, p: int(sd[C6.block_key(s, e, t, p)])), \
            C.EVAL_PER_BLOCK, prm, C6.changes(s, prm)
    if mode != "db8":
        raise ValueError(mode)
    sd = json.loads((C.ROOT / "DB8_SEEDS.json").read_text(encoding="utf-8"))["seeds"]
    prm = C.episode_params(s, e, int(sd[f"db8:params:{s}:e{e}"]))
    return (lambda t: C.block_state(s, t, prm)), (lambda t, p: int(sd[C.block_key(s, e, t, p)])), \
        C.EVAL_PER_BLOCK, prm, C.changes(s, prm)


def _bank_arm(kname, est, k_ad, prev):
    """Unknown path shared with DB1: AD's accepted estimate, else hold."""
    if kname is not None:
        return "bank:" + kname, "bank"
    return (k_ad, "learn") if not est["flagged"] else (prev, "hold")


def episode_job(args):
    mode, s, e, run = args
    import ad2
    import ad3
    import db_core as D
    import mm_contract as K
    import re1
    from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m
    run = Path(run)
    out = run / "records" / f"{s}_e{e}.json"
    if out.exists():
        raise SystemExit(f"{out.name} exists")
    truth, seed, n_eval, prm, true_ch = _setup(mode, s, e)
    tr = _training()
    tpl = {k: np.array(v) for k, v in tr["templates"].items()}
    tau_fit, risk, static = tr["tau_fit"], tr["risk"], tr["static_key"]
    t0 = time.perf_counter()
    classes = K.B.load_classes()
    p0 = C.spec(gate_p=C.P0, measurement_p=C.P0)
    a_nom = m.build_matching(m.build_decomposed_dem(m.build_base_circuit(C.spec(**C.NOMINAL))))
    models = {ad2.NOMKEY: (C.spec(**C.NOMINAL), None)}
    for st in C.STATES + ("E",):
        models["bank:" + st] = (p0, C.support(st))
    for st in C.NEW_UNKNOWN:                                      # DB8: models for the new unknown supports
        models["bank:" + st] = (p0, C.support(st))
    decs, seeds_used = {}, {}
    dets, labx, laby, cnt = [], [], [], []
    seg0, changes, gs, library = 0, [], {}, {}
    prev = {a: "bank:" + static for a in C.BANK_ARMS}
    cb_prev = static                                              # DB8: CB's own previous key
    trk = G.Tracker()
    n_alarms_seen = 0
    blocks, bits = [], {}
    dec_s = est_s = 0.0
    for t in range(C.BLOCKS):
        if t >= 2:                                       # change test for block u = t-1 (AD3's, shared)
            u = t - 1
            k0, n0 = ad3.pool(cnt[ad3.segment_lo(seg0, u):u])
            gs[u] = ad3.g_stat(*cnt[u], k0, n0)
            if gs[u] > C.AD3_TAU:
                seg0 = u
                changes.append(u)
        for part, nrow in (("det", C.DET_PER_BLOCK), ("lab", C.LAB_PER_BLOCK)):
            sd = seed(t, part)
            seeds_used[f"b{t:02d}:{part}"] = sd
            x, y = D.sample(truth(t), nrow, sd)
            if part == "det":
                dets.append(x)
                cnt.append(ad3.counts(x))
            else:
                labx.append(x)
                laby.append(y)
        if t < C.WINDOW:
            continue
        te = time.perf_counter()
        truth_sup = C.support(truth(t - 1))
        t_idx, t_flip = ad3._truth(classes, truth_sup)
        w0 = t - C.WINDOW
        model, sup, est = ad2.estimate(dets[w0:t], labx[w0:t], laby[w0:t], classes, truth_sup)
        k_ad = ad2.model_key(est, sup)
        models.setdefault(k_ad, (model, sup))
        # ---- AD3 (verbatim from DB1's episode_job, M = 6)
        seg_len = t - seg0
        src, k3, e3, store = None, None, None, None
        if seg_len >= C.WINDOW:
            src, k3, e3 = "window", k_ad, dict(est)
            if not est["flagged"]:
                store = (k_ad, model, sup, est, ad3.pool(cnt[w0:t]))
        else:
            kk, nn = ad3.pool(cnt[seg0:t])
            hit = ad3.recall(library, kk, nn, C.AD3_TAU)
            if hit is not None:
                ent = library[hit[1]]
                ci, fl = ent["est"]["class_index"], ent["est"]["flip"]
                src, k3 = "recall", ent["key"]
                models.setdefault(k3, (ent["model"], ent["sup"]))
                e3 = {"flagged": False, "class_index": ci, "flip": fl, "true_class": t_idx,
                      "learned_correct": bool(t_idx is not None and ci == t_idx and fl == t_flip),
                      "p_hat": ent["est"]["p_hat"], "b_hat": ent["est"]["b_hat"], "recall_g": hit[0]}
            if src is None:
                src, k3, e3 = "ad_fallback", k_ad, dict(est)
        if store is not None:
            kx, mx, sx, ex, (kc, nc) = store
            library[ad3._ident(ex)] = {"key": kx, "model": mx, "sup": sx, "est": ex, "k": kc, "n": nc}
        e3.update({"source": src, "seg0": seg0, "seg_len": seg_len})
        # ---- bank arms (segment = AD3's segment, at most the last 6 blocks)
        lo = ad3.segment_lo(seg0, t)
        L = t - lo
        kseg, nseg = ad3.pool(cnt[lo:t])
        gf = {st: D.g_fit(kseg, nseg, tpl[st]) for st in C.STATES}
        name = lambda k: k.split(":", 1)[1] if k.startswith("bank:") else None   # noqa: E731
        kb, P = D.bank_decide(gf, L, tau_fit, risk, name(prev["BANK"]))
        alarm = len(changes) > n_alarms_seen
        n_alarms_seen = len(changes)
        trk.observe(P, alarm)
        snap = trk.snapshot()
        kn_arm = {"BANK": kb}
        for arm, (gm, kap) in C.CANDIDATES.items():
            kn_arm[arm] = G.gate(P, risk, trk, name(prev[arm]), gm, kap)
        trk.commit(P)
        keys, srcs = {}, {}
        for arm, kn in kn_arm.items():
            keys[arm], srcs[arm] = F.fallback_key(kn, est, k_ad, prev[arm], static) if arm in C.FALLBACK_ARMS \
                else _bank_arm(kn, est, k_ad, prev[arm])
        prev.update(keys)
        la = L6.lookahead(cnt, seg0, t, tpl, tau_fit)               # DB6: block t's detection rows only
        for arm, base in C.LA_ARMS.items():
            keys[arm], srcs[arm] = L6.la_key(keys.get(base, "bank:" + static), la)
        for arm, base in C.LA2_ARMS.items():
            keys[arm], srcs[arm] = L6.la_key(keys[base], la, gated=False)
        gf1 = L8.single_fit(cnt, t, tpl)                            # DB8: block t's detection rows only
        keys["LA_R1"], srcs["LA_R1"] = L8.rule_key(keys["W0F"], la, gf1, None)
        keys["LA_R2"], srcs["LA_R2"] = L8.rule_key(keys["W0F"], la, gf1, C.R2_CAP)
        keys["LA_R2_170"], srcs["LA_R2_170"] = L8.rule_key(keys["W0F"], la, gf1, C.R2_CAP_SECONDARY)
        keys["CB"], srcs["CB"], cb_prev = L8.cb_key(gf1, tau_fit, risk, cb_prev, keys["W0F"])
        keys.update({a: "bank:" + a[4:] for a in C.FIX_ARMS})
        est_s += time.perf_counter() - te
        st_t = truth(t)
        arm_key = {**keys, "AD3": k3, "STATIC": "bank:" + static, "ORACLE": "bank:" + st_t}
        x, y = D.sample(st_t, n_eval, seed(t, "eval"))
        seeds_used[f"b{t:02d}:eval"] = seed(t, "eval")
        td = time.perf_counter()
        preds = {}
        for k in dict.fromkeys(arm_key.values()):
            if k not in decs:
                decs[k] = re1.decoders(*models[k])
            preds[k] = re1.predict(decs[k][0], x, "l2") != y
        err = {a: preds[k] for a, k in arm_key.items()}
        err["A_nominal"] = re1.predict(a_nom, x, "plain") != y
        dec_s += time.perf_counter() - td
        errs = {}
        for a in C.ARMS:
            errs[a] = int(err[a].sum())
            bits[f"b{t:02d}_{a}"] = np.packbits(err[a])
        acc = {a: D.acceptable(models[k][1], st_t, classes) for a, k in arm_key.items()}
        blocks.append({"block": t, "state": st_t, "estimate": est, "estimate_ad3": ad2._jsonable(e3),
                       "g_prev": gs.get(t - 1), "seg0": seg0, "L": L, "gfit": {k: round(v, 3) for k, v in gf.items()},
                       "plausible": P, "alarm": alarm, "tracker": snap, "keys": arm_key,
                       "source": {**srcs, "AD3": src}, "acceptable": acc,
                       "burst_action": {a: models[k][1] is not None for a, k in arm_key.items()}, "errors": errs})
        blocks[-1]["lookahead"] = la
        blocks[-1]["db8"] = {"gf1": gf1}
        keep = {k for k in models if k.startswith("bank:")} | {ad2.NOMKEY, k_ad, k3} | set(keys.values()) | \
            {v["key"] for v in library.values()}
        decs = {k: v for k, v in decs.items() if k in keep}
        models = {k: v for k, v in models.items() if k in keep}
    (run / "archives").mkdir(parents=True, exist_ok=True)
    arc = run / "archives" / f"{s}_e{e}.npz"
    np.savez_compressed(arc, **bits)
    rec = {"schedule": s, "episode": e, "mode": mode, "params": prm, "states": [truth(t) for t in range(C.BLOCKS)],
           "true_changes": true_ch, "arms": list(C.ARMS), "eval_per_block": n_eval, "seeds": seeds_used,
           "static_key": static, "changes_detected": changes, "g": {str(k): v for k, v in sorted(gs.items())},
           "blocks": blocks, "archive": f"archives/{arc.name}",
           "archive_sha256": hashlib.sha256(arc.read_bytes()).hexdigest(),
           "timing": {"decode_s": round(dec_s, 1), "control_s": round(est_s, 1)},
           "seconds": round(time.perf_counter() - t0, 1)}
    import studykit as SK
    SK.write_once_json(out, ad2._jsonable(rec))
    return out.name


# ------------------------------------------------------------------ input tracing (for the portable freeze)
def traced_job(args):
    import studykit as SK
    repo, work = SK.REPO.resolve(), WORK.resolve()
    seen = set()

    def hook(ev, a):
        if ev == "open" and a and isinstance(a[0], (str, Path)):
            try:
                p = Path(a[0]).resolve()
            except (OSError, ValueError):
                return
            if p.is_relative_to(repo) and not p.is_relative_to(work):
                seen.add(p)

    sys.addaudithook(hook)
    name = episode_job(args)
    mods = {Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m, "__file__", None)}
    seen |= {p for p in mods if p.is_relative_to(repo) and p.suffix == ".py"}
    return name, sorted(p.relative_to(repo).as_posix() for p in seen if p.is_file())


# ------------------------------------------------------------------ fidelity
TOP = ("params", "states", "true_changes", "seeds", "changes_detected", "g", "static_key", "eval_per_block")
BLOCK_FIELDS = ("block", "state", "estimate", "estimate_ad3", "g_prev", "seg0", "L", "gfit", "plausible", "alarm",
                "tracker", "lookahead")
ARM_FIELDS = ("keys", "errors", "source", "acceptable", "burst_action")


def compare_db6(mine, ref, z_mine, z_ref):
    """Every DB6 field and every DB6-arm array equal; DB8 adds only arms and the "db8" block field."""
    import db6_config as C6
    d = {f: mine[f] == ref[f] for f in TOP}
    d["blocks"] = len(mine["blocks"]) == len(ref["blocks"]) and all(
        all(b[f] == r[f] for f in BLOCK_FIELDS) and all({a: b[f][a] for a in r[f]} == r[f] for f in ARM_FIELDS)
        for b, r in zip(mine["blocks"], ref["blocks"]))
    d["db6_arms_first"] = list(mine["arms"][:len(C6.ARMS)]) == list(C6.ARMS) == list(ref["arms"])
    d["bits_db6_arms"] = all(np.array_equal(z_ref[k], z_mine[k]) for k in z_ref.files)
    return d


def cmd_fidelity():
    import studykit as SK
    run = WORK / "fidelity"
    (run / "records").mkdir(parents=True, exist_ok=False)
    js = [("fidelity", s, e, str(run)) for s, e in FID_EPISODES]
    with get_context("spawn").Pool(len(js)) as pool:
        tr = pool.map(traced_job, js)
    res, inputs = {"episodes": {}}, set()
    for (s, e), (_, files) in zip(FID_EPISODES, tr):
        inputs |= set(files)
        mine = json.loads((run / "records" / f"{s}_e{e}.json").read_text(encoding="utf-8"))
        ref = json.loads((C.DB6 / "results" / "dev" / "records" / f"{s}_e{e}.json").read_text(encoding="utf-8"))
        d = compare_db6(mine, ref, np.load(run / mine["archive"]), np.load(C.DB6 / "work" / "dev" / ref["archive"]))
        uses = {a: sum(b["source"].get(a) == "lookahead" for b in mine["blocks"]) for a in C.RULE_ARMS}
        need = FID_REQUIRE.get((s, e))
        d["pass"] = all(d.values()) and (need is None or uses[need] > 0)
        res["episodes"][f"DB6 dev {s}_e{e}"] = {**{k: bool(v) for k, v in d.items()}, "rule_uses": uses}
    res["compared"] = ("top-level " + ", ".join(TOP) + "; every block's DB6 fields and DB6-arm entries; every DB6-arm "
                       "archive array bit for bit")
    res["traced_inputs"] = sorted(inputs)
    res["all_pass"] = all(v["pass"] for v in res["episodes"].values())
    SK.write_once_json(C.ROOT / "FIDELITY.json", res)
    print(json.dumps({k: v for k, v in res.items() if k != "traced_inputs"}, indent=1), len(inputs), "inputs traced")


# ------------------------------------------------------------------ portable freeze
TEXT = {".py", ".json", ".md", ".txt", ".csv", ".toml", ".cfg"}
SEAL_MARKERS = ("seal", "SEALED", "HIDDEN", "R" "6_")


def _norm_sha(rel, data):
    if Path(rel).suffix in TEXT:
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def _git(args):
    import studykit as SK
    p = subprocess.run(["git"] + args, cwd=SK.REPO, capture_output=True)
    if p.returncode:
        raise SystemExit(f"git {' '.join(args)} failed")
    return p.stdout.decode("utf-8", "replace") if args[0] != "show" else p.stdout


def _blob(rel, rev="HEAD"):
    return _git(["show", f"{rev}:{rel}"])


def freeze_files():
    fid = json.loads((C.ROOT / "FIDELITY.json").read_text(encoding="utf-8"))
    ls = _git(["ls-files"] + [f"outputs/qshift_decoder_bank_v{i}" for i in range(1, 10)]).split()
    fs = {f for f in ls if f.endswith(".py")} | set(fid["traced_inputs"])
    fs = {f for f in fs if "/work/" not in f and "__pycache__" not in f and not f.endswith(".pyc")}
    fs |= {f"outputs/qshift_adaptive_robust_v1/{n}_BURSTS.json" for n in ("BRE", "BRS", "BRT")}
    fs |= {f"outputs/qshift_decoder_bank_v9/{n}" for n in ("DB8_SEEDS.json", "PROTOCOL_DB8.md", "FIDELITY.json",
                                                         "SELECTION.json", "DB8_FREEZE.json", "DB8_FREEZE_A2.json", "DB8_FREEZE_A2b.json",
                                                         "DB8_FREEZE_A2c.json", "SELECTION_A3.json", "AMENDMENT_A3.md",
                                                         "RUN_ATTEMPT2.md", "RUN_ATTEMPT2/journal.jsonl",
                                                         "RUN_ATTEMPT2/RUN_STATUS.json", "RUN_ATTEMPT2/OUTPUTS.json",
                                                         ".gitattributes", "RUN_ATTEMPT1.md",
                                                         "RUN_ATTEMPT1/journal.jsonl",
                                                         "RUN_ATTEMPT1/RUN_STATUS.json",
                                                         "RUN_ATTEMPT1/PARTIALS.json")}
    bad = [f for f in fs if any(m in Path(f).name for m in SEAL_MARKERS)]
    if bad:
        raise SystemExit(f"sealed-looking inputs: {bad}")
    return sorted(fs)


def check_freeze(fz):
    import studykit as SK
    out = []
    for rel, h in fz["files"].items():
        p = SK.REPO / rel
        if not p.is_file() or _norm_sha(rel, p.read_bytes()) != h or _norm_sha(rel, _blob(rel)) != h:
            out.append(rel)
    return out


def cmd_freeze():
    import studykit as SK
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
    dec = {k: getattr(C, k) for k in ("R2_CAP", "R2_CAP_SECONDARY", "A1_RETENTION", "A1_ALPHA", "A2_MAX_EPISODES",
                                      "A3_EPISODE_CAP", "A3_BLOCK_CAP", "A3_UNKNOWN_EPISODE_CAP")}
    dec.update(A2_PANELS=list(C.A2_PANELS), A4_BASELINES=list(C.A4_BASELINES))
    doc = {"schema": "qshift-decoder-bank-db8-freeze-v1", "study": "DB8-dev", "files": hashes,
           "file_count": len(hashes), "code_head": SK.git_head(), "runtime": RK.runtime_identity(),
           "hash_rule": "sha256 of the committed blob with CRLF->LF for text suffixes " + ",".join(sorted(TEXT)),
           "binding": "the run requires HEAD = the commit adding this file, whose parent is code_head and which "
                      "changes only this file (runkit.check_revision), plus the exact runtime above",
           "unknown_states": {k: list(v) for k, v in C.NEW_UNKNOWN.items()},
           "decision": dec, "episodes": C.EPISODES, "attempt": 3, "amendment": "AMENDMENT_A3.md",
           "supersedes": ["DB8_FREEZE.json", "DB8_FREEZE_A2.json", "DB8_FREEZE_A2b.json", "DB8_FREEZE_A2c.json"],
           "study_samples_before_freeze": "attempt 1 (work/dev) wrote 7 episode archives and no records; attempt 2 (work/dev_a2) wrote 28 records and archives (non-null in-bank panels and U_E only; no U_FAR output). All are preserved unopened and unanalysed, byte hashes in RUN_ATTEMPT1/PARTIALS.json and RUN_ATTEMPT2/OUTPUTS.json. Attempt 3 re-runs all 64 episodes from the same seeds into work/dev_a3; only attempt 3 is analysed"}
    SK.write_once_json(FREEZE, doc)
    print(len(hashes), "files frozen")


# ------------------------------------------------------------------ the DB8 run (separate approval)
def _outputs(name):
    return (f"archives/{name}.npz", f"records/{name}.json")


def _prepare_run(run):
    """Create the parent folder of every output path (attempt 1 stopped because records/ was missing)."""
    for rel in _outputs("x"):
        (Path(run) / rel).parent.mkdir(parents=True, exist_ok=True)


def cmd_run(expected_head, workers):
    if not FREEZE.exists():
        raise SystemExit(f"no {FREEZE.name}")
    fz = json.loads(FREEZE.read_text(encoding="utf-8"))
    RK.check_revision(expected_head, FREEZE_REL, fz["code_head"], _git, (RESULTS_REL,))
    bad = RK.check_runtime(fz["runtime"])
    if bad:
        raise SystemExit(f"runtime differs from the freeze: {bad}")
    bad = check_freeze(fz)
    if bad:
        raise SystemExit(f"frozen files changed: {bad}")
    if not json.loads((C.ROOT / "FIDELITY.json").read_text(encoding="utf-8"))["all_pass"]:
        raise SystemExit("fidelity did not pass")
    run = RUN_DIR
    RK.Reservation(run, {"head": expected_head, "workers": workers})
    _prepare_run(run)
    jobs = [(f"{s}_e{e}", ("db8", s, e, str(run))) for s in C.SCHEDULES for e in range(C.EPISODES[s])]
    jobs.sort(key=lambda j: j[1][1] in C.NULL_SCHED)
    RK.run_jobs(jobs, episode_job, run, _outputs, workers=workers, timeout=20_000)


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
