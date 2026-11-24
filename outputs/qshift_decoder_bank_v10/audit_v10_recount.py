"""Recompute the v10 addendum from committed v9 summaries only. Run at the Git root."""
from collections import Counter
import io
import json
import subprocess

V9 = "2e4ef30e0e2cbe7c42b742244f9753c6c5a7dfbd"
V10 = "9b95923f285019e10b3a35208dd0dd64ddd37ab1"
P9 = "outputs/qshift_decoder_bank_v9"
ARMS = ("LA_W0F", "LA_R1", "LA_R2", "LA_R2_170")
OUTSIDE = ("U_E", "U_FAR", "U_OUT", "U_NEAR")
BANK = ("OFF", "A", "B", "C", "D")
COUNTS = dict(AA=2, AB=3, BA=3, BB=3, S1=2, S4=2, N_C=2, N_OFF=2, RX=5,
              U_E=8, U_FAR=12, U_OUT=12, U_NEAR=8)


def git(*args, data=None):
    return subprocess.check_output(["git", *args], input=data)


def records():
    ids = [(s, e) for s, n in COUNTS.items() for e in range(n)]
    samples = [f"{V9}:{P9}/results/dev/records/{s}_e{e}.json" for s, e in ids]
    raw = io.BytesIO(git("cat-file", "--batch", data=("\n".join(samples) + "\n").encode()))
    for s, e in ids:
        _, typ, size = raw.readline().split()
        assert typ == b"blob"
        r = json.loads(raw.read(int(size)))
        assert raw.read(1) == b"\n" and (r["schedule"], r["episode"]) == (s, e)
        assert [b["block"] for b in r["blocks"]] == list(range(6, 30))
        yield r
    assert not raw.read(1)


def cb_choice(b, previous, training):
    choices = [s for s in BANK if b["db8"]["gf1"][s] <= training["tau_fit"]["1"]]
    if not choices:
        return b["keys"]["W0F"], b["errors"]["W0F"], False
    costs = {k: max(training["risk"][s][k] for s in choices) for k in BANK}
    best = min(BANK, key=costs.__getitem__)
    if previous in costs and costs[previous] <= costs[best] + .0005:
        best = previous
    return f"bank:{best}", b["errors"][f"FIX_{best}"], True


def recompute():
    training = json.loads(git("cat-file", "blob",
                         f"{V9}:outputs/qshift_decoder_bank_v1/TRAINING.json"))
    opportunities, tallies, out_counts, cb, near = Counter(), Counter(), Counter(), Counter(), []
    for r in records():
        prev = {m: r["static_key"] for m in ("last_bank", "last_emitted")}
        for b in r["blocks"]:
            t, state = b["block"], b["state"]
            assert r["states"][t] == state
            transition = state != r["states"][t - 1]
            dest = state if transition else "non_onset"
            if transition:
                opportunities[state] += 1
            wkey, errors = b["keys"]["W0F"], b["errors"]
            for arm in ARMS:
                if b["source"][arm] != "lookahead":
                    continue
                key = b["keys"][arm]
                changed = key != wkey
                right = key == "bank:" + state
                cell = (arm, dest, "changed" if changed else "no_op")
                tallies[cell + ("firings",)] += 1
                tallies[cell + ("correct",)] += int(right)
                tallies[cell + ("saved_vs_W0F",)] += errors["W0F"] - errors[arm]
                if r["schedule"] in OUTSIDE:
                    p = (arm, r["schedule"])
                    out_counts[p + ("firings",)] += 1
                    out_counts[p + ("wrong_by_panel_wording",)] += 1
                    out_counts[p + ("wrong_by_block_truth",)] += int(not right)
                    out_counts[p + ("key_changing_wrong",)] += int(changed and not right)
            for mode in prev:
                key, loss, is_bank_fit = cb_choice(b, prev[mode], training)
                if is_bank_fit or mode == "last_emitted":
                    prev[mode] = key[5:] if key.startswith("bank:") else None
                cb[mode, "pooled_errors"] += loss
                cb[mode, "keys_different_from_frozen"] += int(key != b["keys"]["CB"])
            if r["schedule"] == "U_NEAR" and transition:
                near.append({"episode": r["episode"], "block": t, "alarm_g": round(b["lookahead"]["g"], 2),
                             "fit_B": round(b["db8"]["gf1"]["B"], 3),
                             "keys": {a: b["keys"][a] for a in ("W0F", *ARMS[1:])},
                             "excess_vs_W0F": {a: errors[a] - errors["W0F"] for a in ARMS[1:]}})

    def split(arm, dest):
        return {side: {metric: tallies[arm, dest, side, metric]
                       for metric in ("firings", "correct", "saved_vs_W0F")}
                for side in ("changed", "no_op")}

    return {
        "schema": "qshift-decoder-bank-v10-db8-addendum-v1",
        "status": "descriptive; DB8 NO ADVANCE unchanged",
        "onset_opportunities": dict(opportunities),
        "onset_table": {arm: {
            "by_destination": {k: split(arm, k) for k in opportunities
                               if sum(tallies[arm, k, s, "firings"] for s in ("changed", "no_op"))},
            "non_onset": split(arm, "non_onset")} for arm in ARMS},
        "unknown_panels": {a: {s: {f: out_counts[a, s, f] for f in (
            "firings", "wrong_by_block_truth", "wrong_by_panel_wording", "key_changing_wrong")}
            for s in OUTSIDE} for a in ARMS},
        "U_NEAR_onsets": near,
        "cb_memory_sensitivity": {m: {f: cb[m, f]
            for f in ("pooled_errors", "keys_different_from_frozen")} for m in ("last_bank", "last_emitted")},
    }


if __name__ == "__main__":
    if not __debug__:
        raise RuntimeError("Run with assertions enabled")
    expected = git("cat-file", "blob",
                   f"{V10}:outputs/qshift_decoder_bank_v10/DB8_ADDENDUM.json")
    observed = recompute()
    assert (json.dumps(observed, indent=1, sort_keys=True) + "\n").encode() == expected
    print("Byte-identical addendum from 64 pinned v9 records. CB", observed["cb_memory_sensitivity"])
