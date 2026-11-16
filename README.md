# code-reviewer

A Claude Code plugin that performs structured code reviews. Covers SOLID principles, security vulnerabilities, performance issues, error handling, testing, API design, and boundary conditions — with P0–P3 severity ratings and confirmation before applying any fixes.

## Features

- **♻️ Incremental Re-reviews** — Caches findings per scope inside `.git/code-review/` (never committed, one cache per worktree), keyed by a SHA-256 of each file's full diff. On re-runs, skips unchanged files and only re-checks modified files for fixes + new issues — typically **60-80% faster** on follow-up reviews
- **⚡ Token Optimized** — Checklists are compressed with concise bullet points and stripped of boilerplate, saving 20-45% tokens compared to standard instructions
- **SOLID + Architecture** — SRP, OCP, LSP, ISP, DIP violations, layer integrity, and common code smells
- **Security** — XSS, injection, SSRF, AuthN/AuthZ gaps, JWT misuse, secrets leakage, file uploads, race conditions
- **Code Quality** — N+1 queries, async patterns, logging quality, type safety, error handling, boundary conditions
- **Testing + API Design** — test coverage, test quality, testability, API contracts, backward compatibility
- **Removal Planning** — dead code, deprecated APIs, stale feature flags, dead routes, orphaned migrations

## Installation

### Prerequisites

- [Claude Code](https://claude.ai/code) installed

### Install from marketplace (recommended)

**Step 1 — Add the marketplace:**
```bash
claude plugin marketplace add https://github.com/NisweyTech/code-reviewer
```

**Step 2 — Install the plugin:**
```bash
claude plugin install code-reviewer@nisweytech --scope user
```

**Step 3 — Verify:**
```bash
claude plugin list
# code-reviewer@nisweytech   Version: 1.0.0   Scope: user   Status: ✔ enabled
```

### Install from local clone

```bash
git clone https://github.com/NisweyTech/code-reviewer.git ~/code-reviewer
claude plugin marketplace add ~/code-reviewer
claude plugin install code-reviewer@nisweytech --scope user
```

### Session-only (no permanent install)

To try it without installing:
```bash
claude --plugin-dir ~/code-reviewer
```

## Usage

### Slash command

In any git repository, run:
```
/code-reviewer
```

You can also pass a specific file or context:
```
/code-reviewer src/auth/login.ts
```

Review a GitLab MR, or committed work on a branch before its MR exists:
```
/code-reviewer https://gitlab.niswey.net/group/repo/-/merge_requests/123
/code-reviewer !123
/code-reviewer --branch            # current branch vs origin's default branch
/code-reviewer --branch develop    # current branch vs origin/develop
```

Gate mode, for a pre-MR check or CI: reviews the committed branch, finds its open MR by itself, runs two parallel review passes (runtime behaviour, and everything else), verifies every finding against the code, keeps a cache so the next run only reviews files whose diff changed, and ends with `Verdict: BLOCK` or `PASS`:
```
/code-reviewer --gate              # --fresh forces a full review, --target <branch> overrides the target
```
The gate is a script, `scripts/gate.py`, so it runs the same way every time: it plans (`scripts/gate-plan.py`: scope, range, cache, full or incremental), runs each review pass and the verification as separate read-only `claude -p` calls with a JSON schema and a cost cap, saves the cache and exits 0 (PASS), 1 (BLOCK) or 2 (the gate failed). Pre-MR hooks and CI can call it directly:
```
python3 <plugin>/scripts/gate.py --repo .              # the checked-out branch (pre-MR)
python3 <plugin>/scripts/gate.py '!123' --repo .      # any MR: link, !iid or iid; reviewed in a temporary worktree
# options: --fresh, --target <branch>, --model, --review-budget, --verify-budget
```

With a clean working tree and no MR, branch mode is the default. Add `--no-cache` for one-off or parallel runs (gates, CI) so nothing is read from or written to the cache.

### Natural language (auto-activation)

The skill activates automatically when you ask things like:

- "Review my changes"
- "Review this PR"
- "Check for security issues"
- "Look for SOLID violations"
- "Audit my git diff"

## Review workflow

The plugin follows a multi-step process with incremental caching:

| Step | Action |
|------|--------|
| 0. Scope | MR link or ID via `glab`, else uncommitted changes, else the branch against its target |
| 0b. Cache Check | Load the scope's cache from `.git/code-review/` if it exists, enter incremental mode (skipped with `--no-cache`) |
| 1. Preflight | Identify critical paths in the scoped diff |
| 2. SOLID + Architecture | Check against SOLID principles, layer integrity, flag violations |
| 3. Removal Candidates | Identify dead code, deprecated APIs, stale flags, dead routes |
| 4. Security + Reliability | XSS, injection, race conditions, secrets, auth gaps, file uploads |
| 5. Code Quality | Error handling, async patterns, N+1, type safety, boundary conditions |
| 6. Testing + API Design | Test coverage, test quality, API contracts, backward compatibility |
| 7. Structured Output | P0–P3 report with `file:line` citations (+ ✅ Fixed / ⏳ Remaining / 🆕 New on re-runs) |
| 8. Save Cache | Write the scope's cache with findings and diff fingerprints (skipped with `--no-cache`) |
| 9. Confirmation | Present findings, ask before applying any fix |

### Incremental re-review (re-runs)

When you fix issues and run the review again, the plugin detects the cache and:
- **Skips unchanged files** — carries forward cached findings without re-analyzing
- **Targeted re-checks modified files** — verifies fixes and scans new diff hunks only
- **Full reviews new files** — any file not in the previous review gets the complete treatment

This saves significant tokens and time on follow-up reviews.

## Severity levels

| Level | Meaning | Action |
|-------|---------|--------|
| **P0 Critical** | Security vulnerability or data loss | Blocks merge |
| **P1 High** | Logic bug, SOLID violation, perf regression | Fix before merge |
| **P2 Medium** | Code smell, unclear intent | Fix now or in follow-up |
| **P3 Low** | Style, naming, minor consistency | Optional |

## Sample output

```
## Code Review — 3 files changed

### P0 Critical
[src/auth/token.ts:42] **JWT secret falls back to hardcoded value**: `process.env.JWT_SECRET || "dev-secret"` will use the hardcoded string in production if the env var is unset. **Fix**: throw at startup if JWT_SECRET is missing.

### P1 High
[src/db/users.ts:88] **N+1 query in loop**: `getUserById` called inside `for...of` loop over results. **Fix**: batch with `getUsersByIds(ids)` and resolve from a map.

### P2 Medium
[src/api/orders.ts:15] **SRP violation**: file handles HTTP parsing, business validation, and DB writes. **Fix**: extract validation and persistence into separate modules.

---
How would you like to proceed?
(a) Fix all issues (P0–P3)
(b) Fix P0 and P1 only
(c) Fix specific items
(d) Review only — no changes
```

## Repository structure

```
code-reviewer/
├── .claude-plugin/
│   ├── plugin.json                        # Plugin manifest
│   └── marketplace.json                   # Marketplace definition
├── commands/
│   └── code-reviewer.md             # /code-reviewer slash command
├── skills/
│   └── code-reviewer/
│       ├── SKILL.md                      # Auto-activating skill
│       └── subskills/
│           ├── review-solid-architecture.md    # SOLID principles & code smells
│           ├── audit-security-reliability.md   # Security, auth & race conditions
│           ├── check-quality-performance.md    # Error handling, performance, boundaries
│           ├── validate-testing-api-design.md  # Testing quality & API contracts
│           └── plan-dead-code-removal.md       # Dead code removal template
└── README.md
```

## License

MIT
