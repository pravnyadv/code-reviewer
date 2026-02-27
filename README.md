# code-reviewer

A Claude Code plugin that performs structured senior-engineer code reviews. Covers SOLID principles, security vulnerabilities, performance issues, error handling, testing, API design, and boundary conditions — with P0–P3 severity ratings and confirmation before applying any fixes.

## Features

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

### Natural language (auto-activation)

The skill activates automatically when you ask things like:

- "Review my changes"
- "Review this PR"
- "Check for security issues"
- "Look for SOLID violations"
- "Audit my git diff"

## Review workflow

The plugin follows an 8-step process:

| Step | Action |
|------|--------|
| 1. Preflight | `git diff` / `git status` to scope changes, identify critical paths |
| 2. SOLID + Architecture | Check against SOLID principles, layer integrity, flag violations |
| 3. Removal Candidates | Identify dead code, deprecated APIs, stale flags, dead routes |
| 4. Security + Reliability | XSS, injection, race conditions, secrets, auth gaps, file uploads |
| 5. Code Quality | Error handling, async patterns, N+1, type safety, boundary conditions |
| 6. Testing + API Design | Test coverage, test quality, API contracts, backward compatibility |
| 7. Structured Output | P0–P3 report with `file:line` citations |
| 8. Confirmation | Present findings, ask before applying any fix |

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
