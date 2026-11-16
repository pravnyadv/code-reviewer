# Quality & Performance Check

Check changed files for error handling, performance, and boundary issues.

**Verification requirement**: Before reporting, verify the issue is real in context:
1. Check if error handling exists at a higher level (middleware, error boundary, caller)
2. For performance flags, confirm the code is in a hot path — don't flag one-time startup code or admin endpoints
3. For boundary conditions, check if the type system or validation layer already prevents the bad input
---
## 1. Error Handling
- Flag:
  - Swallowed exceptions: empty catch or catch-and-log-only
  - Overly broad catch: base `Exception`/`Error` instead of specific types
  - Error leakage: stack traces or internals exposed to users
  - Missing error handling around I/O, network, parsing
  - Async gaps: unhandled promise rejections, missing `.catch()`, no error boundary
- Check:
  - Errors caught at appropriate boundaries
  - Messages are user-friendly, no internal details
  - Sufficient context logged for debugging
  - Fallback behavior for recoverable errors
  - Critical errors trigger alerts/monitoring
- Ask: "What happens when this fails? Will the caller know?"
---
## 2. Async & Concurrency Patterns
- Flag:
  - Sequential awaits that should be `Promise.all` / parallel
  - `Promise.all` without error handling (one rejection kills all)
  - Connection pool exhaustion from leaked connections
  - Deadlocks from nested locks or circular waits
  - Missing `finally` for resource cleanup (connections, streams, locks)
  - Callback hell / deeply nested async without proper chaining
- Ask: "Can these operations run in parallel? What if one fails?"
---
## 3. Logging Quality
- Flag:
  - Missing structured logging (no correlation/request IDs)
  - Wrong log levels (errors logged as info, debug noise in production)
  - Missing context in log entries (who, what, why)
  - No distinguishing between expected and unexpected errors
- Check:
  - Correlation IDs propagated across service boundaries
  - Log levels follow convention: error → actionable, warn → degraded, info → business events, debug → dev only
---
## 4. CPU & Computation
- Flag:
  - Expensive ops in hot paths (regex compilation, JSON parsing, crypto in loops)
  - Blocking main thread with sync I/O or heavy computation
  - Unnecessary recomputation — same calculation repeated
  - Missing memoization for pure functions with same inputs
---
## 5. Database & I/O
- Flag:
  - N+1 queries: loop makes one query per item instead of batch
  - Missing indexes on queried columns
  - Over-fetching: `SELECT *` when few columns needed
  - No pagination: loading entire dataset into memory
- Ask: "Can this be batched instead of one-by-one?"
---
## 6. Caching
- Flag:
  - Missing cache for repeated expensive operations
  - Cache without TTL (stale indefinitely)
  - No invalidation strategy (data updated, cache stale)
  - Cache key collisions (insufficient uniqueness)
  - User-specific data cached globally (privacy issue)
---
## 7. Memory
- Flag:
  - Unbounded collections (arrays/maps growing without limit)
  - Large object retention preventing GC
  - String concatenation in loops (use join/StringBuilder)
  - Loading large files entirely (use streaming)
- Ask: "How does this behave with 10x/100x data?"
---
## 8. Type Safety
- Flag:
  - Implicit `any` types (TypeScript) or missing type hints
  - Unchecked type assertions / unsafe casts
  - Runtime type checks that should be compile-time
  - Inconsistent use of strict mode / strict null checks
- Ask: "Would a type error here be caught at compile time or runtime?"
---
## 9. Null / Undefined
- Flag:
  - Missing null checks before property access
  - Truthy/falsy confusion: `if (value)` when `0` or `""` are valid
  - Optional chaining overuse hiding structural issues
  - Null vs undefined mixed without convention
---
## 10. Empty Collections
- Flag:
  - Code assumes array has items
  - `arr[0]` or `arr[arr.length-1]` without length check
  - `for...in` / `Object.keys` on potentially empty object
---
## 11. Numeric Boundaries
- Flag:
  - Division by zero without guard
  - Integer overflow beyond safe range
  - Float comparison with `===` instead of epsilon
  - Negative values for index/count
  - Off-by-one in loop bounds, slicing, pagination
---
## 12. String & Date Boundaries
- Flag:
  - Empty string not handled as edge case
  - Whitespace-only passes truthy but is effectively empty
  - No length limits (memory/display issues)
  - Unicode edge cases (emoji, RTL, combining characters)
  - Time zone mismatch (server vs client vs DB vs UTC)
  - Date parsing without explicit format (locale-dependent)
  - DST transitions causing skipped/duplicate events
---
## False positive filters
- Do NOT flag "missing error handling" if a try/catch or error boundary exists higher in the call chain
- Do NOT flag "swallowed exception" if the catch block handles the error appropriately for the context (e.g., returning a default, logging and continuing for non-critical ops)
- Do NOT flag sequential awaits as "should be parallel" if the operations depend on each other or if parallelism isn't safe (e.g., DB transactions)
- Do NOT flag "missing null check" when TypeScript strict null checks, required schema fields, or NOT NULL constraints guarantee the value
- Do NOT flag "empty/null edge case" when the value is guaranteed by the app's initialization flow, route params, required props, or guards (e.g., `accountUser` loaded from URL params before component renders, `beforeEach` guard awaiting data fetch before navigation)
- Do NOT flag "stale keys" or "unknown keys" when the API contract is bounded (e.g., backend returns exactly N known keys, no extra keys exist)
- Do NOT flag "default value is wrong" when the default/fallback is never actually reached due to initialization order (e.g., `beforeEach` loads real data before any code reads the defaults)
- Do NOT flag performance issues on code that runs once at startup, in tests, in CLI scripts, or on admin-only endpoints
- Do NOT flag `arr[0]` as unsafe if the surrounding code already checks array length or the array is guaranteed non-empty
- Do NOT flag "missing pagination" for internal queries with known bounded result sets
---
Severity:
- P1 = logic bug, silent failure, perf regression — with proof it actually happens
- P2 = code smell, missing guard — with a concrete scenario
- P3 = minor boundary hardening — only if realistic
