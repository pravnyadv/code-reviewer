# Dead Code Removal Plan

Identify and classify removal candidates from changed files.
---
## 1. Identify
- Scan for:
  - Unreachable / never-called code
  - Deprecated API usage
  - Permanent or stale feature flags
  - Commented-out code blocks
  - Unused imports, variables, functions, classes
  - Redundant abstraction layers
  - Dead routes / unused endpoints
  - Orphaned DB migrations or unused schema columns
  - Stale environment config / unused env vars
- Tools:
  - `rg` / `grep` for reference search
  - Check for dynamic/reflection-based usage
---
## 2. Classify
- **Remove now** — no active consumers, safe to delete:
  - Location: `file:line`
  - Evidence: no references, dead flag, deprecated
  - Impact: none/low
  - Steps: remove code → remove tests → remove config
  - Verify: run tests, check logs
- **Defer** — needs migration or sign-off:
  - Location: `file:line`
  - Why defer: active consumers, breaking change, needs migration
  - Preconditions: flag off 2 weeks, telemetry shows 0 usage
  - Timeline: target date/sprint
  - Owner: person/team
  - Rollback: how to restore if issues
---
## 3. Pre-Removal Checklist
- Searched codebase for all references
- Checked dynamic/reflection usage
- Verified no external consumers (APIs, SDKs, docs)
- Feature flag telemetry reviewed
- Tests updated/removed
- Documentation updated
- Team notified (if shared code)
---
Severity:
- P0 = removal blocks security fix or causes cost
- P1 = remove in current sprint
- P2 = backlog / next iteration
