# SOLID & Architecture Review

Check changed files for design violations and code smells.

**Verification requirement**: Only report violations you can prove with a concrete scenario. Read the full file — not just the diff — before flagging. Respect the project's existing conventions; do not impose textbook SOLID on code that is reasonably structured for its context.
---
## 1. SRP (Single Responsibility)
- Flag:
  - File mixes unrelated concerns (HTTP + DB + domain in one file)
  - Class/module with low cohesion or multiple reasons to change
  - God objects that know too much
- Ask: "What is the single reason this module would change?"
---
## 2. OCP (Open/Closed)
- Flag:
  - New behavior requires editing switch/if blocks
  - Feature growth modifies core logic instead of extending
  - No plugin/strategy/hook points
- Ask: "Can I add a new variant without touching existing code?"
---
## 3. LSP (Liskov Substitution)
- Flag:
  - Subclass checks concrete type or throws for base method
  - Overrides weaken preconditions or strengthen postconditions
  - Subclass no-ops parent behavior
- Ask: "Can I substitute any subclass without the caller knowing?"
---
## 4. ISP (Interface Segregation)
- Flag:
  - Interfaces with many methods, most unused by implementers
  - Callers depend on broad interfaces for narrow needs
  - Empty/stub method implementations
- Ask: "Do all implementers use all methods?"
---
## 5. DIP (Dependency Inversion)
- Flag:
  - High-level logic depends on concrete IO/storage/network types
  - Hard-coded implementations instead of abstractions
  - Import chains coupling business logic to infrastructure
- Ask: "Can I swap the implementation without changing business logic?"
---
## 6. Dependency & Layer Integrity
- Flag:
  - Circular dependencies between modules/packages
  - Layer violations (controller → DB directly, skipping service layer)
  - Naming/convention inconsistency with existing codebase
  - Tight coupling between unrelated modules via shared mutable state
- Ask: "Does this follow the project's established layering?"
---
## 7. Common Code Smells
- Flag:
  - Long method (>30 lines, deep nesting)
  - Feature envy (method uses more of another class's data)
  - Data clumps (same params passed together repeatedly)
  - Primitive obsession (strings/numbers instead of domain types)
  - Shotgun surgery (one change → edits across many files)
  - Divergent change (one file changes for unrelated reasons)
  - Speculative generality (abstractions for hypothetical future)
  - Magic numbers/strings (hardcoded values without constants)
---
## 8. Refactor Heuristics
- Split by responsibility, not size
- Introduce abstraction only on second use case
- Keep refactors incremental — isolate before moving
- Preserve behavior first — add tests before restructuring
- Prefer composition over inheritance
- Make illegal states unrepresentable via types
---
## False positive filters
- Do NOT flag SRP for files that mix concerns if that is the project's established pattern (e.g., controller files that do validation + routing in Express/Rails/Django)
- Do NOT flag OCP for simple if/switch blocks with 2-3 branches — only flag when the pattern is clearly growing and hardening
- Do NOT flag ISP for interfaces with <5 methods — only flag genuinely bloated interfaces
- Do NOT flag DIP for direct imports of stable, well-known libraries (e.g., importing `fs`, `path`, `lodash`)
- Do NOT flag code smells that are standard practice in the project's ecosystem
- A file being "long" is not a violation — only flag if it genuinely mixes unrelated responsibilities
---
Severity:
- P1 = design violation that causes real maintenance or correctness problems, must fix
- P2 = code smell with a concrete downside, improvement
