# Security & Reliability Audit

Check changed files for vulnerabilities, auth gaps, and concurrency issues.

**Verification requirement**: Security findings have the highest false-positive rate. Before reporting, you MUST:
1. Confirm the vulnerability is reachable — trace the data flow from user input to the flagged line
2. Check if the framework or middleware already mitigates it (e.g., ORM parameterization, React auto-escaping, CSRF middleware)
3. Distinguish between test/dev code and production code — test fixtures with "hardcoded secrets" are not vulnerabilities
4. Only flag supply chain / dependency issues if you can confirm a specific CVE or version range
---
## 1. Input/Output Safety
- Flag:
  - XSS: `dangerouslySetInnerHTML`, unescaped templates, `innerHTML`
  - Injection: SQL/NoSQL/command/GraphQL via string concatenation
  - SSRF: user-controlled URLs hitting internal services without allowlist
  - Path traversal: user input in file paths without sanitization
  - Prototype pollution: unsafe `Object.assign`/spread with user input
  - Open redirect: unvalidated redirect URLs from user input
  - Mass assignment: accepting all request body fields without allowlist
---
## 2. AuthN / AuthZ
- Flag:
  - Missing tenant or ownership checks on read/write
  - New endpoints without auth guards or RBAC
  - Trusting client-provided roles/flags/IDs
  - IDOR (Insecure Direct Object Reference)
  - Session fixation or weak session management
---
## 3. JWT & Token Security
- Flag:
  - Algorithm confusion (`none` or `HS256` when expecting `RS256`)
  - Weak or hardcoded secrets
  - Missing or unvalidated `exp`, `iss`, `aud`
  - Sensitive data in JWT payload (base64, not encrypted)
---
## 4. Secrets & PII
- Flag:
  - API keys, tokens, credentials in code/config/logs
  - Secrets in git history or client-exposed env vars
  - Excessive PII in logs or error messages
  - Missing data masking
  - Logging sensitive request/response bodies in middleware
---
## 5. File Uploads
- Flag:
  - Unrestricted file type or size
  - Storing uploads in webroot (direct execution risk)
  - Missing virus/malware scanning
  - User-controlled filenames used without sanitization
  - No content-type validation (relying only on extension)
---
## 6. Supply Chain & Dependencies
- Flag:
  - Unpinned dependencies
  - Dependency confusion (private name collision)
  - Untrusted CDN imports without integrity checks
  - Known CVEs in outdated dependencies
---
## 7. CORS & Headers
- Flag:
  - `Access-Control-Allow-Origin: *` with credentials
  - Missing security headers (CSP, X-Frame-Options, X-Content-Type-Options)
  - Exposed internal headers or stack traces
---
## 8. Runtime Risks
- Flag:
  - Unbounded loops, recursion, large in-memory buffers
  - Missing timeouts/retries/rate limiting on external calls
  - Sync I/O blocking async context
  - Resource exhaustion (file handles, connections, memory)
  - ReDoS (catastrophic backtracking in regex)
---
## 9. Cryptography
- Flag:
  - Weak algorithms (MD5, SHA1 for security)
  - Hardcoded IVs or salts
  - Encryption without authentication (ECB, no HMAC)
  - Insufficient key length
---
## 10. Race Conditions
- Flag:
  - Shared state without synchronization (globals, singletons, lazy init)
  - TOCTOU: `if (exists) then use` without atomic ops
  - Check-then-act: balance/inventory check → deduction without lock
  - Read-modify-write without transaction isolation
  - Missing optimistic/pessimistic locking in DB
  - Counter increments without atomic operations
  - Distributed: missing locks, cache invalidation races, split-brain
- Ask:
  - "What happens if two requests hit this simultaneously?"
  - "Is this operation atomic?"
  - "What shared state does this access?"
---
## 11. Data Integrity
- Flag:
  - Missing transactions or partial writes
  - Weak validation before persistence
  - Missing idempotency for retryable operations
  - Lost updates from concurrent modifications
---
## False positive filters
- ORM/query-builder parameterized queries are NOT SQL injection — do not flag `User.find({ id })` or `db.query("SELECT * FROM x WHERE id = $1", [id])`
- React JSX auto-escapes — do not flag `{variable}` in JSX as XSS (only flag `dangerouslySetInnerHTML` with user input)
- Framework CSRF protection — do not flag CSRF if Django/Rails/Express has CSRF middleware enabled
- Test files with hardcoded tokens/passwords — not a secret leak
- `process.env.X || "default"` in dev/test config — only flag if it runs in production
- Internal service-to-service endpoints — do not flag missing rate limiting or public auth
- bcrypt/argon2 usage — do not flag as "weak crypto" (they are strong password hashing)
- UUIDs as identifiers — not an IDOR vulnerability by themselves
---
Severity:
- P0 = exploitable vulnerability or data loss — must be provably reachable
- P1 = high risk, auth/crypto flaw — must show a concrete attack scenario
- P2 = hardening, defense-in-depth — nice to have, not blocking
