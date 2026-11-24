"""v11 study binding with admission before success (Codex v11 review, P0-B). Derived from study11.py; v11 is unchanged.

Binding of a run to verified bytes, and admission to analysis (v10 review, blocker 3).

A freeze is a JSON file committed alone, directly above its code commit:
  {"schema", "code_head", "runtime", "files": {path: sha256}, "training", "seeds", "reserved_seeds", "episodes", "workers"}

Nothing that identifies a run is taken from the caller. HEAD comes from git, hashes from git blobs and from the working
files, versions from the interpreter. `approved_head` at launch can only refuse, never authorise.
Trust root: the freeze commit the owner approved. Whoever can rewrite the repository or the run folder consistently can
still forge a run; there are no signatures."""
from __future__ import annotations

import io
import subprocess
import sys
from pathlib import Path

import db8_config as C  # noqa: I001
import lifecycle11p0 as LC
import policy as P
import runkit as RK
from strict import check_inventory, jbytes, loads, need, sha

TEXT = {".py", ".json", ".md", ".txt", ".csv", ".toml", ".cfg"}
FIELDS = {"schema", "code_head", "runtime", "files", "training", "seeds", "reserved_seeds", "episodes", "workers"}
SEED_FIELDS = ("seeds", "rehearsal_seeds", "diag_seeds", "train_seeds", "screen_seeds")
SCHEMA = "qshift-v11-freeze-1"


def norm(rel, data):
    return sha(data.replace(b"\r\n", b"\n") if Path(rel).suffix in TEXT else data)


def job_names(episodes):
    return [f"{s}_e{e}" for s, n in episodes.items() for e in range(n)]


class Study:
    def __init__(self, repo, freeze_rel):
        self.repo, self.rel = Path(repo).resolve(), freeze_rel

    def git(self, *args):
        p = subprocess.run(["git", "--no-replace-objects", "-C", str(self.repo), *args], capture_output=True)
        need(p.returncode == 0, f"git {args[0]} failed")
        return p.stdout

    def blobs(self, head, rels):
        """{path: bytes} of committed files, through one git process."""
        rels = list(rels)
        need(all("\n" not in r for r in rels), "path")
        p = subprocess.run(["git", "--no-replace-objects", "-C", str(self.repo), "cat-file", "--batch"],
                           input="".join(f"{head}:{r}\n" for r in rels).encode(), capture_output=True)
        need(p.returncode == 0, "git cat-file failed")
        f, out = io.BytesIO(p.stdout), {}
        for r in rels:
            h = f.readline().split()
            need(len(h) == 3 and h[1] == b"blob", f"frozen file missing at HEAD: {r}")
            out[r] = f.read(int(h[2]))
            need(f.read(1) == b"\n", "git cat-file output")
        need(not f.read(1), "git cat-file output")
        return out

    def verify(self, approved_head=None):
        """-> Binding. Re-reads everything; raises Invalid on any difference."""
        head = self.git("rev-parse", "HEAD").decode().strip()
        need(approved_head is None or approved_head == head, "HEAD is not the approved revision")
        raw = self.git("cat-file", "blob", f"{head}:{self.rel}")
        fz = loads(raw)
        need(isinstance(fz, dict) and set(fz) == FIELDS and fz["schema"] == SCHEMA, "freeze fields")
        need(norm(self.rel, (self.repo / self.rel).read_bytes()) == norm(self.rel, raw), "working freeze differs from HEAD")
        need(self.git("rev-list", "--parents", "-n", "1", head).decode().split() == [head, fz["code_head"]],
             "freeze commit is not directly above its code commit")
        need(self.git("diff", "--name-only", fz["code_head"], head).decode().split("\n") == [self.rel, ""],
             "freeze commit changes other files")
        need(not self.git("status", "--porcelain", "--untracked-files=no").strip(), "tracked files are modified")
        bad = RK.check_runtime(fz["runtime"])
        need(not bad, f"runtime differs from the freeze: {bad}")
        files, data = fz["files"], {}
        need(isinstance(files, dict) and files and {fz["training"], fz["seeds"], *fz["reserved_seeds"]} <= set(files),
             "inputs are not in the freeze")
        committed = self.blobs(head, files)
        for rel, h in files.items():
            need(".." not in Path(rel).parts and not Path(rel).is_absolute(), f"path {rel}")
            p = self.repo / rel
            need(p.is_file(), f"frozen file missing: {rel}")
            data[rel] = p.read_bytes()
            need(norm(rel, data[rel]) == h == norm(rel, committed[rel]), f"frozen file differs: {rel}")
        check_imports({"repo": str(self.repo), "files": files})
        need(fz["episodes"] == C.EPISODES and list(fz["episodes"]) == sorted(C.EPISODES), "episodes")
        need(type(fz["workers"]) is int, "workers")
        book = loads(data[fz["seeds"]])
        seeds, reserved = book["seeds"], set()
        need(sorted(fz["reserved_seeds"]) == sorted(book["screened"]), "reserved seed files differ from the screened ones")
        for rel in fz["reserved_seeds"]:
            old = loads(data[rel])
            vals = {v for f in SEED_FIELDS for v in old.get(f, {}).values()}
            need(len(vals) == book["screened"][rel]["values"], f"{rel}: seed count")
            reserved |= vals
        check_inventory(seeds, C.all_keys(), reserved)
        ident = {"head": head, "freeze_sha256": sha(raw), "runtime": RK.runtime_identity(),
                 "training_sha256": files[fz["training"]], "seeds_sha256": files[fz["seeds"]]}
        return Binding(ident, fz, seeds, loads(data[fz["training"]]))


class Binding:
    def __init__(self, identity, freeze, seeds, training):
        self.identity, self.freeze, self.seeds, self.training = identity, freeze, seeds, training

    @property
    def jobs(self):
        return job_names(self.freeze["episodes"])

    def context(self, repo):
        return {"repo": str(repo), "files": self.freeze["files"], "training": self.freeze["training"], "seeds": self.freeze["seeds"]}


def check_imports(context):
    """Every module loaded from the repository must be a frozen file with the frozen bytes."""
    repo, files = Path(context["repo"]), context["files"]
    for m in list(sys.modules.values()):
        f = getattr(m, "__file__", None)
        if not f:
            continue
        p = Path(f).resolve()
        if p.is_relative_to(repo):
            rel = p.relative_to(repo).as_posix()
            need(rel in files and norm(rel, p.read_bytes()) == files[rel], f"module is not frozen: {rel}")


def frozen_json(context, role):
    """Worker-side read of the frozen training or seed file, hash-checked on the bytes that are parsed."""
    rel = context[role]
    b = (Path(context["repo"]) / rel).read_bytes()
    need(norm(rel, b) == context["files"][rel], f"frozen input differs: {rel}")
    return loads(b)


def launch(study, run_dir, approved_head, job_fn, preflight, **kw):
    """verify -> decoder preflight -> reserve -> execute. The run closes as succeeded only if the study is still unchanged
    and `check_study` admits the exact bytes being published.

    Still open (P1): `preflight`, `pool` and the job are supplied by the caller. See STUDY_INTEGRATION_CHECKLIST.md."""
    b = study.verify(approved_head)
    need(type(approved_head) is str, "an approved revision is required to launch")
    mod = Path(sys.modules[job_fn.__module__].__file__).resolve()
    need(mod.is_relative_to(study.repo) and mod.relative_to(study.repo).as_posix() in b.freeze["files"], "job is not frozen")
    bad = preflight()
    need(bad == [], f"preflight: {bad}")

    def again():
        need(study.verify().identity == b.identity, "the study changed during the run")
    res = LC.reserve(run_dir, b.identity, b.jobs, b.freeze["workers"])
    return LC.execute(res, [(n, n) for n in b.jobs], job_fn, context=b.context(study.repo),
                      commit_hook=(__name__, "check_imports"), final_check=again,
                      admission=lambda body, episodes, used: check_study(b, body, episodes, used), **kw)


def admit(study, run_dir):
    """-> (pairs [(record, arrays)], provenance). The only way analysis obtains records."""
    b = study.verify()
    body, episodes, used, close_sha = LC.load_success(run_dir)
    return check_study(b, body, episodes, used), {"run_id": body["run_id"], "close_sha256": close_sha, **b.identity}


def check_study(b, body, episodes, used):
    """The study's own rules on lifecycle-checked bytes. Used before success is published and again before analysis."""
    need(body["identity"] == b.identity, "the run belongs to another revision, freeze, runtime or input set")
    need(body["jobs"] == b.jobs and body["workers"] == b.freeze["workers"], "the run's jobs or workers differ from the freeze")
    pairs = []
    for s, n in b.freeze["episodes"].items():
        for e in range(n):
            nm = f"{s}_e{e}"
            rec, raw = episodes[nm]
            r = loads(rec)
            need(r.get("archive") == "archive.npz", f"{nm}: archive name")
            P.check_record(r, b.seeds, b.training, (s, e), extra=("run_id",))
            need(used[nm] == sha(jbytes(r["seeds"])), f"{nm}: seeds differ from the confirmed ones")
            pairs.append((r, P.check_arrays(r, raw)))
    order = list(C.EPISODES)
    pairs.sort(key=lambda x: (order.index(x[0]["schedule"]), x[0]["episode"]))
    return pairs
