# Testing & API Design Validation

Check changed files for test coverage gaps, test quality, and API contract issues.
---
## Precondition
- Before running checks, verify tests exist in the project:
  - Look for: `test/`, `tests/`, `__tests__/`, `spec/`, `*_test.*`, `*.test.*`, `*.spec.*`
  - Or: test runner config (`package.json` scripts, `pytest.ini`, `phpunit.xml`, `jest.config.*`, `.mocharc.*`)
- If no tests found:
  - Skip all testing checks (§1–§3)
  - Still apply API design checks (§4–§5)
  - Note in output: "No test suite detected — consider adding tests for critical paths"
---
## 1. Test Coverage
- Flag:
  - New/changed logic without corresponding tests
  - Critical paths (auth, payments, data writes) lacking tests
  - Only happy-path tested — no error/edge case coverage
  - Deleted tests without explanation or replacement
- Ask: "If this breaks in production, would a test catch it?"
---
## 2. Test Quality
- Flag:
  - Testing implementation details instead of behavior
  - Brittle assertions (exact string match, snapshot bloat)
  - Tests that pass when the feature is broken (false positives)
  - Shared mutable state between tests (order-dependent)
  - Flaky patterns: time-dependent, network-dependent, race-prone
  - Over-mocking: mocking everything, testing the mock not the code
  - Mocking what you don't own (third-party internals)
- Check:
  - Each test has a single clear assertion / intent
  - Test names describe the behavior, not the method
  - Setup/teardown properly isolates test state
---
## 3. Testability
- Flag:
  - Code that is hard to test without refactoring:
    - Side effects in constructors
    - Hidden dependencies (new inside methods, static calls)
    - Global state accessed directly
    - Deep inheritance chains requiring complex setup
  - Missing dependency injection points
  - Non-deterministic behavior without seams (time, random, network)
- Ask: "Can I test this in isolation without standing up the whole system?"
---
## 4. API Contract Design
- Flag:
  - Breaking changes to public APIs without versioning
  - Inconsistent naming across endpoints (camelCase vs snake_case)
  - Inconsistent response shapes (some wrap in `data`, some don't)
  - Missing input validation at API boundary
  - Undocumented error responses / status codes
  - Missing pagination on list endpoints
  - Missing rate limiting on public endpoints
  - Exposing internal IDs or implementation details in response
- Ask: "Would a consumer break if they upgraded to this version?"
---
## 5. API Compatibility
- Flag:
  - Removed or renamed fields without deprecation period
  - Changed response status codes for existing behavior
  - New required fields on existing request schemas
  - Changed default values silently
  - Enum values removed without negotiation
- Check:
  - Additive changes only (new optional fields, new endpoints)
  - Deprecation warnings before removal
  - Versioned APIs for breaking changes
---
Severity:
- P1 = missing test for critical path, breaking API change
- P2 = test quality issue, inconsistent API design
- P3 = missing edge case test, naming inconsistency
