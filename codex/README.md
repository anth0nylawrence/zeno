[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Claude Code Compatible](https://img.shields.io/badge/Claude%20Code-Compatible-blue)](https://claude.ai/code)
[![Docs](https://img.shields.io/badge/Docs-Read%20the%20manual-brightgreen)](../README.md)
[![JSONL](https://img.shields.io/badge/Protocol-JSONL-1f6feb)](#jsonl-repl-protocol-summary)
[![OpenTelemetry](https://img.shields.io/badge/Telemetry-OpenTelemetry-8A2BE2)](../codex/zeno/references/otel.md)
[![Codex Compatible](https://img.shields.io/badge/Codex-Compatible-blue)](https://platform.openai.com/)
[![Read-Only](https://img.shields.io/badge/Mode-Read--Only-ff69b4)](#budgets-and-guardrails-default-behavior)
[![Evidence-First](https://img.shields.io/badge/Policy-Evidence--First-2ea44f)](#output-blocks-required-for-persistence)

# Zeno Skill - Detailed Documentation

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
- [What this skill is](#what-this-skill-is)
- [Why it matters](#why-it-matters)
- [How it works (high-level flow)](#how-it-works-high-level-flow)
- [Components](#components)
- [The Zeno loop (detailed)](#the-zeno-loop-detailed)
- [Evidence discipline](#evidence-discipline)
- [Determinism and safety](#determinism-and-safety)
- [How to use it with Codex (step-by-step)](#how-to-use-it-with-codex-step-by-step)
- [CLI checkpoint signal](#cli-checkpoint-signal)
- [Context bridge](#context-bridge)
- [Flags and help](#flags-and-help)
- [Example workflow](#example-workflow)
- [Trajectory logs and visualization](#trajectory-logs-and-visualization)
- [Notify payload (what the hook receives)](#notify-payload-what-the-hook-receives)
- [Non-interactive mode](#non-interactive-mode)
- [How this transforms coding agents](#how-this-transforms-coding-agents)
- [Limitations and tradeoffs](#limitations-and-tradeoffs)
- [Extending the system](#extending-the-system)
- [Folder layout in this directory](#folder-layout-in-this-directory)
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
Technical: This is a Codex skill that implements a recursive retrieval loop. It stores large corpora outside the model context, pulls small slices on demand, and optionally recurses on slices for focused summaries. It avoids context bloat and enforces evidence-backed analysis.

For the full project overview, see `../README.md`.

## What this skill is
ELI5: It is a set of instructions that teach Codex to read huge codebases or documents by taking tiny bites instead of swallowing everything at once.
Technical: The skill defines a read-only workflow that uses a JSONL REPL server to list files, read line ranges, grep patterns, and extract symbols. It supports recursive sub-analysis to summarize slices without loading the full corpus into context.

## Why it matters
ELI5: If you try to read everything at once, you get confused and forget earlier pages. This skill keeps your attention on the right pages and helps you remember what matters.
Technical: Large contexts cause cost spikes, latency, and degraded reasoning. This skill mitigates context rot by using strict retrieval budgets, evidence discipline, and a deterministic interface for slicing data. It improves reliability and repeatability for large-scale analysis tasks.

## How it works (high-level flow)
ELI5: You ask a question, the helper checks the shelf for the right book, reads just a few pages, and tells you what those pages mean. If the pages are still too big, it asks another helper to read just that chunk, then combines the notes.
Technical:
1. Store the corpus in an external REPL server (read-only).
2. Use list/peek/grep to identify the minimum evidence.
3. Read small slices by line range.
4. Optionally recurse on slices (subcalls) for summaries.
5. Consolidate results with citations and warn on partial coverage.

## Components

### 1) The Codex skill
ELI5: This is the rulebook that tells Codex how to behave.
Technical: `zeno/SKILL.md` defines the triggering description, guardrails, Zeno loop steps, subcall templates, and output format. It is intentionally concise to reduce context load.

### 2) The REPL server
ELI5: This is the librarian. You ask for a page, it brings it back.
Technical: `zeno/scripts/zeno_server.py` is a tiny JSONL server that exposes `list_files`, `read_file`, `grep`, `peek`, and `extract_symbols`. It is read-only, deterministic, and constrained to a root directory.

### 3) The protocol reference
ELI5: This is the instruction manual for how to ask the librarian.
Technical: `zeno/references/protocol.md` defines JSONL request/response envelopes, op schemas, defaults, constraints, and logging recommendations.

### 4) The client CLI
ELI5: This is a small remote control for asking the librarian one question at a time.
Technical: `zeno/scripts/zeno_client.py` sends a single JSONL request, pretty-prints the response, and can tail JSONL logs for live debugging.

### 5) Recipes
ELI5: These are ready-made question scripts for common stacks.
Technical: `zeno/references/recipes.md` includes copy/paste JSONL request sequences for Swift, Node, Python, and Rust entrypoint discovery.

### 6) Trajectory logging
ELI5: This is a breadcrumb trail of everything the helper asked for, so you can replay or audit it later.
Technical: The server can log JSONL events for every request and response. Agents can add higher-level events like claims and subcalls for visualization.

### 7) Pattern A: per-turn persistence (notify)
ELI5: After every turn, a helper saves the receipts so you never lose the evidence trail.
Technical: `zeno/scripts/notify_persist.py` is wired via Codex `notify`. It extracts the three Zeno blocks from the last assistant message and persists them under `.codex/zeno/` as state/evidence/claims ledgers plus per-turn snapshots.

### 8) Pattern B: high-fidelity telemetry (OTEL)
ELI5: This is a live stream of every tool decision so you can replay the run later.
Technical: Codex exports OTEL events to a local collector (`zeno/configs/otel-collector.yaml`) which writes JSONL logs for replay and audit. This complements Pattern A by capturing tool-level traces.

## The Zeno loop (detailed)
ELI5: First decide where to look, then peek at small parts, explain what you see, and keep going until you have enough to answer the question.
Technical:
- Plan: identify entrypoints, config, routing, and DI boundaries.
- Retrieve: use list/grep/peek to locate minimal evidence.
- Interpret: explain what the excerpt implies.
- Recurse: summarize complex slices with subcalls.
- Consolidate: stitch findings with citations.
- Log: record each retrieval and conclusion.

## Evidence discipline
ELI5: Do not guess. Show the page number for every important claim.
Technical: Every non-trivial assertion must be backed by a file path and a line range or grep hit. If evidence is missing, retrieve more or mark uncertainty.

## Determinism and safety
ELI5: The helper should always behave the same way and never change the library.
Technical: The server never writes to disk, never executes arbitrary code, and never accesses paths outside `--root`. It sorts paths and hits for stable ordering and caps output sizes.

## How to use it with Codex (step-by-step)

### Step 1: Start the REPL server
ELI5: Turn on the librarian.
Technical:
```bash
python3 /Users/anthony/.codex/skills/zeno/scripts/zeno_server.py \
  --root /path/to/repo \
  --log /tmp/zeno_trace.jsonl
```

### Step 2: Send JSONL requests
ELI5: Ask for a list of pages or a tiny slice.
Technical:
```json
{"id":"req-1","op":"list_files","args":{"glob":"**/*.swift","max":200}}
{"id":"req-2","op":"read_file","args":{"path":"Blaze/Sources/App/AppCoordinator.swift","start_line":1,"end_line":200}}
```

Optional: use the client CLI for one-off requests:
```bash
python3 /Users/anthony/.codex/skills/zeno/scripts/zeno_client.py send \
  --root /path/to/repo \
  --op list_files \
  --args '{"glob":"**/*.swift","max":200}' \
  --pretty
```

### Step 3: Use the results in your analysis
ELI5: Read the page, then write your notes with citations.
Technical: Use the returned `path` and `start_line`/`end_line` as evidence for claims. Avoid copying whole files.

### Step 4: Wire persistence and telemetry (optional but recommended)
ELI5: Turn on the recorder so you can replay the run later.
Technical:
1) Add this to `~/.codex/config.toml`:
```toml
notify = ["python3", "/ABS/PATH/zeno/scripts/notify_persist.py"]

[history]
max_bytes = 104857600

[otel]
environment = "prod"
exporter = "otlp-http"
log_user_prompt = false
```
2) Start the collector from `zeno/configs/otel-collector.yaml`.

## CLI checkpoint signal
ELI5: Watch a live “checkpoint saved” stream in a second terminal.
Technical:
```bash
tail -f /path/to/repo/.codex/zeno/notify.log
```

## Context bridge
ELI5: Print a small memory card you can paste into the next prompt.
Technical:
```bash
python3 zeno/scripts/zeno_context_bridge.py --zeno-root /path/to/repo/.codex/zeno
```

## Flags and help
ELI5: The helper scripts accept flags; `--help` shows them.
Technical:
```bash
python3 zeno/scripts/zeno_context_bridge.py --help
python3 zeno/scripts/zeno_client.py --help
```
Common flags:
- `zeno_context_bridge.py`: `--zeno-root`, `--thread-id`, `--max-evidence`, `--max-claims`, `--json`
- `zeno_client.py`: `send|tail`, `--op`, `--args`, `--request`, `--pretty`, `--log`, `--lines`, `--follow`

## Example workflow
ELI5: Find the front door, read the welcome sign, then trace where visitors go.
Technical:
1) `list_files` for entrypoints and configs.
2) `grep` for "main", "App", "Router", "Coordinator".
3) `read_file` small ranges for key files.
4) Subcall: summarize each file (file capsule).
5) Consolidate into a wiring map with citations.

## Trajectory logs and visualization
ELI5: Keep a timeline of every question and answer so you can replay it.
Technical: The server logs request/response JSONL. Agents can add `claim` events with evidence. This enables timeline views, graph views (claims -> evidence), and coverage heatmaps.

## Notify payload (what the hook receives)
ELI5: Codex sends a tiny summary note after each turn so the helper knows what just happened.
Technical: The notify hook receives a single JSON argument with fields like `type`, `thread-id`, `turn-id`, `cwd`, `input-messages`, and `last-assistant-message`. The helper parses these to persist state and evidence.

## Non-interactive mode
ELI5: This works even when Codex runs in the background.
Technical: The notify hook and OTEL exporter work in interactive TUI sessions and `codex exec` automation runs, as long as the config keys are set.

## How this transforms coding agents
ELI5: The agent stops drowning in information and starts making careful, provable observations.
Technical: This workflow scales analysis to very large repos without exploding context windows. It reduces hallucinations via evidence discipline, makes analysis auditable via logs, and enables recursive decomposition of complex files.

## Limitations and tradeoffs
ELI5: You still have to pick which pages to read, and you might miss something if you never look there.
Technical: Retrieval is only as good as the search strategy. The default symbol extraction is heuristic. Large binary files are skipped. Partial sampling requires explicit caveats in conclusions.

## Extending the system
ELI5: You can teach the librarian new tricks.
Technical: Replace `extract_symbols` with tree-sitter, add a persistent index, or integrate embeddings for semantic search. The JSONL protocol stays stable.

## Folder layout in this directory
ELI5: The skill files live in a subfolder, and this README explains the whole system.
Technical:
```
$REPO_ROOT/codex/
  README.md
  zeno/
    SKILL.md
    README.md
    configs/example.config.toml
    configs/otel-collector.yaml
    scripts/zeno_server.py
    scripts/zeno_client.py
    scripts/notify_persist.py
    scripts/log_lint.py
    scripts/rotate_history.py
    scripts/verify_evidence.py
    references/protocol.md
    references/recipes.md
    references/operator_instructions_and_review.md
    references/data_model.md
    references/security.md
    references/otel.md
    references/troubleshooting.md
    examples/
    tests/
```

## Acknowledgments
This skill is inspired by and references:
- Zhang et al., "Recursive Language Models" (arXiv:2512.24601v1): https://arxiv.org/abs/2512.24601v1
- Alex Zhang's reference implementation: https://github.com/alexzhang13/rlm
- Original announcement thread: https://x.com/a1zhang/status/2007566581409144852?s=46
- Prime Intellect's RLM research: https://www.primeintellect.ai/blog/rlm

Thank you to Alex Zhang and collaborators for the Zeno concept and open resources that informed this work.
