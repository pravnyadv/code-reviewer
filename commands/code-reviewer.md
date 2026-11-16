# Code Review Protocol

Review current git changes using a risk-first, incremental approach.
---
## 0. Scope (decide this first)
Pick exactly one scope from the arguments and the repo state:
- **MR mode**: the user gave an MR link (e.g. `https://gitlab.niswey.net/…/merge_requests/123`) or ID (`!123`, `MR 123`, `mr 123`).
  - `glab mr view <MR_ID>` for title, description, source and target branch. Read the description: it states intent and deploy steps that change what counts as a bug.
  - `glab mr diff <MR_ID>` is the review scope. Do NOT fall back to `git diff` against `master`/`main`.
  - Scope key: `mr-<MR_ID>`.
- **Working-tree mode**: no MR given and `git status --porcelain` shows uncommitted changes. Scope is `git diff HEAD` (staged plus unstaged). Scope key: `worktree-<current branch>`.
- **Branch mode**: no MR given and the working tree is clean (committed work not yet in an MR, e.g. a pre-MR check), or the user passed `--branch`.
  - Target: the branch the user named, else `git symbolic-ref --short refs/remotes/origin/HEAD` (strip `origin/`), else `master` or `main`, whichever exists.
  - `git fetch origin <target>`, then the scope is `git diff origin/<target>...HEAD`.
  - Scope key: `branch-<current branch>`.

Say in one line which mode and range you are reviewing.
---
## 0b. Incremental Review Check (cache)
- Skip this step entirely when the user passed `--no-cache` (use it for gates and for parallel runs, which would otherwise race on one file).
- Cache file: `$(git rev-parse --git-dir)/code-review/<scope key>.json`, with `/` in the key replaced by `-`. It lives inside `.git`, so it is never committed and each worktree has its own. Ignore any old `.code-review-cache.json` in the project root.
- **Fingerprint** of a file = SHA-256 of that file's FULL diff, always computed with git so every run gets the same value. Never a prefix of the diff: a change further down the file must change the fingerprint.
  - Branch mode: `git diff origin/<target>...HEAD -- <file> | shasum -a 256`
  - Working-tree mode: `git diff HEAD -- <file> | shasum -a 256`
  - MR mode: `git fetch origin <target> <source>` (branches from `glab mr view`), then `git diff origin/<target>...origin/<source> -- <file> | shasum -a 256`. Do not hash slices of `glab mr diff` output: how it is split is not stable between runs.
- **If the cache file exists (re-run):**
  - Read it, compute each in-scope file's fingerprint, and classify:
    - **unchanged**: same fingerprint, so carry its cached findings forward without re-analysis
    - **modified**: fingerprint differs, so re-check that file's cached findings (fixed or not) and review its whole current diff for new issues
    - **new**: not in the cache, so full review (Steps 2-6)
  - A cached file no longer in scope: its findings count as resolved.
  - Print a summary at the start:
    ```
    ♻️ Incremental review (cache: <scope key>, last reviewed <short sha>)
    • X files unchanged (carrying forward N findings)
    • Y files modified (targeted re-check)
    • Z new files (full review)
    ```
  - Continue at Step 2 with the narrowed scope.
- **If no cache exists (first run):** review everything in scope.
---
## 1. Risk
- Identify:
  - Changed files
  - Entry points
  - Critical paths (auth, payments, permissions, data writes, external calls)
- If >20 files:
  - Prioritize high-risk/core logic
- Output:
  - Brief risk summary
---
## 2. Architecture & Design
- Read: `../skills/code-reviewer/subskills/review-solid-architecture.md`
- Apply checks **only to files in scope** (all files on first run, only modified/new files on re-run)
- Severity: P1 = must fix, P2 = improvement
---
## 3. Removal Candidates
- Read: `../skills/code-reviewer/subskills/plan-dead-code-removal.md`
- Apply checks **only to files in scope**
---
## 4. Security & Concurrency
- Read: `../skills/code-reviewer/subskills/audit-security-reliability.md`
- Apply checks **only to files in scope**
- Severity: P0 = exploitable, P1 = high risk, P2 = hardening
---
## 5. Reliability & Quality
- Read: `../skills/code-reviewer/subskills/check-quality-performance.md`
- Apply checks **only to files in scope**
---
## 6. Testing & API Design
- First check if tests exist:
  - Look for: `test/`, `tests/`, `__tests__/`, `spec/`, `*_test.*`, `*.test.*`, `*.spec.*`
  - Or check for test scripts in `package.json`, `pytest.ini`, `phpunit.xml`, etc.
- If tests found:
  - Read: `../skills/code-reviewer/subskills/validate-testing-api-design.md`
  - Apply checks **only to files in scope**
- If no tests found:
  - Skip testing checks
  - Note: "No test suite detected — consider adding tests for critical paths"
---
## 7. Structured Output
Group findings by severity:
- **P0 Critical** – security/data loss – blocks merge
- **P1 High** – logic/design/performance – fix before merge
- **P2 Medium** – code smells – fix now or follow-up
- **P3 Low** – style/naming – optional
Format each finding as:
`[file:line] **Title**: description. **Fix**: concrete suggestion.`

On incremental re-runs, also show:
- **✅ Fixed** — findings from previous review that are now resolved
- **⏳ Remaining** — findings still present from previous review
- **🆕 New** — new findings from modified/new files
---
## 8. Save Review Cache
Skip with `--no-cache`. Otherwise write the cache file from Step 0b (create the `code-review/` directory if needed):
```json
{
  "timestamp": "<ISO 8601>",
  "scope": "<scope key>",
  "range": "<the exact diff range or MR id reviewed>",
  "reviewed_commit": "<HEAD short SHA>",
  "file_fingerprints": {
    "path/to/file.ts": "<sha256 of the file's full diff in this scope>"
  },
  "findings": [
    {
      "id": "<short unique id, e.g. F001>",
      "file": "path/to/file.ts",
      "line": 42,
      "severity": "P1",
      "title": "Missing null check",
      "description": "...",
      "fix": "...",
      "status": "open"
    }
  ]
}
```
- Record every in-scope file, including those with no findings, so the next run can tell unchanged from new.
---
## 9. Confirmation Before Applying Fixes
After presenting findings, ask:
> How would you like to proceed?
> (a) Fix all issues (P0–P3)
> (b) Fix P0 and P1 only
> (c) Fix specific items
> (d) Review only — no changes
Wait for explicit user confirmation before making any edits.
---
## Verification Rules (CRITICAL — reduces false positives)
Before reporting ANY finding, you MUST:
1. **Understand the diff before flagging** — In a diff, `-` lines are REMOVED and `+` lines are ADDED. When you spot a problem on a `-` line, do NOT immediately flag it. Instead, check the `+` lines and the final state of the file to see if the new code fixes it. If the `+` lines resolve the issue, it is already fixed — do not report it. Only flag the issue if the problem **still exists in the final code** (the `+` lines and unchanged context). Always verify against the final state of the file, not the removed code.
2. **Read the actual code** around the flagged line — not just the diff hunk. Use surrounding context (20+ lines) to check if the issue is real.
3. **Check for existing mitigations** — the codebase may already handle the issue elsewhere (middleware, base class, framework convention, wrapper function, config). Search before flagging.
4. **Trace the runtime flow** — understand how the code actually executes. Check route guards, initialization order, lifecycle hooks, and data loading sequences. A value that *looks* like it could be empty may be guaranteed non-empty by the app's boot/navigation flow.
5. **Check the API contract** — if data comes from a backend API, check what the API actually returns. Don't flag "unknown keys" or "missing fields" if the API contract is bounded and known.
6. **Prove it with a reachable scenario** — every finding must include a concrete, *reachable* scenario: "If X happens, then Y breaks because Z." The scenario must be possible in the actual application flow — not just theoretically possible if you ignore guards, middleware, and initialization. If you cannot construct a realistic scenario that a user or caller can actually trigger, drop the finding.
7. **Respect the framework** — if the project uses a framework (Express, Django, Rails, Next.js, Spring, Vue Router, etc.), do NOT flag things the framework already handles (e.g., CSRF in Django, XSS escaping in React/JSX, SQL injection with an ORM's parameterized queries).
8. **Only flag what changed** — do not flag pre-existing issues in unchanged code pulled into the diff context. The review is about the current changes, not a full codebase audit.

### Common false positives to suppress:
- Flagging an issue seen on `-` (removed) lines without checking if the `+` (added) lines fix it — always verify the final state before reporting
- "Empty/null edge case" when the value is guaranteed by route params, required props, initialization flow, or guards that run before the code is reached
- "Default/fallback value never used" is not a bug — it's defensive coding. Only flag if the default causes *wrong behavior*, not if it's merely unreachable
- "Stale keys" or "extra keys" when the API contract is bounded and no code reads unknown keys
- "Missing permission check" when a route guard or middleware already enforces it before the code runs
- "Missing null check" when TypeScript strict mode, the type system, or the app flow guarantees non-null
- "SQL injection" when using parameterized queries / ORM methods
- "XSS" in JSX/TSX (React auto-escapes by default)
- "Missing error handling" on operations that are already inside a try/catch or error boundary higher up
- "Hardcoded secret" for obviously placeholder/example values in test files or comments
- "Missing rate limiting" on internal-only endpoints
- "CSRF" when the framework has CSRF middleware enabled
- "Missing input validation" when validation happens in a middleware, decorator, or schema layer
- Flagging standard library or well-known package usage as "risky"
- "SRP violation" for files that are reasonably cohesive for the project's conventions

**If in doubt, leave it out.** A report with 3 real issues is far more valuable than one with 3 real issues buried in 15 false positives.
---
Constraints:
- Be concise
- Be evidence-based — every finding needs proof
- Avoid generic commentary
- On re-runs, minimize token usage by skipping unchanged files
- Quality over quantity — fewer, verified findings only