# Quality & Performance Check

Check changed files for error handling, performance, and boundary issues.
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
Severity:
- P1 = logic bug, silent failure, perf regression
- P2 = code smell, missing guard
- P3 = minor boundary hardening
