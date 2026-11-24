"""Read-only DB8 audit. Failed-attempt payloads are hashed, never decoded."""
import ast
import hashlib
import io
import json
import math
import subprocess
from collections import Counter
from pathlib import Path

import numpy as np

TARGET = "2e4ef30e0e2cbe7c42b742244f9753c6c5a7dfbd"
EVIDENCE = "1e3c26e06509b3192e898f81dcba7821aad97654"
P = Path("outputs/qshift_decoder_bank_v9")
W6 = Path("outputs/qshift_decoder_bank_v6")
RUN = P / "work/dev_a3"
RES = P / "results/dev"
FREEZES = {"DB8_FREEZE.json": "7d2aec31a", "DB8_FREEZE_A2.json": "6931cb43d",
           "DB8_FREEZE_A2b.json": "7680b3e5d", "DB8_FREEZE_A2c.json": "48161c830",
           "DB8_FREEZE_A3.json": "7ac49b16c"}
PANELS = dict(AA=2, AB=3, BA=3, BB=3, S1=2, S4=2, N_C=2, N_OFF=2, RX=5,
              U_E=8, U_FAR=12, U_OUT=12, U_NEAR=8)
ARMS = ("W0F", "W0", "DB2", "DB2_PLAN", "BANK", "AD3", "STATIC", "ORACLE", "A_nominal",
        "LA_W0F", "LA_BANK", "LA_DB2", "LA_STATIC", "LA2_W0F",
        "LA_R1", "LA_R2", "LA_R2_170", "CB", "FIX_OFF", "FIX_A", "FIX_B", "FIX_C", "FIX_D")
CASES = (("LA_R1", None), ("LA_R2", 180), ("LA_R2_170", 170))
PAIRS = [(s, e) for s, count in PANELS.items() for e in range(count)]
SCORED = tuple(range(6, 30))
TEXT = {".py", ".json", ".md", ".txt", ".csv", ".toml", ".cfg"}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def git(*args, data=None):
    return subprocess.check_output(["git", *args], input=data)


def pinned(path, rev=TARGET):
    return git("cat-file", "blob", f"{rev}:{path.as_posix()}")


def same(path, rev=TARGET):
    data = pinned(path, rev)
    assert data == path.read_bytes(), path
    return json.loads(data)


def batch(rev, paths):
    req = "".join(f"{rev}:{p}\n" for p in paths)
    stream = io.BytesIO(git("cat-file", "--batch", data=req.encode()))
    for p in paths:
        _, kind, length = stream.readline().split()
        assert kind == b"blob", p
        data = stream.read(int(length))
        assert stream.read(1) == b"\n", p
        yield p, data
    assert not stream.read(1)


def freezes():
    sha_list = {}
    for name, revision in FREEZES.items():
        freeze = same(P / name, revision)
        assert freeze["episodes"] == PANELS
        assert int(freeze["file_count"]) == len(freeze["files"])
        assert git("rev-parse", revision+"^").decode().strip() == freeze["code_head"]
        assert git("diff", "--name-only", revision+"^", revision).decode().strip() == (P / name).as_posix()
        for rel in freeze["files"]:
            assert rel.startswith("outputs/") and "/work/" not in rel
            assert ".." not in Path(rel).parts and not any(x in Path(rel).name.upper() for x in ("SEAL", "HIDDEN"))
        for rel, data in batch(revision, freeze["files"]):
            data = data.replace(b"\r\n", b"\n") if Path(rel).suffix in TEXT else data
            assert sha(data) == freeze["files"][rel], (revision, rel)
            if name == "DB8_FREEZE_A3.json":
                sha_list[rel] = sha(data)
        print(name, revision, freeze["file_count"], "hashes")
    diffs = []
    for rel, data in batch(TARGET, sha_list):
        data = data.replace(b"\r\n", b"\n") if Path(rel).suffix in TEXT else data
        if sha(data) != sha_list[rel]:
            diffs.append(rel)
    assert diffs == [(P/"db8_analyze.py").as_posix(), (P/"tests/test_db8.py").as_posix()], diffs
    print("Final freeze vs result expected post-run changes", diffs)


def inventory():
    book = same(P/"EVIDENCE_MANIFEST.json", EVIDENCE)
    assert book["base_commit"] == TARGET
    allowed = ["work/dev/", "work/dev_a2/", "work/dev_a3/", "work/fidelity/"]
    found = Counter()
    for rel, item in book["files"].items():
        assert ".." not in Path(rel).parts and any(rel.startswith(v) for v in allowed)
        data = (P/rel).read_bytes()
        assert len(data) == item["bytes"] and sha(data) == item["sha256"], rel
        found["/".join(rel.split("/")[:2])] += 1
    assert sum(found.values()) == book["file_count"] == 204
    for folder in allowed:
        assert {x.relative_to(P).as_posix() for x in (P/folder).rglob("*") if x.is_file()} == {
            rel for rel in book["files"] if rel.startswith(folder)
        }
    for number, run, leaf, field, count in [
        (1, "dev", "PARTIALS.json", "partials", 7),
        (2, "dev_a2", "OUTPUTS.json", "outputs", 56),
    ]:
        p = P/f"RUN_ATTEMPT{number}"
        payload = same(p/leaf)
        assert len(payload[field]) == count
        for rel, item in payload[field].items():
            assert book["files"][f"work/{run}/{rel}"] == item
        for meta in ("RUN_STATUS.json", "journal.jsonl"):
            assert pinned(p/meta) == (P/"work"/run/meta).read_bytes()
        lock = json.loads((P/"work"/run/"RUN.lock").read_bytes())
        assert all(lock[k] == v for k,v in payload["lock"].items())
    old1 = [m["sha256"] for rel,m in book["files"].items() if rel.startswith("work/dev/partial/")]
    full = {m["sha256"] for rel,m in book["files"].items() if rel.startswith("work/dev_a3/archives/")}
    old2 = [m["sha256"] for rel,m in book["files"].items() if rel.startswith("work/dev_a2/archives/")]
    print("Evidence inventory", dict(found), "old archive byte matches vs final",
          sum(h in full for h in old1), sum(h in full for h in old2))


def load_archive(base, rec):
    raw = (base/rec["archive"]).read_bytes()
    assert sha(raw) == rec["archive_sha256"]
    return np.load(io.BytesIO(raw), allow_pickle=False)


def fidelity():
    v6_arms = ARMS[:14]
    for subject in ("BB_e0", "U_e0"):
        original = same(W6/"results/dev/records"/f"{subject}.json")
        replay = json.loads((P/"work/fidelity/records"/f"{subject}.json").read_bytes())
        assert original["archive"] == replay["archive"] == f"archives/{subject}.npz"
        for k, v in original.items():
            if k not in ("arms", "blocks", "archive_sha256", "timing", "seconds", "mode"):
                assert v == replay[k], (subject,k)
        assert original["mode"] == "dev" and replay["mode"] == "fidelity"
        with load_archive(W6/"work/dev", original) as a, load_archive(P/"work/fidelity", replay) as b:
            assert len(a.files) == 336
            assert all(np.array_equal(a[k], b[k]) for k in a.files)
        for a,b in zip(original["blocks"], replay["blocks"], strict=True):
            for k,v in a.items():
                if k in ("keys","errors","source","acceptable","burst_action"):
                    assert v == {n: y for n,y in b[k].items() if n in v6_arms}
                else:
                    assert v == b[k]
        print("Saved fidelity match", subject, "LA_R2 uses",
              sum(b["source"]["LA_R2"] == "lookahead" for b in replay["blocks"]))


def seeds():
    manifest = same(P/"DB8_SEEDS.json")
    names = {"INVENTORIES", "EXTRA_SCREENED"}
    code = ast.parse(pinned(Path("outputs/qshift_d5_lowp_regime_v1/prepare_dev_seeds.py")))
    constants = {n.targets[0].id: ast.literal_eval(n.value) for n in code.body
                 if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and n.targets[0].id in names}
    fields = ("seeds", "rehearsal_seeds")
    sources = dict.fromkeys(constants["INVENTORIES"], fields)
    sources["outputs/qshift_d5_model_mismatch_v1/SEEDS.json"] = (*fields, "diag_seeds")
    for stem in ("DEV", "EVAL"):
        sources[f"outputs/qshift_d5_lowp_regime_v1/{stem}_SEEDS.json"] = fields
    for stem in ("DEV2", "RE1", "RE2", "BRE", "BRS", "BRT", "AD1", "AD2", "AD3"):
        sources[f"outputs/qshift_adaptive_robust_v1/{stem}_SEEDS.json"] = (
            (*fields, "screen_seeds") if stem == "AD3" else fields)
    for i, stem in enumerate(("DB1", "DB2", "DB3", "DB4", "CF1", "DB6", "CF2"), start=1):
        sources[f"outputs/qshift_decoder_bank_v{i}/{stem}_SEEDS.json"] = (
            ("seeds", "train_seeds") if i == 1 else ("seeds",))
    assert len(sources) == 35 and set(sources) == set(manifest["screened"])
    old = set(constants["EXTRA_SCREENED"])
    for path, raw in batch(TARGET, sources):
        item = manifest["screened"][path]
        if "sha256" in item:
            assert sha(raw) == item["sha256"], path
        b = json.loads(raw)
        ns = set().union(*(b.get(f, {}).values() for f in sources[path]))
        assert all(type(i) is int for i in ns) and len(ns) == item["values"], path
        old.update(ns)
    assert len(old) == manifest["union_screened"]
    new = manifest["seeds"]
    assert len(new) == len(set(new.values())) == 5824 and not old.intersection(new.values())
    labels = [f"db8:params:{s}:e{e}" for s,e in PAIRS]+[
        f"db8:{s}:e{e}:b{t:02}:{p}" for s,e in PAIRS for t in range(30) for p in ("det","lab","eval")]
    assert set(labels) == set(new)
    used = set(old)
    bumps = 0
    for label in labels:
        k = 0
        while True:
            buf = f"{manifest['namespace']}:{label}:{k}".encode()
            x = int.from_bytes(hashlib.sha256(buf).digest()[:8],"big")%(2**31-1)+1
            if x not in used:
                break
            k += 1
        assert x == new[label]
        used.add(x)
        bumps += k
    print("Predeclared seed derivation", len(new), len(old), bumps)
    return new


def recount(seedbook):
    analysis = same(RES/"ANALYSIS.json")
    st = same(RES/"RUN_STATUS.json")
    assert st["state"] == "ready_for_analysis" and st["n_jobs"] == 64 and not st["reruns"]
    names = {f"{s}_e{e}": {"returncode": 0} for s,e in PAIRS}
    assert st["jobs"] == names
    log = pinned(RES/"journal.jsonl")
    assert log == (RUN/"journal.jsonl").read_bytes()
    assert pinned(RES/"RUN_STATUS.json") == (RUN/"RUN_STATUS.json").read_bytes()
    events = [json.loads(line) for line in log.splitlines()]
    assert Counter(e["event"] for e in events) == dict(run_start=1, run_end=1, job_wait=64, job_done=64)
    assert Counter(e["job"] for e in events if e["event"]=="job_done") == {k:1 for k in names}
    assert events[0]["t"] == st["started"] and events[-1]["t"] == st["finished"]
    lock = json.loads((RUN/"RUN.lock").read_bytes())
    assert lock["head"] == git("rev-parse","7ac49b16c").decode().strip()
    assert lock["reserved"] == st["started"]
    training = same(Path("outputs/qshift_decoder_bank_v1/TRAINING.json"))
    tau, risk = training["tau_fit"]["1"], training["risk"]
    states = ("OFF","A","B","C","D")
    for p,sfx in ((RES/"records","json"),(RUN/"records","json"),(RUN/"archives","npz")):
        assert {n.stem for n in p.glob(f"*.{sfx}")} == set(names)
    per, pooled, harmful = {}, Counter(), Counter()
    onset_summary = Counter()
    pre_onset_a = Counter()
    cb_change_rows, cb_last_emitted_errors = 0, 0
    near = []
    for (s,e), item in zip(PAIRS, analysis["episodes"], strict=True):
        name=f"{s}_e{e}"
        f=RES/"records"/f"{name}.json"
        r=same(f)
        assert f.read_bytes()==(RUN/"records"/f.name).read_bytes()
        assert (r["schedule"],r["episode"],r["mode"],r["eval_per_block"])==(s,e,"db8",1000)
        assert r["arms"]==list(ARMS) and r["archive"]==f"archives/{name}.npz" and len(r["states"])==30
        expect={f"b{t:02}:{p}":seedbook[f"db8:{s}:e{e}:b{t:02}:{p}"] for t in range(30)
                for p in ("det","lab","eval") if p!="eval" or t>=6}
        assert r["seeds"]==expect
        assert [b["block"] for b in r["blocks"]]==list(SCORED)
        if s.startswith("U_"):
            onset=int(np.random.default_rng(seedbook[f"db8:params:{s}:e{e}"]).integers(8,13))
            assert r["params"]=={"onset":onset} and r["true_changes"]==[onset]
            st_true={"U_E":"E","U_NEAR":"UN","U_FAR":"UF","U_OUT":"UO"}[s]
            assert r["states"]==["A"]*onset+[st_true]*(30-onset)
        totals, fires, wrong, shot, maxblock=Counter(),Counter(),Counter(),Counter(),{}
        prev=training["static_key"]
        cb_alt_prev=prev
        with load_archive(RUN,r) as z:
            assert set(z.files)=={f"b{t:02}_{a}" for t in SCORED for a in ARMS} and len(z.files)==24*len(ARMS)
            for b in r["blocks"]:
                t=b["block"]
                assert b["state"]==r["states"][t]
                bit={}
                bykey={}
                for a in ARMS:
                    v=z[f"b{t:02}_{a}"]
                    assert v.dtype==np.uint8 and v.shape==(125,)
                    bit[a]=np.unpackbits(v).astype(bool)
                    n=int(bit[a].sum())
                    assert n==b["errors"][a]
                    totals[a]+=n
                    if a in b["keys"]:
                        k=b["keys"][a]
                        if k in bykey:
                            assert np.array_equal(bit[a],bykey[k])
                        bykey[k]=bit[a]
                    if a in item["shot_harm"]:
                        shot[a]+=int((bit[a] & ~bit["W0F"]).sum())
                    if a in item["block_harm"]:
                        maxblock[a]=max(maxblock.get(a,-1001),n-b["errors"]["W0F"])
                gf, la, ks, src=b["db8"]["gf1"], b["lookahead"], b["keys"], b["source"]
                ps=[k for k in states if gf[k]<=tau]
                assert all(math.isfinite(gf[k]) for k in states)
                assert ps==la["P1"] and bool(la["g"]>163.13055125732944)==la["alarm"]
                for a,cap in CASES:
                    active=la["alarm"] and len(ps)==1 and ks["W0F"]!="bank:"+ps[0] and (cap is None or gf[ps[0]]<=cap)
                    expected="bank:"+ps[0] if active else ks["W0F"]
                    assert ks[a]==expected and src[a]==("lookahead" if active else "base")
                    fires[a]+=active
                    wrong[a]+=active and expected!="bank:"+b["state"]
                if ps:
                    worst={a:max(risk[x][a] for x in ps) for a in states}
                    best=min(states,key=worst.get)
                    prev=prev if worst[prev]<=worst[best]+.0005 else best
                    assert ks["CB"]=="bank:"+prev and src["CB"]=="cb"
                else:
                    assert ks["CB"]==ks["W0F"] and src["CB"]=="w0f"
                if ps:
                    candidate=(cb_alt_prev if cb_alt_prev in worst and
                               worst[cb_alt_prev]<=worst[best]+.0005 else best)
                    cb_alt_key="bank:"+candidate
                    cb_alt_err=b["errors"]["FIX_"+candidate]
                else:
                    cb_alt_key,cb_alt_err=ks["W0F"],b["errors"]["W0F"]
                cb_alt_prev=cb_alt_key[5:] if cb_alt_key.startswith("bank:") else None
                cb_change_rows+=cb_alt_key!=ks["CB"]
                cb_last_emitted_errors+=cb_alt_err
                active=la["alarm"] and len(ps)==1
                assert src["LA_W0F"]==("lookahead" if active else "base")
                assert ks["LA_W0F"]==("bank:"+ps[0] if active else ks["W0F"])
                wrong["LA_W0F"]+=active and ks["LA_W0F"]!="bank:"+b["state"]
                fires["LA_W0F"]+=active
                for a in ("LA_W0F","LA_R1","LA_R2","LA_R2_170"):
                    if src[a]=="lookahead":
                        changed=ks[a]!=ks["W0F"]
                        onset_summary[a,b["state"]!=r["states"][t-1],changed]+=1
                        if s.startswith("U_") and b["state"]=="A" and ks[a]=="bank:A":
                            pre_onset_a[s,a]+=1
                if s=="U_NEAR" and t==onset:
                    near.append((name,t,la["g"],gf["B"],ks["W0F"],ks["LA_R2"],ks["LA_R2_170"],
                                 b["errors"]["LA_R2"]-b["errors"]["W0F"]))
        assert item["errors"]==totals and item["fires"]==fires and item["shot_harm"]==shot
        assert item["block_harm"]==maxblock and item["wrong_ident_LA_W0F"]==wrong.pop("LA_W0F")
        assert item["wrong_actions"]==wrong
        pooled.update(totals)
        harmful.update(shot)
        per[s,e]=(totals,wrong,maxblock)
    assert pooled==analysis["pooled_errors"] and harmful==analysis["reported"]["shot_harm"]
    print("64 archives, 1,536 scored blocks, 1,536,000 paired rows and 5,376 used seed IDs; totals",dict(pooled))
    print("U_NEAR onset tuples",near, "shot harm",dict(harmful))
    print("Reported CB vs last-emitted CB sensitivity", pooled["CB"], cb_last_emitted_errors, cb_change_rows)
    print("Lookahead counts by (arm, is true onset, key changes)", dict(onset_summary))
    print("Unknown-panel pre-onset correct-state firings", dict(pre_onset_a))
    for a,which in (("LA_R2","primary"),("LA_R2_170","secondary")):
        f=analysis[which]
        i=[r for (s,e),r in per.items() if not s.startswith("U_")]
        gap=sum(r[0]["W0F"]-r[0]["LA_W0F"] for r in i)
        d=[r[0][a]-r[0]["W0F"] for r in i]
        wins,loss=sum(x<0 for x in d),sum(x>0 for x in d)
        p=sum(math.comb(wins+loss,j) for j in range(wins,wins+loss+1))/2**(wins+loss)
        unknown={s:[r[0][a]-r[0]["W0F"] for (ss,e),r in per.items() if ss==s]
                 for s in PANELS if s.startswith("U_")}
        count=lambda arm:sum(r[1][arm]>0 for (s,e),r in per.items() if s in ("U_FAR","U_OUT"))
        maxep=max(r[0][a]-r[0]["W0F"] for r in per.values())
        maxb=max(r[2][a] for r in per.values())
        expected={
          "A1":dict(retention=-sum(d)/gap,sign_p=p,better=wins,worse=loss,tied=len(i)-wins-loss,
                    **{"pass":-sum(d)/gap>=.90 and p<=.05}),
          "A2":dict(episodes=24,wrong_action_episodes=count(a),LA_R1_wrong_action_episodes=count("LA_R1"),
                    **{"pass":count(a)<=min(2,count("LA_R1"))}),
          "A3":dict(max_episode=maxep,max_block=maxb,unknown={s:dict(d=x,pooled=sum(x)) for s,x in unknown.items()},
                    **{"pass":maxep<=24 and maxb<=24 and all(sum(x)<=0 and max(x)<=12 for x in unknown.values())}),
          "A4":dict(pooled={k:pooled[k] for k in (a,"CB","LA_DB2")},**{"pass":pooled[a]<=min(pooled["CB"],pooled["LA_DB2"])})}
        expected["ADVANCE"]=all(x["pass"] for x in expected.values())
        assert expected==f
        print(a,"in-bank gain numerator/denominator",-sum(d),gap,expected)
    assert analysis["decision"]==dict(ADVANCE=False,arm_for_CF3_plan=None,CB_has_fewer_errors_than_LA_R2=False)
    print("NO ADVANCE independently reproduced")


if __name__=="__main__":
    if not __debug__:
        raise RuntimeError("Assertions required")
    freezes()
    inventory()
    fidelity()
    recount(seeds())
