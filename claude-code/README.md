[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Claude Code Compatible](https://img.shields.io/badge/Claude%20Code-Compatible-blue)](https://claude.ai/code)
[![Docs](https://img.shields.io/badge/Docs-Read%20the%20manual-brightgreen)](../README.md)
[![JSONL](https://img.shields.io/badge/Protocol-JSONL-1f6feb)](#jsonl-repl-protocol-summary)
[![OpenTelemetry](https://img.shields.io/badge/Telemetry-OpenTelemetry-8A2BE2)](../codex/zeno/references/otel.md)
[![Codex Compatible](https://img.shields.io/badge/Codex-Compatible-blue)](https://platform.openai.com/)
[![Read-Only](https://img.shields.io/badge/Mode-Read--Only-ff69b4)](#budgets-and-guardrails-default-behavior)
[![Evidence-First](https://img.shields.io/badge/Policy-Evidence--First-2ea44f)](#output-blocks-required-for-persistence)

# Zeno for Claude Code (Project Scope)

<p align="center"><img src="../assets/zeno.png" width="50%" alt="Zeno"></p>

> **Recursive decomposition for unbounded codebase analysis.** Zeno is an evidence-first, read-only workflow that lets AI models analyze massive codebases without context rot -- by keeping the corpus external and pulling only what is needed.

## Table of Contents
- [Why Zeno? The Problem It Solves](#why-zeno-the-problem-it-solves)
- [What Makes Zeno Different](#what-makes-zeno-different)
- [Architecture](#architecture)
- [Core Ideas](#core-ideas)
- [The Name](#the-name)
- [When to Use Zeno](#when-to-use-zeno)
- [Budgets and Guardrails (Default Behavior)](#budgets-and-guardrails-default-behavior)
- [JSONL REPL Protocol (Summary)](#jsonl-repl-protocol-summary)
- [Output Blocks (Required for Persistence)](#output-blocks-required-for-persistence)
- [Persistence Artifacts (Where the Receipts Live)](#persistence-artifacts-where-the-receipts-live)
- [Security and Privacy Notes](#security-and-privacy-notes)
- [Performance Notes](#performance-notes)
- [Introduction](#introduction)
- [Folder layout](#folder-layout)
- [Quick start](#quick-start)
- [Verification](#verification)
- [Acknowledgments](#acknowledgments)

---

## Why Zeno? The Problem It Solves

Zeno targets long-context analysis where a model must understand a large codebase without loading it all at once. It keeps the corpus external and pulls only the small slices needed to answer each question.
For the full narrative and diagrams, see ../README.md.

---

## What Makes Zeno Different

- Evidence-first: every claim cites a file and line range.
- Recursive decomposition: large questions become smaller, auditable sub-queries.
- Deterministic retrieval: JSONL REPL ops keep context small and reproducible.

Reported results are benchmark-specific: OOLONG shows +28.4% (GPT-5) and +33.3% (Qwen3-Coder), and some settings show up to 2x gains vs long-context scaffolds and up to 3x lower cost vs summarization baselines. Results vary by model and task. (Source: https://arxiv.org/abs/2512.24601)

---

## Architecture

Zeno runs as a loop between the model and a JSONL REPL server, with a persistence layer that stores state, evidence, and claims. Optional telemetry (OTEL) can capture tool-level traces.

---

## Core Ideas

- Externalize context: keep the corpus in a REPL server, not in the prompt.
- Minimize retrieval: prefer peek and narrow read_file over whole-file loads.
- Evidence discipline: no evidence, no claim.
- Recursive inspection: summarize slices, then consolidate into a report.

---

## The Name

Zeno of Elea framed motion as repeated halving. That mirrors recursive inspection: split a big problem into smaller slices, then assemble the answer.

- The Dichotomy paradox divides a journey in half, then half again.
- The name signals infinite splitting and recursion.
- RLMs treat a too-long prompt as an external environment and decompose it into smaller subproblems.

---

## When to Use Zeno

- Large repos (hundreds or thousands of files)
- Long logs or traces where only a few lines matter
- Audits (security, concurrency, dependency wiring) that require citations
- Any analysis where you want reproducible, evidence-backed answers

---

## Budgets and Guardrails (Default Behavior)

Default caps (unless you explicitly ask for deeper coverage):

| Resource | Per Section | Per Answer |
|:---------|:-----------:|:----------:|
| Retrieval ops | <=12 | <=30 |
| `read_file` lines | - | <=2,000 total |
| `read_file` per call | - | <=400 lines |
| `grep` hits | - | <=200 per call |
| File capsules | - | <=12 |
| Recursion depth | - | <=2 |

If budgets are hit: stop, summarize, and provide a next retrieval plan.

---

## JSONL REPL Protocol (Summary)

Core operations exposed by the server:

| Operation | Purpose |
|:----------|:--------|
| `list_files` | Discovery |
| `peek` | Tiny previews |
| `read_file` | Specific line ranges |
| `grep` | Pattern-based narrowing |
| `extract_symbols` | Heuristic symbol lists |
| `stat` | File size and timestamp checks |

---

## Output Blocks (Required for Persistence)

Each Zeno response ends with three machine-parseable blocks:

- `ZENO_STATE_UPDATE_JSON`
- `ZENO_EVIDENCE_LEDGER_JSONL`
- `ZENO_CLAIM_LEDGER_JSONL`

---

## Persistence Artifacts (Where the Receipts Live)

**Codex (notify-based):**
```
.codex/zeno/
  state/<thread-id>.json
  evidence/<thread-id>.jsonl
  claims/<thread-id>.jsonl
  snapshots/<thread-id>/<turn-id>.json
  notify.log
```

**Claude Code (hooks-based):**
```
.claude/zeno/
  state/<thread-id>.json
  evidence/<thread-id>.jsonl
  claims/<thread-id>.jsonl
  snapshots/<thread-id>/<turn-id>.json
  notify.log
```

---

## Security and Privacy Notes

- Zeno is read-only by design; the server does not execute arbitrary code.
- Default OTEL prompt logging is off; enable only if required.
- Avoid logging secrets in evidence or claims; redact as needed.

---

## Performance Notes

- Prefer narrow grep patterns and short read_file slices.
- Use stat to skip huge or generated files.
- Expect slower runs on very large repos; Zeno favors reliability over speed.

---

## Introduction
Zeno is a way to read huge codebases without stuffing them into the model's memory. It keeps the big files outside the model, pulls only the few lines needed, and keeps receipts so every claim can be traced back to evidence.
Technical: This repo stores the Claude Code layout in `claude/` for visibility. Claude Code itself expects `.claude/` at runtime, so copy `claude/` to `.claude/` before use.

For the full project overview, see `../README.md`.

## Folder layout
```
claude/               # Repo-visible Claude Code layout (copy to .claude/)
  skills/zeno/        # Skill manual + scripts + references
  hooks/zeno.hooks.json
  settings.example.json
  zeno/               # Output artifacts (state/evidence/claims)
```

## Quick start
1) Copy the visible folder into the runtime location:
   - `rsync -a claude/ .claude/`
   - or from repo root: `./scripts/sync_claude.sh`
2) Merge `.claude/hooks/zeno.hooks.json` into `.claude/settings.json`.
3) Optionally merge `.claude/settings.example.json` for OTEL env settings.
4) Run `/hooks` in Claude Code to refresh hook registrations.

## Verification
- Run `claude --debug` and confirm hooks fire.
- Check `.claude/zeno/notify.log` after a turn.

## Acknowledgments
This skill is inspired by and references:
- Zhang et al., "Recursive Language Models" (arXiv:2512.24601v1): https://arxiv.org/abs/2512.24601v1
- Alex Zhang's reference implementation: https://github.com/alexzhang13/rlm
- Original announcement thread: https://x.com/a1zhang/status/2007566581409144852?s=46
- Prime Intellect's RLM research: https://www.primeintellect.ai/blog/rlm

Thank you to Alex Zhang and collaborators for the Zeno concept and open resources that informed this work.
