"""DB6 development run: alarm-gated block-lookahead overlay (LA) against W0F and the DB4 arms (PROPOSAL_DB6.md).

  python db6_run.py fidelity                                   # DB4 dev AA_e3, BA_e0: DB4 arms bit-exact; LA = replay
  python db6_run.py freeze                                     # DB6_FREEZE.json (portable: LF-normalized blobs)
  python db6_run.py dev --expected-head <sha> [--workers 8]    # the single development attempt
  python db6_run.py analyze <out_dir>                          # ANALYSIS.json + TIMELINE.json (twice -> identical)

Per block t (6-29) every arm decodes the same 1,000 evaluation rows. Base arms use only blocks < t (as DB4).
LA arms may also use block t's own 2,000 detection-only rows (one block of decoding latency); never labels,
evaluation rows or truth. The per-block loop is DB4's episode_job plus the LA overlay lines (tested).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from multiprocessing import TimeoutError as MPTimeout
from multiprocessing import get_context
from pathlib import Path

import numpy as np

import db6_config as C  # noqa: I001  (puts DB4, DB3, DB2, DB1 and AD2/AD3 on sys.path first)
import db2_core as G  # noqa: E402
import db4_core as F  # noqa: E402
import db6_core as L6  # noqa: E402

WORK = C.ROOT / "work"
FID_EPISODES = (("AA", 3), ("BA", 0))


def _training():
    return json.loads((C.DB1 / "TRAINING.json").read_text(encoding="utf-8"))


def _setup(mode, s, e):
    """-> (truth(t), seed(t, part), n_eval, params, true_changes)."""
    if mode == "fidelity":
        C4 = C.C4
        sd = json.loads((C.DB4 / "DB4_SEEDS.json").read_text(encoding="utf-8"))["seeds"]
        prm = C4.episode_params(s, e, int(sd[f"db4:params:{s}:e{e}"]))
        return (lambda t: C4.block_state(s, t, prm)), (lambda t, p: int(sd[C4.block_key(s, e, t, p)])), \
            C.EVAL_PER_BLOCK, prm, C4.changes(s, prm)
    sd = json.loads((C.ROOT / "DB6_SEEDS.json").read_text(encoding="utf-8"))["seeds"]
    prm = C.episode_params(s, e, int(sd[f"db6:params:{s}:e{e}"]))
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
    decs, seeds_used = {}, {}
    dets, labx, laby, cnt = [], [], [], []
    seg0, changes, gs, library = 0, [], {}, {}
    prev = {a: "bank:" + static for a in C.BANK_ARMS}
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
    """episode_job with an audit hook that lists every repo file the job opens and every repo module it loads."""
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
BLOCK_FIELDS = ("state", "estimate", "estimate_ad3", "g_prev", "seg0", "L", "gfit", "plausible", "alarm", "tracker")
ARM_FIELDS = ("keys", "errors", "source", "acceptable", "burst_action")


def _replay_la(ref_blocks, i):
    if i + 1 >= len(ref_blocks):
        return None
    nb = ref_blocks[i + 1]
    if nb["L"] == 1 and nb["seg0"] == ref_blocks[i]["block"] and len(nb["plausible"]) == 1:
        return "bank:" + nb["plausible"][0]
    return False


def cmd_fidelity():
    import studykit as SK
    run = WORK / "fidelity"
    (run / "records").mkdir(parents=True, exist_ok=False)
    js = [("fidelity", s, e, str(run)) for s, e in FID_EPISODES]
    with get_context("spawn").Pool(len(js)) as pool:
        traced = pool.map(traced_job, js)
    res, inputs = {"episodes": {}}, set()
    for (s, e), (_, files) in zip(FID_EPISODES, traced):
        inputs |= set(files)
        mine = json.loads((run / "records" / f"{s}_e{e}.json").read_text(encoding="utf-8"))
        ref = json.loads((C.DB4 / "results" / "dev" / "records" / f"{s}_e{e}.json").read_text(encoding="utf-8"))
        z0, z1 = np.load(C.DB4 / "work" / "dev" / ref["archive"]), np.load(run / mine["archive"])
        d = {f: mine[f] == ref[f] for f in ("params", "states", "true_changes", "seeds", "changes_detected", "g")}
        d["bits_db4_arms"] = all(np.array_equal(z0[k], z1[k]) for k in z0.files)
        d["blocks_db4_fields"] = all(
            all(b[f] == r[f] for f in BLOCK_FIELDS) and all({a: b[f][a] for a in r[f]} == r[f] for f in ARM_FIELDS)
            for b, r in zip(mine["blocks"], ref["blocks"]))
        la_ok, la_uses, skipped, g_ok = True, 0, 0, True
        for i, (b, r) in enumerate(zip(mine["blocks"], ref["blocks"])):
            t, lk = b["block"], b["lookahead"]
            if str(t) in ref["g"]:
                g_ok &= lk["g"] == ref["g"][str(t)]
                g_ok &= lk["alarm"] == (t in ref["changes_detected"])
            exp = _replay_la(ref["blocks"], i)
            if exp is None:
                skipped += 1
                continue
            want = exp if exp else b["keys"]["W0F"]
            la_ok &= b["keys"]["LA_W0F"] == want
            la_uses += bool(exp)
        d.update(la_equals_replay=bool(la_ok), la_uses=la_uses, la_last_block_unchecked=skipped, g_and_alarm=bool(g_ok))
        d["pass"] = all(v for k, v in d.items() if k not in ("la_uses", "la_last_block_unchecked"))
        res["episodes"][f"DB4 dev {s}_e{e}"] = d
    res["traced_inputs"] = sorted(inputs)
    res["all_pass"] = all(v["pass"] for v in res["episodes"].values())
    SK.write_once_json(C.ROOT / "FIDELITY.json", res)
    print(json.dumps({k: v for k, v in res.items() if k != "traced_inputs"}, indent=1), len(inputs), "inputs traced")


# ------------------------------------------------------------------ portable freeze (LF-normalized committed blobs)
FREEZE = C.ROOT / "DB6_FREEZE.json"
TEXT = {".py", ".json", ".md", ".txt", ".csv", ".toml", ".cfg"}
SEAL_MARKERS = ("seal", "SEALED", "HIDDEN", "R" "6_")   # split so the no-seal source scan stays meaningful


def _norm_sha(rel, data):
    if Path(rel).suffix in TEXT:
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def _blob(rel, rev="HEAD"):
    import subprocess
    import studykit as SK
    p = subprocess.run(["git", "show", f"{rev}:{rel}"], cwd=SK.REPO, capture_output=True)
    if p.returncode:
        raise SystemExit(f"not committed at {rev}: {rel}")
    return p.stdout


def freeze_files():
    import subprocess
    import studykit as SK
    fid = json.loads((C.ROOT / "FIDELITY.json").read_text(encoding="utf-8"))
    ls = subprocess.run(["git", "ls-files"] + [f"outputs/qshift_decoder_bank_v{i}" for i in range(1, 7)],
                        cwd=SK.REPO, capture_output=True, text=True, check=True).stdout.split()
    fs = {f for f in ls if f.endswith(".py")} | set(fid["traced_inputs"])
    fs = {f for f in fs if "/work/" not in f and "__pycache__" not in f and not f.endswith(".pyc")}
    fs |= {f"outputs/qshift_adaptive_robust_v1/{n}_BURSTS.json" for n in ("BRE", "BRS", "BRT")}   # config-named assets
    fs |= {f"outputs/qshift_decoder_bank_v6/{n}" for n in ("DB6_SEEDS.json", "PROPOSAL_DB6.md", "FIDELITY.json")}
    bad = [f for f in fs if any(m in Path(f).name for m in SEAL_MARKERS)]
    if bad:
        raise SystemExit(f"sealed-looking inputs: {bad}")
    return sorted(fs)


def check_freeze(fz):
    """-> files whose working copy or committed HEAD blob (both LF-normalized) differ from the freeze."""
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
    files = freeze_files()
    hashes = {}
    for rel in files:
        w, b = _norm_sha(rel, (SK.REPO / rel).read_bytes()), _norm_sha(rel, _blob(rel))
        if w != b:
            raise SystemExit(f"working copy differs from HEAD: {rel}")
        hashes[rel] = b
    doc = {"schema": "qshift-decoder-bank-db6-freeze-v1", "study": "DB6-dev", "files": hashes,
           "file_count": len(hashes), "code_head": SK.git_head(),
           "hash_rule": "sha256 of the committed blob with CRLF->LF for text suffixes " + ",".join(sorted(TEXT)),
           "inputs": "tracked .py in decoder_bank v1-v6, every repo file the fidelity jobs opened or imported "
                     "(audit hook), DB6_SEEDS.json, PROPOSAL_DB6.md, FIDELITY.json",
           "non_circular_binding": "Excludes its own digest; the run requires --expected-head = the commit containing "
                                   "this file, a clean tree, and every hash above on both the working copy and HEAD.",
           "decision": {k: getattr(C, k) for k in ("E1_MEAN", "E1_ALPHA", "S1_EPISODE_CAP", "S2_BLOCK_CAP",
                                                   "S3_WRONG_MAX", "S4_RX_EPISODE_CAP")},
           "episodes": C.EPISODES, "study_samples_before_freeze": 0}
    SK.write_once_json(FREEZE, doc)
    print(len(hashes), "files frozen")


# ------------------------------------------------------------------ development run
INFRA = (OSError, MemoryError, EOFError, ConnectionError, MPTimeout)


def cmd_dev(expected_head, workers):
    import studykit as SK
    if SK.git_head() != expected_head:
        raise SystemExit(f"HEAD {SK.git_head()} != expected {expected_head}")
    if not SK.tree_clean():
        raise SystemExit("working tree not clean")
    bad = check_freeze(json.loads(FREEZE.read_text(encoding="utf-8")))
    if bad:
        raise SystemExit(f"frozen files changed: {bad}")
    if not json.loads((C.ROOT / "FIDELITY.json").read_text(encoding="utf-8"))["all_pass"]:
        raise SystemExit("fidelity did not pass")
    run = WORK / "dev"
    st = run / "RUN_STATUS.json"
    if st.exists():
        raise SystemExit("RUN_STATUS.json exists; single attempt only")
    (run / "records").mkdir(parents=True, exist_ok=True)
    js = [("dev", s, e, str(run)) for s in C.SCHEDULES for e in range(C.EPISODES[s])]
    js.sort(key=lambda j: j[1] in C.NULL_SCHED)
    status = {"head": SK.git_head(), "workers": workers, "state": "running", "reruns": {},
              "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "jobs": {}}
    SK.dump_json(st, status)
    t0 = time.perf_counter()
    try:
        failed = []
        with get_context("spawn").Pool(workers) as pool:
            hs = [(j, pool.apply_async(episode_job, (j,))) for j in js]
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
                pool.apply(episode_job, (j,))
            status["jobs"][nm] = {"returncode": 0, "rerun": True}
        status["state"] = "ready_for_analysis"
    except BaseException as ex:      # noqa: BLE001  (code errors are not retried: the run is void)
        status["state"], status["error"] = "failed", repr(ex)
        raise
    finally:
        status.update(finished=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                      wall_seconds=round(time.perf_counter() - t0, 1), n_jobs=len(js))
        SK.dump_json(st, status)


# ------------------------------------------------------------------ analysis (PROPOSAL_DB6.md section 4)
def sign_test_p(d):
    """One-sided exact sign test: P(at least k negatives of n nonzero | p = 1/2)."""
    from math import comb
    nz = [x for x in d if x != 0]
    n, k = len(nz), sum(x < 0 for x in nz)
    return 1.0 if n == 0 else float(sum(comb(n, i) for i in range(k, n + 1)) / 2 ** n)


def cp_upper(k, n, a=0.05):
    """One-sided Clopper-Pearson upper bound for k events in n."""
    from math import comb
    if n == 0:
        return 1.0
    lo, hi = 0.0, 1.0
    for _ in range(80):
        p = (lo + hi) / 2
        c = sum(comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k + 1))
        lo, hi = (p, hi) if c > a else (lo, p)
    return hi


def load_checked(run, episodes, arms):
    """Records with strict archive validation: hash, exact key set, exact packed width, zero padding, counts."""
    st = json.loads((run / "RUN_STATUS.json").read_text(encoding="utf-8"))
    if st["state"] != "ready_for_analysis":
        raise SystemExit(f"run state {st['state']}")
    recs = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((run / "records").glob("*.json"))]
    if len(recs) != st["n_jobs"] or len(recs) != sum(episodes.values()):
        raise SystemExit("record count does not match jobs")
    width = -(-C.EVAL_PER_BLOCK // 8)
    for r in recs:
        if hashlib.sha256((run / r["archive"]).read_bytes()).hexdigest() != r["archive_sha256"]:
            raise ValueError("archive hash")
        if list(r["arms"]) != list(arms):
            raise ValueError("arm list")
        z = np.load(run / r["archive"])
        want = {f"b{b['block']:02d}_{a}" for b in r["blocks"] for a in arms}
        if set(z.files) != want or [b["block"] for b in r["blocks"]] != list(C.SCORED):
            raise ValueError("archive keys")
        for b in r["blocks"]:
            for a in arms:
                v = z[f"b{b['block']:02d}_{a}"]
                if v.dtype != np.uint8 or v.shape != (width,):
                    raise ValueError("archive width")
                bits = np.unpackbits(v)
                if bits[r["eval_per_block"]:].any() or int(bits.sum()) != b["errors"][a]:
                    raise ValueError("count mismatch")
    return st, recs


def analyze(run):
    st, recs = load_checked(run, C.EPISODES, C.ARMS)
    n_rows = len(C.SCORED) * C.EVAL_PER_BLOCK
    out = {"schema": "qshift-decoder-bank-db6-analysis-v1", "run_status": {k: st.get(k) for k in
           ("head", "started", "finished", "wall_seconds", "n_jobs", "reruns")}, "schedules": {}}
    tl = {"schema": "qshift-decoder-bank-db6-timeline-v1", "blocks": list(C.SCORED), "schedules": {}}
    eps, worst_block, uses, wrong = [], [], 0, 0
    for s in C.SCHEDULES:
        rr = sorted([r for r in recs if r["schedule"] == s], key=lambda r: r["episode"])
        tot = {a: [sum(b["errors"][a] for b in r["blocks"]) for r in rr] for a in C.ARMS}
        u = [sum(b["source"]["LA_W0F"] == "lookahead" for b in r["blocks"]) for r in rr]
        w = [sum(b["source"]["LA_W0F"] == "lookahead" and b["keys"]["LA_W0F"] != "bank:" + b["state"]
                 for b in r["blocks"]) for r in rr]
        uses, wrong = uses + sum(u), wrong + sum(w)
        for r in rr:
            worst_block.append(max(b["errors"]["LA_W0F"] - b["errors"]["W0F"] for b in r["blocks"]))
            eps.append((s, r["episode"], {a: sum(b["errors"][a] for b in r["blocks"]) for a in C.ARMS}))
        out["schedules"][s] = {"episodes": len(rr), "params": [r["params"] for r in rr],
                               "errors": {a: int(sum(v)) for a, v in tot.items()}, "errors_per_episode": tot,
                               "ler": {a: float(sum(v) / (len(rr) * n_rows)) for a, v in tot.items()},
                               "LA_W0F_uses": u, "LA_W0F_wrong_state": w}
        tl["schedules"][s] = {"state": [[b["state"] for b in r["blocks"]] for r in rr],
                              "lookahead": [[b["lookahead"] for b in r["blocks"]] for r in rr],
                              "keys": {a: [[b["keys"][a] for b in r["blocks"]] for r in rr]
                                       for a in C.BANK_ARMS + tuple(C.LA_ARMS) + tuple(C.LA2_ARMS)},
                              "errors": {a: [[b["errors"][a] for b in r["blocks"]] for r in rr] for a in C.ARMS}}
    d = [e[2]["LA_W0F"] - e[2]["W0F"] for e in eps]
    rx = [e[2]["LA_W0F"] - e[2]["W0F"] for e in eps if e[0] == "RX"]
    pooled = {a: sum(e[2][a] for e in eps) for a in C.ARMS}
    m = lambda a, b: float(np.mean([e[2][a] - e[2][b] for e in eps]))   # noqa: E731
    v = {"E1_mean_LA_W0F_minus_W0F": float(np.mean(d)), "E1_sign_p": sign_test_p(d), "E1_d": d,
         "E2_LA_W0F_minus_LA_BANK": m("LA_W0F", "LA_BANK"), "E2_LA_W0F_minus_LA_DB2": m("LA_W0F", "LA_DB2"),
         "S1_max_episode_harm": max(d), "S2_max_block_harm": max(worst_block),
         "S3_uses": uses, "S3_wrong": wrong, "S3_rate": wrong / uses if uses else 0.0,
         "S3_cp_upper": cp_upper(wrong, uses), "S4_RX_d": rx, "S4_RX_pooled": sum(rx),
         "R_harm_episodes": sum(x > 0 for x in d), "R_harm_cp_upper": cp_upper(sum(x > 0 for x in d), len(d)),
         "R_LA2_W0F_minus_W0F": m("LA2_W0F", "W0F"), "pooled_errors": pooled}
    c = {"E1": v["E1_mean_LA_W0F_minus_W0F"] <= C.E1_MEAN and v["E1_sign_p"] <= C.E1_ALPHA,
         "S1": v["S1_max_episode_harm"] <= C.S1_EPISODE_CAP, "S2": v["S2_max_block_harm"] <= C.S2_BLOCK_CAP,
         "S3": v["S3_rate"] <= C.S3_WRONG_MAX,
         "S4": v["S4_RX_pooled"] <= 0 and all(x <= C.S4_RX_EPISODE_CAP for x in rx)}
    c = {k: bool(x) for k, x in c.items()}
    c["ADVANCE"] = all(c.values())
    best = min(("LA_W0F", "LA_BANK", "LA_DB2"), key=lambda a: (pooled[a], a != "LA_W0F"))
    c["E2_confirm_arm"] = best
    c["values"] = v
    out["criteria"] = c
    return out, tl


def cmd_analyze(out_dir):
    import studykit as SK
    res, tl = analyze(WORK / "dev")
    o = Path(out_dir)
    o.mkdir(parents=True, exist_ok=False)
    SK.write_once_json(o / "ANALYSIS.json", res)
    SK.write_once_json(o / "TIMELINE.json", tl)
    print(json.dumps({k: x for k, x in res["criteria"].items() if k != "values"}, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["fidelity", "freeze", "dev", "analyze"])
    ap.add_argument("path", nargs="?")
    ap.add_argument("--expected-head")
    ap.add_argument("--workers", type=int, default=8)
    x = ap.parse_args()
    if x.cmd == "fidelity":
        cmd_fidelity()
    elif x.cmd == "freeze":
        cmd_freeze()
    elif x.cmd == "dev":
        if not x.expected_head:
            raise SystemExit("--expected-head is required")
        cmd_dev(x.expected_head, x.workers)
    else:
        cmd_analyze(x.path)
