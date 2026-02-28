# Code Review Protocol

Review current git changes using a risk-first approach.
---
## 1. Scope & Risk
- Run:
  - `git status`
  - `git diff`
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
- Apply all checks from subskill
- Severity: P1 = must fix, P2 = improvement
---
## 3. Removal Candidates
- Read: `../skills/code-reviewer/subskills/plan-dead-code-removal.md`
- Apply all checks from subskill
---
## 4. Security & Concurrency
- Read: `../skills/code-reviewer/subskills/audit-security-reliability.md`
- Apply all checks from subskill
- Severity: P0 = exploitable, P1 = high risk, P2 = hardening
---
## 5. Reliability & Quality
- Read: `../skills/code-reviewer/subskills/check-quality-performance.md`
- Apply all checks from subskill
---
## 6. Testing & API Design
- First check if tests exist:
  - Look for: `test/`, `tests/`, `__tests__/`, `spec/`, `*_test.*`, `*.test.*`, `*.spec.*`
  - Or check for test scripts in `package.json`, `pytest.ini`, `phpunit.xml`, etc.
- If tests found:
  - Read: `../skills/code-reviewer/subskills/validate-testing-api-design.md`
  - Apply all checks from subskill
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
---
## 8. Confirmation Before Applying Fixes
After presenting findings, ask:
> How would you like to proceed?  
> (a) Fix all issues (P0–P3)  
> (b) Fix P0 and P1 only  
> (c) Fix specific items  
> (d) Review only — no changes  
Wait for explicit user confirmation before making any edits.
---
Constraints:
- Be concise
- Be evidence-based
- Avoid generic commentary