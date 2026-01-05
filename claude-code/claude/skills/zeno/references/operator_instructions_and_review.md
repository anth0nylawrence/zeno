# Zeno - Operator Instructions and Review

## Plain-English context
ELI5: This document is the rulebook for how to run the skill and a frank review of what still needs to improve. It tells you how to read huge codebases without stuffing everything into the model, and it explains the weak spots you should fix next.
Technical: This is a combined operator manual and implementation review. It defines the execution contract, evidence mechanics, budgets, stop rules, and a concrete 10x roadmap for hardening the system.

---

## A) Operator instructions to the LLM (do this every time)

### A0) Claude Code hooks are the engine
ELI5: The helpers are always on, and the skill is the rulebook.
Technical:
- Hooks persist state and inject memory every turn.
- The skill text is policy and output requirements.

### A1) The contract
ELI5: Treat the external server like the library. Only talk about what you actually read.
Technical:
- The external REPL server is the source of truth.
- Only claim what you can cite with path:Lx-Ly or a grep hit.
- Keep retrieval tight: peek -> narrow with grep -> small read_file slices.

### A2) Default budgets
ELI5: You only get a small number of page requests, so use them wisely.
Technical:
- <= 30 retrieval ops per answer, <= 12 per section.
- <= 2000 total lines returned across the answer.
- If budget hit: STOP, summarize, output Next Retrieval Plan.

### A3) Evidence discipline (mechanical)
ELI5: Give every important sentence a receipt.
Technical:
- Maintain an evidence registry: E1, E2, E3, E4 each is path + line range or a grep hit.
- Output a Claim Ledger:
  - C1 -> [E1, E4]
  - C2 -> [E2]
- If you cannot attach an E#, move it to Open Questions.

### A4) Stop rules (prevent infinite exploring)
ELI5: Stop searching when you already have enough to answer the question.
Technical:
Stop retrieval and write the report when:
- You have entrypoints + lifecycle + top module map.
- Additional retrieval repeats the same patterns.
- You are within 20 percent of any budget.

Always include Open Questions and a Next Retrieval Plan.

### A5) Failure-mode playbooks
ELI5: If you get stuck, do a small, predictable move.
Technical:
- grep truncated -> narrow by paths and use a more specific pattern.
- big file -> peek then read_file on targeted blocks only.
- uncertainty -> move to Open Questions, then list the next 3-10 ops.

---

## B) Candid review of the current implementation

### B1) Strengths
ELI5: The system is safe and predictable in the basics.
Technical:
- Root sandboxing prevents path traversal.
- Default excludes reduce noise.
- JSONL protocol is deterministic and log-friendly.

### B2) Weaknesses
ELI5: It works, but it is not yet fast or safe enough for heavy use.
Technical:
1) Performance: read_file, peek, and grep load entire files into memory.
   Status update: read_file now streams line ranges; peek and grep still scan files line-by-line (no full-buffer load, but still O(n) per file).
2) Regex risk: grep uses regex by default and can hang on pathological patterns.
   Status update: grep now defaults to literal matching; regex is opt-in via `regex=true`.
3) Missing ops: no stat, no literal grep, no timing metrics, no dependency index.
   Status update: stat, literal grep default, and timing/byte metrics were added; import/dependency index remains a gap.

Impact:
- Slow scans on large repos.
- Occasional agent stalls.
- Harder to measure coverage and performance.
Remaining impact after fixes:
- Large files can still be expensive to scan, especially with broad grep patterns.
- No native import/dependency index yet, so wiring maps still require manual greps.

---

## C) 10x roadmap (prioritized)

### P0 - Make the skill enforce behavior
ELI5: Tight rules stop drift and hallucination.
Technical:
1) Keep SKILL.md strict with budgets and Claim Ledger.
2) Add explicit failure-mode playbooks.

### P1 - Make docs complete
ELI5: Clear rules prevent wrong tool usage.
Technical:
3) Keep protocol.md complete, with full schemas and defaults.
4) Keep README and operator docs up to date.

### P1 - Harden the server
ELI5: Make it fast and safe even for huge repos.
Technical:
5) Add safe grep mode (literal by default, regex opt-in).
6) Stream line-range reads to avoid loading whole files.
7) Add stat op (size, mtime) to skip large/generated files.
8) Add timing and byte metrics in responses.
9) Add basic import index op for fast wiring maps.

### P2 - Evaluation and linting
ELI5: Tests keep the system honest.
Technical:
10) Golden fixture repo + expected report.
11) Log linter for claims without evidence and budget violations.
12) Regression checks for doc placeholders and op mismatch.

### P3 - Usability
ELI5: Make it easy to run and reuse.
Technical:
13) Ship a tiny client CLI for JSONL requests and log tailing.
14) Provide recipes for common stacks (Swift, Node, Python, Rust).
15) Add a context bridge script to emit a prompt-ready summary for the next turn.

---

## D) Non-obvious risks

### D1) Goodharting evidence
ELI5: The model might cite the wrong line just to satisfy the rule.
Technical: Require a one-line justification for why the evidence proves the claim.

### D2) Recall bias
ELI5: Searching only what you expect can miss the truth.
Technical: Phase 1 must include a neutral repo map before hypothesis greps.

### D3) Coverage illusion
ELI5: A nice report can still be based on shallow sampling.
Technical: Always report coverage: files sampled, greps run, lines read.

---

## E) Definition of done
ELI5: You are done when the system is safe, tested, and auditable.
Technical:
- SKILL.md enforces budgets + Claim Ledger + strict output schema.
- protocol.md has no placeholders and matches server behavior.
- Server supports safe grep, streaming reads, stat, timing.
- Golden fixture + log linter + regressions exist.
- Full replay from JSONL logs is possible.

## Acknowledgments
This skill is inspired by and references:
- Zhang et al., "Recursive Language Models" (arXiv:2512.24601v1): https://arxiv.org/abs/2512.24601v1
- Alex Zhang's reference implementation: https://github.com/alexzhang13/rlm
- Original announcement thread: https://x.com/a1zhang/status/2007566581409144852?s=46

Thank you to Alex Zhang and collaborators for the Zeno concept and open resources that informed this work.