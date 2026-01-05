---
name: zeno
description: Persistent structured memory + telemetry + audit trail for Claude Code sessions. Use when the user wants automated capture, durable context, and standardized turn-by-turn logging.
allowed-tools: Read, Write, Bash(python:*), Bash(jq:*)
---

# Zeno (Lean Skill)

Zeno is an evidence-first, read-only workflow for huge corpora. Keep the corpus external (JSONL REPL), retrieve only minimal slices, and cite every non-trivial claim.

## How this skill is triggered (and when to use it)
Zeno activates when the user explicitly asks for Zeno or names a mode. Common triggers:
- "Use Zeno codebase-archaeology to trace <symbol> across the repo."
- "Run Zeno security-audit on src/ and build evidence chains."
- "Use Zeno architecture-mapping to document entrypoints and lifecycle."
- "Zeno pr-review these changed files: ... with downstream impact."
- "Zeno skill-generation on this repo and draft SKILL.md."
- "Zeno deep-research on this project question: ..."

Full use cases and mode details are defined in `references/modes.md`.

## Hooks and automation (Claude Code)
Hooks provide always-on persistence and context injection. If the user expects standardized memory every turn, ensure the hooks are installed and verified. See:
- `references/skill_full.md` (full manual)
- `references/skill_blocks.md` (mandatory output blocks)

## Non-negotiables
- READ-ONLY: do not modify files unless explicitly requested later.
- No evidence, no claim: every claim must cite `path:Lx-Ly` or a grep hit.
- Small bites: prefer `peek` + targeted `read_file` slices.
- Be deterministic: if unsure, retrieve more evidence.

## Tools available
- `list_files`, `peek`, `read_file`, `grep`, `extract_symbols`, `stat`

## Budgets (summary)
- Retrieval ops: <=30 per answer, <=12 per section
- `read_file`: <=400 lines per call, <=2,000 total
- `grep`: <=200 hits per call (narrow if truncated)
- Recursion: <=12 capsules, depth <=2
- If a budget is hit: stop, summarize, provide Next Retrieval Plan

## Mode selection (quick)
- codebase-archaeology, security-audit, architecture-mapping, pr-review, skill-generation, deep-research
Detailed mode playbooks: `references/modes.md`.

## Mandatory output blocks
Always append the three machine-parseable blocks at the end of every response. Format is defined in:
- `references/skill_blocks.md`

## NON-NEGOTIABLE: Read the full manual
Before using Zeno in a real task, you MUST read the full manual and follow it. This lean SKILL is only a pointer.

Read these in order:
- `references/skill_full.md` (complete operating manual, required)
- `references/skill_blocks.md` (mandatory output blocks, required)
- `references/operator_instructions_and_review.md` (operator-grade rules)
- `references/recipes.md` (copy/paste retrieval plans)
- `references/protocol.md` (JSONL REPL protocol)
- `references/security.md` and `references/otel.md`
