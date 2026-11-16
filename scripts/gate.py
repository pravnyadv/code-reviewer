#!/usr/bin/env python3
"""Run the code-review gate on the current branch: plan, review, verify, save, verdict.

    gate.py [MR] [--repo DIR] [--target BRANCH] [--fresh] [--model opus] [--review-budget 8] [--verify-budget 4]

With no MR, it reviews the branch checked out in --repo (a pre-MR check). With an MR (a GitLab link, `!438`
or `438`), it reads the MR through glab, fetches the MR's head into a temporary worktree of --repo, reviews
that, and removes the worktree, so any checkout of the repository can review anyone's MR.

Everything mechanical happens here, in the same order on every run. Claude is called only for the two
judgment steps, each as its own headless `claude -p` call with a JSON schema for its answer:

  1. plan     scripts/gate-plan.py picks the range, the open MR, the cache, and full vs incremental
  2. review   full: two calls in parallel (A runtime behaviour, B everything else) on the whole range
              incremental: one call with both lenses, on the changed files only, re-checking old findings
  3. verify   one fresh call checks every finding against the code, merges duplicates, drops what fails
  4. save     scripts/gate-plan.py --save writes the cache, so the next run only reviews what changed
  5. report   P0-P3 findings and `Verdict: BLOCK` (a verified P0/P1 is open) or `PASS`

Exit status: 0 PASS, 1 BLOCK, 2 the gate itself failed (the message says why).
"""
import argparse
import concurrent.futures
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SUBSKILLS = os.path.join(ROOT, "skills", "code-reviewer", "subskills")
COMMAND = os.path.join(ROOT, "commands", "code-reviewer.md")

READ_ONLY_TOOLS = ["Read", "Grep", "Glob", "Bash"]
ALLOWED_BASH = [
    "Bash(git diff:*)", "Bash(git log:*)", "Bash(git show:*)", "Bash(git grep:*)",
    "Bash(git blame:*)", "Bash(git ls-files:*)", "Bash(glab mr view:*)",
]
SEVERITIES = ["P0", "P1", "P2", "P3"]

FINDING = {
    "type": "object",
    "properties": {
        "file": {"type": "string"},
        "line": {"type": "integer"},
        "severity": {"type": "string", "enum": SEVERITIES},
        "title": {"type": "string"},
        "scenario": {"type": "string", "description": "the reachable chain of events that breaks, concretely"},
        "fix": {"type": "string"},
        "evidence": {"type": "string", "description": "file:line references or command output that prove it"},
    },
    "required": ["file", "line", "severity", "title", "scenario", "fix", "evidence"],
}
REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "findings": {"type": "array", "items": FINDING},
        "recheck": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "status": {"type": "string", "enum": ["fixed", "open"]},
                    "evidence": {"type": "string"},
                },
                "required": ["id", "status", "evidence"],
            },
        },
    },
    "required": ["findings"],
}
VERIFY_SCHEMA = {
    "type": "object",
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                **FINDING,
                "properties": {
                    **FINDING["properties"],
                    "status": {"type": "string", "enum": ["verified", "unverified"]},
                    "settle": {"type": "string", "description": "for unverified: what would settle it"},
                },
                "required": FINDING["required"] + ["status"],
            },
        },
        "dropped": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"title": {"type": "string"}, "reason": {"type": "string"}},
                "required": ["title", "reason"],
            },
        },
    },
    "required": ["findings", "dropped"],
}

LENS_A = """LENS A, runtime behaviour. Spend your effort here:
- Queue jobs: compare each job's `timeout` and any internal time budget with its queue connection's `retry_after` /
  visibility timeout (read the queue config), and check tries, backoff, uniqueness and what a re-delivery does.
- Return contracts: list every call in the added code whose result is discarded or only partly used (a bare
  statement call, a result never checked), open each callee, and note whether it signals failure by throwing or by
  returning false/null/an error object. A returned failure the caller ignores is a finding, and so is a retry setting
  (`tries`, backoff) that can never fire because nothing throws.
- Time windows: list every query or filter in the added code on a time or sequence column (created_at, time, ids
  used as cursors). For each, write down its lower bound, its upper bound (or that it has none), which clock or
  source each bound comes from and its precision, and which OTHER code paths write rows into that range while this
  code runs (the live path, a sweep, a retry). Rows that both this code and another path handle, or that fall just
  outside a bound, are findings.
- Idempotency and dedupe: list every external record the added code creates or updates (API events, messages, rows
  in another system). For each, find every other code path that writes the same record and compare the id or dedupe
  key each one builds. Two paths that build different keys for the same thing produce duplicates; that is a finding.
- Concurrency and races, continuations and failure handlers, data that can be lost or duplicated."""

LENS_B = """LENS B, everything else: security and authorization, architecture and design, error handling,
performance and N+1 queries, API design and backward compatibility, dead code, and tests."""


START = time.time()


def progress(message):
    """One live status line on stderr, so a caller sees where the gate is while it runs."""
    print(f"[gate {int(time.time() - START):>4}s] {message}", file=sys.stderr, flush=True)


def fail(message):
    print(f"❌ gate: {message}", file=sys.stderr)
    sys.exit(2)


def read(path):
    with open(path) as fh:
        return fh.read()


def verification_rules():
    text = read(COMMAND)
    start = text.find("## Verification Rules")
    return text[start:] if start >= 0 else ""


def checklists(names):
    return "\n\n".join(read(os.path.join(SUBSKILLS, f"{n}.md")) for n in names)


def mr_text(repo, mr):
    if not mr:
        return ""
    out = subprocess.run(["glab", "mr", "view", str(mr["iid"])], cwd=repo, capture_output=True, text=True)
    body = out.stdout.strip() if out.returncode == 0 else f"(could not read MR !{mr['iid']})"
    return body[:8000]


def claude(repo, prompt, schema, model, budget, label):
    """One headless, read-only Claude call; returns (structured_output, cost)."""
    started = time.time()
    progress(f"{label}: started ({model}, cap ${budget:.0f})")
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    cmd = [
        "claude", "-p", prompt, "--model", model, "--output-format", "json",
        "--json-schema", json.dumps(schema), "--max-budget-usd", str(budget),
        "--tools", ",".join(READ_ONLY_TOOLS), "--allowedTools", *ALLOWED_BASH,
        "--strict-mcp-config", "--disable-slash-commands", "--no-session-persistence",
    ]
    out = subprocess.run(cmd, cwd=repo, env=env, capture_output=True, text=True, timeout=3600)
    try:
        data = json.loads(out.stdout)
    except json.JSONDecodeError:
        fail(f"claude returned no JSON (exit {out.returncode}): {(out.stderr or out.stdout)[-600:]}")
    cost = float(data.get("total_cost_usd") or 0)
    result = data.get("structured_output")
    if data.get("is_error") or result is None:
        fail(f"{label} failed ({data.get('subtype')}, ${cost:.2f}): {str(data.get('result'))[-600:]}")
    found = len(result.get("findings", []))
    progress(f"{label}: done in {int(time.time() - started)}s, ${cost:.2f}, {found} finding(s)")
    return result, cost


def review_prompt(plan, lens, checklist_names, mr, files, recheck):
    listed = ", ".join(f"`{f}`" for f in (files if files is not None else plan["changed_files"]))
    scope = (
        f"the diff of these files (generated files such as lock files are left out on purpose): {listed}"
        if files is None
        else f"ONLY these files' diffs (the rest of the branch was reviewed before and has not changed): {listed}"
    ) + f". Use `git diff {plan['range']} -- <file>`."
    parts = [
        f"You are reviewing branch `{plan['branch']}` against `origin/{plan['target']}` in this repository, as a "
        f"senior engineer before it merges. Review {scope}",
        "Read the diff yourself, then read whatever the claims depend on outside it: callers, callees, wrappers, "
        "config, migrations, tests. Do not edit anything.",
        lens,
        "Checklists to apply:\n\n" + checklists(checklist_names),
        verification_rules(),
    ]
    if mr:
        parts.insert(1, "The MR's description states the intent and the manual deploy steps; do not report what it "
                        "already handles:\n\n" + mr)
    if recheck:
        parts.append(
            "Earlier findings in these files, to re-check: for each id say `fixed` or `open`, with evidence:\n"
            + json.dumps(recheck, indent=1)
        )
    parts.append(
        "Return every finding that survives the verification rules, each with a concrete reachable scenario and "
        "the evidence (file:line) that proves it. Return an empty list if there are none."
    )
    return "\n\n---\n\n".join(parts)


def verify_prompt(plan, mr, findings):
    return "\n\n---\n\n".join(filter(None, [
        f"Two reviewers reported the findings below on branch `{plan['branch']}` (diff `git diff {plan['range']}`). "
        "You are the verifier. Reviewers are often confidently wrong, so check every finding yourself.",
        "For each finding: open the cited code and what it depends on; confirm the cited lines say what is claimed, "
        "the scenario is reachable through the real call path, and nothing elsewhere (framework, middleware, config, "
        "the MR description) already handles it. Read only what each claim needs. Do not edit anything.",
        "Merge duplicates (same root cause) into one. Keep a finding as `verified` when you confirmed it, "
        "`unverified` with `settle` (what would decide it) when you cannot tell, and put it in `dropped` with a "
        "one-line reason when it is wrong or already handled. You may correct a severity, line or fix; keep "
        "titles short.",
        ("MR description:\n\n" + mr) if mr else "",
        "Findings:\n" + json.dumps(findings, indent=1),
    ]))


def checkout_mr(repo, ref):
    """Look the MR up with glab and check its head out into a temporary worktree: (dir, branch, mr)."""
    out = subprocess.run(["glab", "mr", "view", ref, "-F", "json"], cwd=repo, capture_output=True, text=True)
    if out.returncode != 0:
        fail(f"glab could not read MR {ref}: {(out.stderr or out.stdout).strip()[:400]}")
    data = json.loads(out.stdout)
    iid = data["iid"]
    # GitLab publishes every MR's head (fork MRs included) as refs/merge-requests/<iid>/head.
    fetched = subprocess.run(["git", "-C", repo, "fetch", "--quiet", "origin",
                              f"refs/merge-requests/{iid}/head", data["target_branch"]], capture_output=True, text=True)
    if fetched.returncode != 0:
        fail(f"could not fetch MR !{iid}: {fetched.stderr.strip()[:400]}")
    head = subprocess.run(["git", "-C", repo, "rev-parse", "FETCH_HEAD"], capture_output=True, text=True).stdout.split()[0]
    work = os.path.join(tempfile.gettempdir(), f"code-review-mr-{iid}-{os.getpid()}")
    added = subprocess.run(["git", "-C", repo, "worktree", "add", "--quiet", "--detach", work, head],
                           capture_output=True, text=True)
    if added.returncode != 0:
        fail(f"could not create the review worktree: {added.stderr.strip()[:400]}")
    mr = {"iid": iid, "url": data.get("web_url"), "target": data["target_branch"], "title": data.get("title")}
    return work, data["source_branch"], mr


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mr", nargs="?", help="GitLab MR link, !iid or iid (default: the checked-out branch)")
    ap.add_argument("--repo", default=os.getcwd())
    ap.add_argument("--target")
    ap.add_argument("--fresh", action="store_true", help="ignore the cache and review everything")
    ap.add_argument("--model", default="opus")
    ap.add_argument("--review-budget", type=float, default=8.0, help="USD cap per review call")
    ap.add_argument("--verify-budget", type=float, default=4.0, help="USD cap for the verify call")
    a = ap.parse_args()
    a.repo = subprocess.run(["git", "-C", a.repo, "rev-parse", "--show-toplevel"],
                            capture_output=True, text=True).stdout.strip() or fail(f"{a.repo} is not a git repository")
    if not a.mr:
        run(a, a.repo, [])
        return
    progress(f"reading MR {a.mr} and checking out its head in a temporary worktree")
    work, branch, mr = checkout_mr(a.repo, re.sub(r"^!", "", a.mr))
    try:
        run(a, work, ["--branch", branch, "--mr-json", json.dumps(mr), "--target", a.target or mr["target"]])
    finally:
        subprocess.run(["git", "-C", a.repo, "worktree", "remove", "--force", work], capture_output=True)
        shutil.rmtree(work, ignore_errors=True)


def run(a, repo, extra):
    """Plan, review, verify, save and report for the checkout at `repo`."""
    plan_cmd = [sys.executable, os.path.join(HERE, "gate-plan.py"), "--repo", repo, *extra]
    plan_cmd += ["--target", a.target] if a.target and "--target" not in extra else []
    plan_cmd += ["--fresh"] if a.fresh else []
    out = subprocess.run(plan_cmd, capture_output=True, text=True)
    if out.returncode != 0:
        fail((out.stderr or out.stdout).strip())
    plan = json.loads(out.stdout)
    mr = plan.get("mr")
    progress(f"plan: {plan['plan']} ({plan['why']}), {plan['files']} file(s) on {plan['range']}"
             + (f", MR !{mr['iid']}" if mr else ""))
    head = (f"Gate: {plan['plan']} on {plan['range']} ({plan['branch']}"
            + (f", MR !{mr['iid']}" if mr else "") + f") · files {plan['files']}")

    carried = [dict(f, status=f.get("status", "open")) for f in plan["carried_findings"]]
    cost = 0.0
    fixed_ids = []

    if plan["plan"] in ("nothing", "up-to-date"):
        report(head + f" · {plan['why']}", carried, [], [], fixed_ids, cost)
        return

    mr_body = mr_text(repo, mr)
    every = ["review-solid-architecture", "plan-dead-code-removal", "audit-security-reliability",
             "check-quality-performance", "validate-testing-api-design"]

    if plan["plan"] == "full-parallel":
        calls = [
            (LENS_A, ["audit-security-reliability", "check-quality-performance"]),
            (LENS_B, every),
        ]
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            jobs = [pool.submit(claude, repo, review_prompt(plan, lens, names, mr_body, None, []),
                                REVIEW_SCHEMA, a.model, a.review_budget, label)
                    for (lens, names), label in zip(calls, ["review A (runtime behaviour)", "review B (everything else)"])]
            results = [j.result() for j in jobs]
        raw = [f for r, _ in results for f in r["findings"]]
        cost += sum(c for _, c in results)
        reopened = []
    else:  # incremental
        recheck = plan["recheck_findings"]
        result, c = claude(repo, review_prompt(plan, LENS_A + "\n\n" + LENS_B, every, mr_body,
                                               plan["changed_files"], recheck),
                           REVIEW_SCHEMA, a.model, a.review_budget, f"review ({len(plan['changed_files'])} changed file(s))")
        cost += c
        raw = result["findings"]
        status = {r["id"]: r["status"] for r in result.get("recheck", [])}
        fixed_ids = [f["id"] for f in recheck if status.get(f.get("id")) == "fixed"]
        reopened = [f for f in recheck if status.get(f.get("id")) != "fixed"]

    verified, dropped = [], []
    if raw:
        result, c = claude(repo, verify_prompt(plan, mr_body, raw), VERIFY_SCHEMA, a.model, a.verify_budget,
                           f"verify ({len(raw)} finding(s))")
        cost += c
        verified, dropped = result["findings"], result["dropped"]

    final = carried + reopened + verified
    for i, f in enumerate(final, 1):
        f.setdefault("id", f"F{i:03d}")
        f.setdefault("description", f.get("scenario", ""))
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump(final, fh)
    saved = subprocess.run([sys.executable, os.path.join(HERE, "gate-plan.py"), "--repo", repo, *extra,
                            *(["--target", a.target] if a.target and "--target" not in extra else []),
                            "--save", fh.name],
                           capture_output=True, text=True)
    os.unlink(fh.name)
    if saved.returncode != 0:
        fail("could not save the cache: " + (saved.stderr or saved.stdout).strip())
    progress("cache saved")

    report(head + f" · reviewed {len(plan['changed_files'])} · carried {len(carried)}",
           final, dropped, [f for f in final if f.get("status") == "unverified"], fixed_ids, cost)


def report(head, findings, dropped, unverified, fixed_ids, cost):
    open_findings = [f for f in findings if f.get("status") != "unverified"]
    blocking = [f for f in open_findings if f.get("severity") in ("P0", "P1")]
    print(head)
    for sev in SEVERITIES:
        group = [f for f in open_findings if f.get("severity") == sev]
        if group:
            print(f"\n{sev}")
            for f in group:
                print(f"- [{f['file']}:{f['line']}] **{f['title']}**: {f.get('scenario') or f.get('description', '')} "
                      f"**Fix**: {f.get('fix', '')}")
    if unverified:
        print("\nUnverified")
        for f in unverified:
            print(f"- [{f['file']}:{f['line']}] {f['title']}: {f.get('settle', 'needs a check')}")
    if fixed_ids:
        print("\nFixed since last review: " + ", ".join(fixed_ids))
    if dropped:
        print(f"\nDropped {len(dropped)}: " + "; ".join(f"{d['title']} ({d['reason']})" for d in dropped))
    print(f"\nCost ${cost:.2f}")
    print("Verdict: " + ("BLOCK" if blocking else "PASS"))
    sys.exit(1 if blocking else 0)


if __name__ == "__main__":
    main()
