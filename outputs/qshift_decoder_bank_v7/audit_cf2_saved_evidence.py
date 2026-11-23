"""Read-only independent recount of the unsealed CF2 saved error archives."""
import ast
import hashlib
import importlib.metadata
import io
import json
import math
import platform
import subprocess
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.special import betaincinv

TARGET = "6bd35b7520736223b6ad950f342df09450c6552c"
FROZEN = "9b41acfac"
DB6 = Path("outputs/qshift_decoder_bank_v6")
CF2 = Path("outputs/qshift_decoder_bank_v7")
PANELS = dict(AA=4, AB=6, BA=6, BB=5, S1=3, S4=4, U=5, N_C=3, N_OFF=4, RX=8)
ARMS = ("W0F", "W0", "DB2", "DB2_PLAN", "BANK", "AD3", "STATIC", "ORACLE",
        "A_nominal", "LA_W0F", "LA_BANK", "LA_DB2", "LA_STATIC", "LA2_W0F")
PAIRS = {
    "C1": ("W0F", tuple(PANELS)),
    "C2": ("LA_STATIC", ("AB", "BA", "BB", "S1", "S4", "N_C", "U")),
    "C3": ("LA_BANK", ("AA", "AB", "BA", "RX")),
}
BASES = dict(LA_W0F="W0F", LA_STATIC="STATIC", LA_BANK="BANK", LA_DB2="DB2")
TEXT = {".cfg", ".csv", ".json", ".md", ".py", ".toml", ".txt"}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def blob(revision, path):
    return subprocess.check_output(["git", "cat-file", "blob", f"{revision}:{path.as_posix()}"])


def as_json(path):
    return json.loads(path.read_bytes())


def published(path):
    data = blob(TARGET, path)
    assert path.read_bytes() == data, path
    return json.loads(data)


def verified_archive(directory, name, record):
    relative = f"archives/{name}.npz"
    assert record["archive"] == relative, relative
    raw = (directory / relative).read_bytes()
    assert sha(raw) == record["archive_sha256"], name
    return np.load(io.BytesIO(raw), allow_pickle=False)


def freeze_check():
    path = CF2 / "CF2_FREEZE.json"
    fz = published(path)
    assert path.read_bytes() == blob(FROZEN, path)
    assert fz["file_count"] == len(fz["files"]) == 85
    assert fz["episodes"] == PANELS
    for rel, expected in fz["files"].items():
        path = Path(rel)
        assert path.parts[0] == "outputs" and ".." not in path.parts
        assert "work" not in path.parts and "results" not in path.parts
        assert not any(w in path.name.upper() for w in ("SEAL", "HIDDEN", "R6_"))
        for raw in (blob(FROZEN, path), blob(TARGET, path), path.read_bytes()):
            data = raw.replace(b"\r\n", b"\n") if path.suffix in TEXT else raw
            assert sha(data) == expected, path
    print("85/85 freeze hashes, both Git revisions and working bytes")
    return fz


def fidelity_check():
    for directory, evidence in [("fidelity_attempt1", "FIDELITY_ATTEMPT1.json"),
                                ("fidelity", "FIDELITY.json")]:
        manifest = published(CF2 / evidence)
        assert manifest["all_pass"] == (directory == "fidelity")
        for name, expected_uses in (("BB_e0", 2), ("U_e0", 0)):
            base, check = DB6 / "work/dev", CF2 / "work" / directory
            ref = published(DB6 / "results/dev/records" / f"{name}.json")
            actual = as_json(check / "records" / f"{name}.json")
            ignore = {"seconds", "timing", "archive_sha256"}
            assert {k: v for k, v in ref.items() if k not in ignore} == {
                k: v for k, v in actual.items() if k not in ignore}
            with verified_archive(base, name, ref) as left, verified_archive(check, name, actual) as right:
                assert len(left.files) == len(right.files) == 336
                assert set(left.files) == set(right.files)
                assert all(np.array_equal(left[k], right[k]) for k in left.files)
            uses = sum(b["source"]["LA_W0F"] == "lookahead" for b in actual["blocks"])
            assert uses == expected_uses
            item = manifest["episodes"][f"DB6 dev {name}"]
            assert item["bits"] and item["la_uses"] == uses
            assert item["pass"] == (uses > 0 or directory == "fidelity")
    print("Both archived fidelity attempts match pinned DB6 fields and arrays")


def cp_upper(k, n):
    return float(betaincinv(k + 1, n - k, .95)) if k < n else 1.0


def stats(totals, analysis):
    p_values = {}
    for h, (a, panels) in PAIRS.items():
        d = [v["LA_W0F"] - v[a] for (s, _), v in totals.items() if s in panels]
        wins, losses = sum(x < 0 for x in d), sum(x > 0 for x in d)
        nz = wins + losses
        p = sum(math.comb(nz, k) for k in range(wins, nz + 1)) / 2**nz
        draw = np.random.default_rng(20261123).integers(len(d), size=(20_000, len(d)))
        ci = np.sort(np.array(d)[draw].sum(axis=1)) / len(d)
        interval = np.interp(np.array([.025, .975]) * (ci.size - 1), np.arange(ci.size), ci)
        f = analysis["hypotheses"][h]
        assert (f["n"], f["d"], f["better"], f["worse"], f["tied"]) == (len(d), d, wins, losses, len(d) - nz)
        assert f["sign_p"] == p and np.isclose(f["mean"], np.mean(d)) and f["median"] == np.median(d)
        assert np.allclose(f["boot95_mean"], interval, rtol=0, atol=1e-12)
        p_values[h] = p
        print(h, "n/wins/losses/ties", len(d), wins, losses, len(d)-nz,
              "mean/median", np.mean(d), np.median(d), "p", p, "CI", interval.tolist())
    adjusted = {}
    for i, h in enumerate(sorted(p_values, key=p_values.get)):
        adjusted[h] = min(1, max([p_values[h] * (len(p_values)-i), *adjusted.values()]))
        assert (adjusted[h] <= .05) == analysis["hypotheses"][h]["holm_rejected"]
    print("Holm adjusted", adjusted)
    return adjusted


def seed_check(seedbook, ordered_keys):
    # Use the named historical seed metadata only, including the timing probe.
    source = Path("outputs/qshift_d5_lowp_regime_v1/prepare_dev_seeds.py")
    names = {"INVENTORIES", "EXTRA_SCREENED"}
    constants = {
        n.targets[0].id: ast.literal_eval(n.value)
        for n in ast.parse(blob(TARGET, source)).body
        if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and n.targets[0].id in names
    }
    default = ("seeds", "rehearsal_seeds")
    sources = {name: default for name in constants["INVENTORIES"]}
    sources["outputs/qshift_d5_model_mismatch_v1/SEEDS.json"] = (*default, "diag_seeds")
    for stem in ("DEV", "EVAL"):
        sources[f"outputs/qshift_d5_lowp_regime_v1/{stem}_SEEDS.json"] = default
    for stem in ("DEV2", "RE1", "RE2", "BRE", "BRS", "BRT", "AD1", "AD2", "AD3"):
        sources[f"outputs/qshift_adaptive_robust_v1/{stem}_SEEDS.json"] = (
            (*default, "screen_seeds") if stem == "AD3" else default
        )
    for i, stem in enumerate(("DB1", "DB2", "DB3", "DB4", "CF1", "DB6"), start=1):
        sources[f"outputs/qshift_decoder_bank_v{i}/{stem}_SEEDS.json"] = (
            ("seeds", "train_seeds") if i == 1 else ("seeds",)
        )
    assert set(seedbook["screened"]) == set(sources) and len(sources) == 34
    historical = set(constants["EXTRA_SCREENED"])
    for rel, fields in sources.items():
        raw = blob(TARGET, Path(rel))
        info = seedbook["screened"][rel]
        if "sha256" in info:
            assert sha(raw) == info["sha256"], rel
        data = json.loads(raw)
        nums = set().union(*(data.get(field, {}).values() for field in fields))
        assert all(type(n) is int for n in nums) and len(nums) == info["values"], rel
        historical.update(nums)
    assert len(historical) == seedbook["union_screened"]
    seeds = seedbook["seeds"]
    assert not historical.intersection(seeds.values())
    used = set(historical)
    collision_steps = 0
    for key in ordered_keys:
        counter = 0
        while True:
            digest = hashlib.sha256(f"{seedbook['namespace']}:{key}:{counter}".encode()).digest()
            value = int.from_bytes(digest[:8], "big") % (2**31 - 1) + 1
            if value not in used:
                break
            counter += 1
        assert value == seeds[key], key
        used.add(value)
        collision_steps += counter
    print("Seed identifiers", len(seeds), "historical union", len(historical), "collision steps", collision_steps)


def recount(fz):
    pairs = [(s, e) for s, n in PANELS.items() for e in range(n)]
    names = {f"{s}_e{e}" for s, e in pairs}
    run, result = CF2 / "work/cf2", CF2 / "results/cf2"
    st = published(result / "RUN_STATUS.json")
    assert as_json(run / "RUN_STATUS.json") == st and st["head"].startswith(FROZEN)
    assert st["state"] == "ready_for_analysis" and st["n_jobs"] == 48 and not st["reruns"]
    assert st["environment"] == fz["environment"]
    assert st["jobs"] == {name: {"returncode": 0} for name in names}
    for path, suffix in [(result / "records", ".json"), (run / "records", ".json"), (run / "archives", ".npz")]:
        assert {p.stem for p in path.glob("*"+suffix)} == names
    analysis = published(result / "ANALYSIS.json")
    timeline = published(result / "TIMELINE.json")
    seedbook = published(CF2 / "CF2_SEEDS.json")
    seeds = seedbook["seeds"]
    def key(s,e,t,part):
        return f"cf2:{s}:e{e}:b{t:02d}:{part}"
    all_keys = [f"cf2:params:{s}:e{e}" for s,e in pairs]
    all_keys.extend(key(s,e,t,p) for s,e in pairs for t in range(30) for p in ("det","lab","eval"))
    assert set(seeds) == set(all_keys) and len(set(seeds.values())) == len(all_keys) == 4368
    seed_check(seedbook, all_keys)

    totals = {}
    triggers, wrong, paired, fallback, onset = Counter(), [], Counter(), Counter(), {}
    no_onset = Counter()
    block_max = -math.inf
    for s, e in pairs:
        name = f"{s}_e{e}"
        path = result / "records" / f"{name}.json"
        r = published(path)
        assert (run / "records" / path.name).read_bytes() == path.read_bytes()
        assert (r["schedule"], r["episode"], r["mode"], r["eval_per_block"]) == (s,e,"cf2",1000)
        assert r["arms"] == list(ARMS) and len(r["states"]) == 30
        assert [b["block"] for b in r["blocks"]] == list(range(6,30))
        used = {f"b{t:02d}:{p}": seeds[key(s,e,t,p)] for t in range(30) for p in ("det","lab","eval")
                if p != "eval" or t >= 6}
        assert r["seeds"] == used
        tline = timeline["schedules"][s]
        assert tline["state"][e] == [b["state"] for b in r["blocks"]]
        assert tline["lookahead"][e] == [b["lookahead"] for b in r["blocks"]]
        assert all(tline["keys"][a][e] == [b["keys"][a] for b in r["blocks"]] for a in tline["keys"])
        err = Counter()
        with verified_archive(run, name, r) as z:
            want = {f"b{t:02}_{a}" for t in range(6,30) for a in ARMS}
            assert len(z.files) == len(want) and set(z.files) == want
            for b in r["blocks"]:
                t, state = b["block"], b["state"]
                assert state == r["states"][t] and b["keys"]["ORACLE"] == f"bank:{state}"
                cnt, bits = {}, {}
                for a in ARMS:
                    val = z[f"b{t:02}_{a}"]
                    assert val.dtype == np.uint8 and val.shape == (125,)
                    bits[a] = np.unpackbits(val).astype(bool)
                    cnt[a] = int(bits[a].sum())
                    assert cnt[a] == b["errors"][a] == tline["errors"][a][e][t-6]
                err.update(cnt)
                la = b["lookahead"]
                fired = bool(la["alarm"] and len(la["P1"]) == 1)
                for overlay, base in BASES.items():
                    assert b["source"][overlay] == ("lookahead" if fired else "base")
                    assert b["keys"][overlay] == (f"bank:{la['P1'][0]}" if fired else b["keys"][base])
                    if b["keys"][overlay] == b["keys"][base]:
                        assert np.array_equal(bits[overlay], bits[base])
                assert b["keys"]["LA2_W0F"] == (f"bank:{la['P1'][0]}" if len(la["P1"]) == 1 else b["keys"]["W0F"])
                saved = cnt["W0F"] - cnt["LA_W0F"]
                block_max = max(block_max, -saved)
                correct = fired and b["keys"]["LA_W0F"] == f"bank:{state}"
                if fired:
                    triggers.update((s,))
                    if not correct or s == "U":
                        wrong.append((name,t,state,b["keys"]["LA_W0F"],b["keys"]["W0F"],saved))
                    paired["key_changes"] += b["keys"]["LA_W0F"] != b["keys"]["W0F"]
                if state != r["states"][t-1]:
                    row = onset.setdefault(state, Counter())
                    row["opportunities"] += 1
                elif fired:
                    row = no_onset
                else:
                    row = None
                if row is not None:
                    row["triggers"] += fired
                    row["correct"] += correct
                    row["saved_vs_W0F"] += saved
                for counter, a, c in [(paired,"LA_W0F","W0F"), (fallback,"W0F","W0")]:
                    counter["wins"] += int((~bits[a] & bits[c]).sum())
                    counter["losses"] += int((bits[a] & ~bits[c]).sum())
        for a in ARMS:
            assert err[a] == analysis["schedules"][s]["errors_per_episode"][a][e]
        totals[s,e] = err
    pooled = {a: sum(v[a] for v in totals.values()) for a in ARMS}
    assert pooled == analysis["pooled_errors"]
    assert analysis["reported"]["onsets"] == {"by_destination": onset, "non_opportunity_triggers": no_onset}
    adjusted = stats(totals,analysis)
    d = {k:v["LA_W0F"]-v["W0F"] for k,v in totals.items()}
    rx, u = ([v for (s,_),v in d.items() if s == panel] for panel in ("RX","U"))
    g3, uses = sum(v > 0 for v in d.values()), sum(triggers.values())
    g4 = cp_upper(len(wrong),uses)
    assert math.isclose(g4,analysis["gates"]["G4_wrong_cp_upper"])
    assert math.isclose(cp_upper(g3,48),analysis["gates"]["G3_harm_cp_upper"])
    dec = dict(C1=adjusted["C1"]<=.05 and np.mean(list(d.values()))<=-3,
               G1=max(d.values())<=24, G2=block_max<=24, G3=g3<=2, G4=0<uses and g4<=.05,
               G5=sum(rx)<=0 and max(rx)<=12, G6=sum(u)<=0 and max(u)<=12)
    dec["CONFIRMED"] = all(dec.values())
    dec.update({h: dec["CONFIRMED"] and adjusted[h]<=.05 for h in ("C2","C3")})
    assert dec == analysis["decision"]
    print("48 archives, 1,152,000 rows, 16,128 error arrays, 4,032 block-seed mappings")
    print("Error totals", pooled)
    print("Uses by panel", triggers, "wrong", wrong, "G4", g4, "G3", cp_upper(g3,48))
    print("Paired C1", paired, "underlying fallback", fallback, "onsets", onset, no_onset)
    print("G1/G2 max", max(d.values()), block_max, "G5 RX", rx, "G6 U", u, "gates", dec)
    print("Minimum IID CP denominators at 0/1/2/3 events",
          [next(n for n in range(k+1,200) if cp_upper(k,n)<=.05) for k in range(4)])


if __name__ == "__main__":
    if not __debug__:
        raise RuntimeError("Audit assertions must be enabled")
    if len(sys.argv) != 1:
        raise SystemExit("Run from the source repository root without arguments")
    fz = freeze_check()
    print("Freeze and status environment", fz["environment"], "audit Python", platform.python_version(),
          "audit distributions", {k: importlib.metadata.version(k) for k in ("numpy","scipy","ldpc")})
    fidelity_check()
    recount(fz)
