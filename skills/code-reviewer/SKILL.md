---
name: code-review-expert
description: This skill should be used when the user asks to "review my changes", "review this PR", "check for security issues", "look for SOLID violations", "audit my git diff", or requests a senior engineer code review with structured findings.
---

# Code Review Expert

Perform a structured 8-step senior-engineer code review covering SOLID/architecture, security, reliability, performance, error handling, testing, API design, and boundary conditions with P0–P3 severity ratings.

## Eight-Step Review Process
1. **Preflight** – `git diff`/`git status` to scope changes, identify critical paths
2. **SOLID + Architecture** – SRP, OCP, LSP, ISP, DIP violations → `subskills/review-solid-architecture.md`
3. **Removal Candidates** – dead code, deprecated APIs, stale flags → `subskills/plan-dead-code-removal.md`
4. **Security + Reliability** – XSS, injection, AuthZ, race conditions, JWT, secrets → `subskills/audit-security-reliability.md`
5. **Code Quality** – error handling, N+1, boundary conditions → `subskills/check-quality-performance.md`
6. **Testing + API Design** *(only if tests exist)* – test coverage, test quality, API contracts → `subskills/validate-testing-api-design.md`
7. **Structured Output** – P0–P3 report with file:line citations
8. **Confirmation** – present findings first, never apply fixes without explicit user approval

## Severity
| Level | Meaning | Action |
|-------|---------|--------|
| P0 Critical | Security/data loss | Blocks merge |
| P1 High | Logic/SOLID/perf | Fix before merge |
| P2 Medium | Code smells | Fix now or follow-up |
| P3 Low | Style/naming | Optional |

## Reference Files
Load when needed:
- `subskills/review-solid-architecture.md` — SOLID principles & code smells
- `subskills/audit-security-reliability.md` — security and reliability audit
- `subskills/check-quality-performance.md` — error handling, performance, boundaries
- `subskills/plan-dead-code-removal.md` — dead code removal template
- `subskills/validate-testing-api-design.md` — testing quality & API contract design
