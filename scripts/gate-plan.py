#!/usr/bin/env python3
"""Decide what a /code-reviewer --gate run reviews, and keep its cache.

Plan (default): prints JSON with the scope, the diff range, the cache path and
whether the review must be full (two parallel passes) or incremental (only the
files whose diff changed since the cached review).

    gate-plan.py [--repo DIR] [--target BRANCH] [--fresh]
    gate-plan.py [--repo DIR] [--target BRANCH] --save FINDINGS.json

The review range is always origin/<target>...HEAD, so a run before the MR
exists and a run after it review the same diff and share one cache, keyed by
the branch. An open GitLab MR for the branch only adds its id and description.
The cache lives inside the git dir (never committed, one per worktree).
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

FULL_REVIEW_SHARE = 0.5  # more than this share of files changed: review everything again


def git(repo, *args, check=True):
    out = subprocess.run(["git", "-C", repo, *args], capture_output=True)
    if check and out.returncode != 0:
        sys.exit(f"gate-plan: git {' '.join(args)} failed: {out.stderr.decode().strip()}")
    return out.stdout


def git_text(repo, *args, check=True):
    return git(repo, *args, check=check).decode().strip()


def open_mr(repo, branch):
    """The open GitLab MR whose source is this branch, or None."""
    if not shutil.which("glab") or "gitlab" not in git_text(repo, "remote", "get-url", "origin", check=False):
        return None
    out = subprocess.run(
        ["glab", "mr", "list", "--source-branch", branch, "-F", "json"],
        cwd=repo, capture_output=True,
    )
    if out.returncode != 0:
        return None
    try:
        mrs = [m for m in json.loads(out.stdout or b"[]") if m.get("state") == "opened"]
    except json.JSONDecodeError:
        return None
    if not mrs:
        return None
    mr = mrs[0]
    return {"iid": mr["iid"], "url": mr.get("web_url"), "target": mr.get("target_branch"), "title": mr.get("title")}


def default_target(repo):
    head = git_text(repo, "symbolic-ref", "--short", "refs/remotes/origin/HEAD", check=False)
    if head.startswith("origin/"):
        return head[len("origin/"):]
    for name in ("master", "main"):
        if git_text(repo, "rev-parse", "--verify", "--quiet", f"refs/remotes/origin/{name}", check=False):
            return name
    sys.exit("gate-plan: cannot tell the target branch; pass --target")


def fingerprints(repo, rng):
    files = [f for f in git_text(repo, "diff", "--name-only", rng).splitlines() if f]
    return {f: hashlib.sha256(git(repo, "diff", rng, "--", f)).hexdigest() for f in files}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.getcwd())
    ap.add_argument("--target")
    ap.add_argument("--fresh", action="store_true", help="ignore the cache: plan a full review")
    ap.add_argument("--save", metavar="FINDINGS_JSON", help="write the cache with these verified findings")
    a = ap.parse_args()

    repo = git_text(a.repo, "rev-parse", "--show-toplevel")
    dirty = [l for l in git_text(repo, "status", "--porcelain", "--untracked-files=no").splitlines() if l]
    if dirty:
        sys.exit("gate-plan: uncommitted changes; commit them first (the gate reviews committed work):\n" + "\n".join(dirty))
    branch = git_text(repo, "rev-parse", "--abbrev-ref", "HEAD")
    if branch == "HEAD":
        sys.exit("gate-plan: detached HEAD; check out the branch under review")

    mr = open_mr(repo, branch)
    target = a.target or (mr and mr["target"]) or default_target(repo)
    git(repo, "fetch", "--quiet", "origin", target)
    rng = f"origin/{target}...HEAD"
    prints = fingerprints(repo, rng)
    head = git_text(repo, "rev-parse", "--short", "HEAD")

    cache_dir = os.path.join(git_text(repo, "rev-parse", "--absolute-git-dir"), "code-review")
    cache_path = os.path.join(cache_dir, "branch-" + re.sub(r"[^A-Za-z0-9._-]", "-", branch) + ".json")

    if a.save:
        with open(a.save) as fh:
            findings = json.load(fh)
        os.makedirs(cache_dir, exist_ok=True)
        with open(cache_path, "w") as fh:
            json.dump({
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
                "branch": branch, "target": target, "range": rng, "reviewed_commit": head,
                "file_fingerprints": prints, "findings": findings,
            }, fh, indent=2)
        print(json.dumps({"saved": cache_path, "files": len(prints), "findings": len(findings)}))
        return

    cache = None
    if not a.fresh and os.path.exists(cache_path):
        with open(cache_path) as fh:
            cache = json.load(fh)
        if cache.get("target") != target:
            cache = None

    old = (cache or {}).get("file_fingerprints", {})
    changed = [f for f, h in prints.items() if old.get(f) != h]
    unchanged = [f for f in prints if f not in changed]
    gone = [f for f in old if f not in prints]

    if not prints:
        plan, why = "nothing", "the branch has no changes against its target"
    elif cache is None:
        plan, why = "full-parallel", "fresh run requested" if a.fresh else "no cache for this branch yet"
    elif not changed and not gone:
        plan, why = "up-to-date", "every file's diff matches the cached review"
    elif len(changed) > FULL_REVIEW_SHARE * len(prints):
        plan, why = "full-parallel", f"{len(changed)} of {len(prints)} files changed since the cached review"
    else:
        plan, why = "incremental", f"{len(changed)} of {len(prints)} files changed since the cached review"

    carried = [f for f in (cache or {}).get("findings", []) if f.get("file") in unchanged]
    recheck = [f for f in (cache or {}).get("findings", []) if f.get("file") in changed]
    resolved = [f for f in (cache or {}).get("findings", []) if f.get("file") in gone]

    print(json.dumps({
        "plan": plan, "why": why,
        "mode": "mr" if mr else "branch", "mr": mr,
        "branch": branch, "target": target, "range": rng, "head": head,
        "cache": cache_path, "cached_commit": (cache or {}).get("reviewed_commit"),
        "files": len(prints), "changed_files": changed if cache else list(prints),
        "unchanged_files": len(unchanged) if cache else 0, "removed_files": gone,
        "carried_findings": carried, "recheck_findings": recheck, "resolved_findings": resolved,
    }, indent=2))


if __name__ == "__main__":
    main()
