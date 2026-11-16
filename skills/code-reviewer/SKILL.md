---
name: code-review-expert
description: This skill should be used when the user asks to "review my changes", "review this PR", "review this MR", "check for security issues", "look for SOLID violations", "audit my git diff", or requests a senior engineer code review with structured findings. Supports GitLab MR links/IDs via glab.
---

# Code Review Expert

Perform a structured senior-engineer code review covering SOLID/architecture, security, reliability, performance, error handling, testing, API design, and boundary conditions with P0–P3 severity ratings. **Supports incremental re-reviews** — on re-runs, only re-checks modified files and verifies fixes, saving significant time and tokens.

## Review Process
0. **Scope** – MR link or ID: `glab mr view` + `glab mr diff`. Otherwise uncommitted changes: `git diff HEAD`. Otherwise (clean tree, or `--branch`): the branch against its target, `git diff origin/<target>...HEAD`
0b. **Cache Check** – unless `--no-cache`, read `$(git rev-parse --git-dir)/code-review/<scope key>.json`. If found, run in incremental mode: skip unchanged files, targeted re-check on modified files, full review only on new files
1. **Preflight** – identify critical paths in the scoped diff
2. **SOLID + Architecture** – SRP, OCP, LSP, ISP, DIP violations → `subskills/review-solid-architecture.md`
3. **Removal Candidates** – dead code, deprecated APIs, stale flags → `subskills/plan-dead-code-removal.md`
4. **Security + Reliability** – XSS, injection, AuthZ, race conditions, JWT, secrets → `subskills/audit-security-reliability.md`
5. **Code Quality** – error handling, N+1, boundary conditions → `subskills/check-quality-performance.md`
6. **Testing + API Design** *(only if tests exist)* – test coverage, test quality, API contracts → `subskills/validate-testing-api-design.md`
7. **Structured Output** – P0–P3 report with file:line citations. On re-runs: show ✅ Fixed, ⏳ Remaining, 🆕 New
8. **Save Cache** – unless `--no-cache`, write the cache file (inside `.git`, never committed) with findings and a SHA-256 of each file's full diff
9. **Confirmation** – present findings first, never apply fixes without explicit user approval

## Incremental Mode
When the scope's cache file exists from a previous review:
- **Unchanged files** (same SHA-256 of the file's full diff): skip entirely, carry forward cached findings
- **Modified files** (diff changed): targeted re-check — verify if cached findings are fixed, review the file's current diff for new issues
- **New files** (not in cache): full review
- This typically reduces re-review effort by 60-80% when only a few files were changed to fix issues

## Severity
| Level | Meaning | Action |
|-------|---------|--------|
| P0 Critical | Security/data loss | Blocks merge |
| P1 High | Logic/SOLID/perf | Fix before merge |
| P2 Medium | Code smells | Fix now or follow-up |
| P3 Low | Style/naming | Optional |

## Reference Files
Load when needed (only for files in scope):
- `subskills/review-solid-architecture.md` — SOLID principles & code smells
- `subskills/audit-security-reliability.md` — security and reliability audit
- `subskills/check-quality-performance.md` — error handling, performance, boundaries
- `subskills/plan-dead-code-removal.md` — dead code removal template
- `subskills/validate-testing-api-design.md` — testing quality & API contract design
