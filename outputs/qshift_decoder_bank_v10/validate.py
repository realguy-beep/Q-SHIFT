"""Semantic validation of DB8-format records, and analysis input bound to one run (audit F5).

v8 load_strict checks hashes, seeds, widths and counts but not whether states, keys and sources agree.
  validate_record   every metadata field against the schedule, seeds and decision rules
  arrays            archive bytes -> checked bit arrays (the same bytes that were hashed)
  load_bound        a runkit2 run: reservation, status, journal, worker events, commits, then both checks above"""
from __future__ import annotations

import io
import json
import math
from collections import Counter

import numpy as np

import db8_config as C  # noqa: I001
import runkit2 as R2
from seed_spec import SeedSpec

RECORD_KEYS = {"archive", "archive_sha256", "arms", "blocks", "changes_detected", "episode", "eval_per_block", "g", "mode",
               "params", "schedule", "seconds", "seeds", "states", "static_key", "timing", "true_changes"}
BLOCK_KEYS = {"L", "acceptable", "alarm", "block", "burst_action", "db8", "errors", "estimate", "estimate_ad3", "g_prev",
              "gfit", "keys", "lookahead", "plausible", "seg0", "source", "state", "tracker"}
KEYED = tuple(a for a in C.ARMS if a != "A_nominal")
CAPS = {"LA_R1": None, "LA_R2": C.R2_CAP, "LA_R2_170": C.R2_CAP_SECONDARY}
BANKLIKE = ("BANK", "DB2", "DB2_PLAN", "W0", "W0F")
SOURCES = {**{a: {"bank", "learn", "hold"} for a in BANKLIKE}, "W0F": {"bank", "learn", "static_fallback"},
           "AD3": {"window", "recall", "ad_fallback"}, "CB": {"cb", "w0f"},
           **{a: {"lookahead", "base"} for a in (*C.LA_ARMS, *C.LA2_ARMS, *CAPS)}}
BANK_KEYS = {"bank:" + s for s in C.STATES}


def spec():
    return SeedSpec(C.BLOCKS, C.SCORED, C.block_key)


def training():
    return json.loads((C.DB1 / "TRAINING.json").read_text(encoding="utf-8"))


def db8_seeds():
    return json.loads((C.ROOT / "DB8_SEEDS.json").read_text(encoding="utf-8"))["seeds"]


def need(ok, what):
    if not ok:
        raise ValueError(what)


def _learned(k):
    """A key learned by AD/AD3: 'nominal' or a canonical ["est", p, b, support|null] list."""
    if k == "nominal":
        return True
    try:
        v = json.loads(k)
    except (TypeError, ValueError):
        return False
    return isinstance(v, list) and len(v) == 4 and v[0] == "est" and all(
        isinstance(x, (int, float)) and math.isfinite(x) for x in v[1:3]) and (
        v[3] is None or (isinstance(v[3], list) and all(type(q) is int for q in v[3])))


def _single(la):
    return la["P1"][0] if len(la["P1"]) == 1 else None


def validate_record(r, seeds, tr, ident, extra=()):
    """`extra`: additional required top-level fields (runkit2 adds run_id)."""
    s, e = ident
    nm = f"{s}_e{e}"
    need(set(r) == RECORD_KEYS | set(extra), f"{nm}: record fields")
    need((r["schedule"], r["episode"], r["mode"]) == (s, e, "db8"), f"{nm}: identity or mode")
    need(r["archive"] == f"archives/{nm}.npz" or r["archive"] == "archive.npz", f"{nm}: archive name")
    need(r["eval_per_block"] == C.EVAL_PER_BLOCK and r["arms"] == list(C.ARMS), f"{nm}: rows or arms")
    need(r["seeds"] == spec().expected(seeds, s, e), f"{nm}: seeds")
    prm = C.episode_params(s, e, int(seeds[f"db8:params:{s}:e{e}"]))
    need(r["params"] == json.loads(json.dumps(prm)), f"{nm}: params")
    need(r["states"] == [C.block_state(s, t, prm) for t in range(C.BLOCKS)], f"{nm}: states")
    need(r["true_changes"] == C.changes(s, prm), f"{nm}: true changes")
    static = tr["static_key"]
    need(r["static_key"] == static, f"{nm}: static key")
    need([b["block"] for b in r["blocks"]] == list(C.SCORED), f"{nm}: scored blocks")
    prev = {a: "bank:" + static for a in BANKLIKE}
    cb_prev = static
    for b in r["blocks"]:
        w = f"{nm} b{b['block']:02d}: "
        need(set(b) == BLOCK_KEYS, w + "block fields")
        need(b["state"] == r["states"][b["block"]], w + "state")
        ks, src, la = b["keys"], b["source"], b["lookahead"]
        need(set(ks) == set(KEYED) and set(b["acceptable"]) == set(KEYED) and set(b["burst_action"]) == set(KEYED), w + "key arms")
        need(set(src) == set(SOURCES) and all(src[a] in SOURCES[a] for a in src), w + "sources")
        need(set(b["errors"]) == set(C.ARMS) and all(type(v) is int and 0 <= v <= C.EVAL_PER_BLOCK
                                                     for v in b["errors"].values()), w + "errors")
        need(all(type(v) is bool for f in ("acceptable", "burst_action") for v in b[f].values()), w + "flags")
        need(all(ks[a] in BANK_KEYS or _learned(ks[a]) for a in KEYED if a != "ORACLE"), w + "key format")
        need(ks["ORACLE"] == "bank:" + b["state"] and ks["STATIC"] == "bank:" + static, w + "ORACLE/STATIC key")
        need(all(ks[a] == "bank:" + a[4:] for a in C.FIX_ARMS), w + "FIX key")
        need(_learned(ks["AD3"]), w + "AD3 key")
        for a in BANKLIKE:
            k = ks[a]
            good = {"bank": k in BANK_KEYS and bool(b["plausible"]), "learn": _learned(k) and not b["plausible"],
                    "hold": k == prev[a] and not b["plausible"],
                    "static_fallback": k == "bank:" + static and not b["plausible"]}[src[a]]
            need(good, w + f"{a} key does not follow from its source")
            prev[a] = k
        gf = b["db8"]["gf1"]
        need(set(gf) == set(C.STATES) and all(math.isfinite(v) for v in gf.values()), w + "gf1")
        need(la["P1"] == [x for x in C.STATES if gf[x] <= tr["tau_fit"]["1"]], w + "P1")
        need(la["alarm"] is bool(la["g"] > C.AD3_TAU), w + "alarm")
        one = _single(la)
        for arms, gated in ((C.LA_ARMS, True), (C.LA2_ARMS, False)):
            for a, base in arms.items():
                on = one is not None and (la["alarm"] or not gated)
                need((ks[a], src[a]) == (("bank:" + one, "lookahead") if on else
                                         (ks.get(base, "bank:" + static), "base")), w + a)
        for a, cap in CAPS.items():
            on = one is not None and la["alarm"] and "bank:" + one != ks["W0F"] and (cap is None or gf[one] <= cap)
            need((ks[a], src[a]) == (("bank:" + one, "lookahead") if on else (ks["W0F"], "base")), w + a)
        import controller as CT                        # frozen DB8 rule: CB memory is LAST_BANK
        k, sc, cb_prev = CT.cb_key(gf, tr["tau_fit"], tr["risk"], cb_prev, ks["W0F"], memory=CT.LAST_BANK)
        need((ks["CB"], src["CB"]) == (k, sc), w + "CB")


def arrays(r, raw):
    """raw: the archive bytes whose hash the caller checked against r. -> {block: {arm: bool[eval rows]}}."""
    need(R2.sha(raw) == r["archive_sha256"], "archive hash")
    n, width, out = C.EVAL_PER_BLOCK, -(-C.EVAL_PER_BLOCK // 8), {}
    with np.load(io.BytesIO(raw), allow_pickle=False) as z:
        need(set(z.files) == {f"b{t:02d}_{a}" for t in C.SCORED for a in C.ARMS}, "archive keys")
        for b in r["blocks"]:
            t, row, by = b["block"], {}, {}
            for a in C.ARMS:
                v = z[f"b{t:02d}_{a}"]
                need(v.dtype == np.uint8 and v.shape == (width,), "archive width")
                bits = np.unpackbits(v)
                need(not bits[n:].any() and int(bits.sum()) == b["errors"][a], "count mismatch")
                row[a] = bits[:n].astype(bool)
                if a in b["keys"]:
                    first = by.setdefault(b["keys"][a], row[a])
                    need(np.array_equal(first, row[a]), f"b{t:02d}: one key, two results")
            out[t] = row
    return out


def load_bound(run_dir, head, freeze_sha):
    """-> (status, [(record, arrays)]) in episode order, for exactly the approved head and freeze."""
    from pathlib import Path
    run = Path(run_dir)
    body = R2.read_reservation(run)
    want = [(s, e) for s, n in C.EPISODES.items() for e in range(n)]
    names = [f"{s}_e{e}" for s, e in want]
    need((body["head"], body["freeze_sha256"]) == (head, freeze_sha), "reservation is for another head or freeze")
    need(body["jobs"] == sorted(names), "reserved jobs")
    st = json.loads((run / "RUN_STATUS.json").read_bytes())
    need(st["state"] == "ready_for_analysis" and all(st[k] == body[k] for k in ("run_id", "head", "freeze_sha256")), "status")
    need(not any((run / f).exists() for f in ("FAILURE.json", "RECOVERY.json")), "run was closed as failed")
    need(set(st["jobs"]) == set(names) and all(j["returncode"] == 0 for j in st["jobs"].values()), "job status")
    ev, torn = R2.read_events(run / "journal.jsonl")
    need(not torn and ev[0]["event"] == "run_start" and ev[0]["run_id"] == body["run_id"] and
         ev[-1]["event"] == "run_end", "journal")
    need(Counter(x["job"] for x in ev if x["event"] == "job_done") == Counter(names), "journal jobs")
    need({x["job"] for x in ev if x["event"] == "job_retry"} == set(st["reruns"]), "journal retries")
    need({p.name for p in (run / "episodes").iterdir()} == set(names), "committed episodes")
    need(not any((run / "staging").iterdir()) and not any((run / "partial").iterdir()), "uncommitted output")
    seeds, tr, out = db8_seeds(), training(), []
    for nm, ident in zip(names, want):
        jev, jt = R2.read_events(run / "events" / f"{nm}.jsonl")
        c = [x["event"] for x in jev]
        need(not jt and c == ["started"] * (1 + (nm in st["reruns"])) + ["sampling_started", "committed"] or
             (not jt and nm in st["reruns"] and c == ["started", "sampling_started", "committed"]), f"{nm}: events")
        need(all(x.get("run_id", body["run_id"]) == body["run_id"] for x in jev), f"{nm}: event run id")
        rec, raw = R2.read_committed(run, body["run_id"], nm)
        validate_record(rec, seeds, tr, ident, extra=("run_id",))
        out.append((rec, arrays(rec, raw)))
    return st, out
