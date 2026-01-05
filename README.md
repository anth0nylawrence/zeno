[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Claude Code Compatible](https://img.shields.io/badge/Claude%20Code-Compatible-blue)](https://claude.ai/code)
[![Docs](https://img.shields.io/badge/Docs-Read%20the%20manual-brightgreen)](README.md)
[![JSONL](https://img.shields.io/badge/Protocol-JSONL-1f6feb)](#jsonl-repl-protocol-summary)
[![OpenTelemetry](https://img.shields.io/badge/Telemetry-OpenTelemetry-8A2BE2)](codex/zeno/references/otel.md)
[![Codex Compatible](https://img.shields.io/badge/Codex-Compatible-blue)](https://platform.openai.com/)
[![Read-Only](https://img.shields.io/badge/Mode-Read--Only-ff69b4)](#budgets-and-guardrails-default-behavior)
[![Evidence-First](https://img.shields.io/badge/Policy-Evidence--First-2ea44f)](#output-blocks-required-for-persistence)

# Zeno

<p align="center"><img src="assets/zeno.png" width="50%" alt="Zeno"></p>

> **Recursive decomposition for unbounded codebase analysis.** Zeno is an evidence-first, read-only workflow that lets AI models analyze massive codebases without context rot—by keeping the corpus external and pulling only what's needed.

## Table of Contents
- [Why Zeno? The Problem It Solves](#why-zeno-the-problem-it-solves)
- [What Makes Zeno Different](#what-makes-zeno-different)
- [Architecture](#architecture)
- [Core Ideas](#core-ideas)
- [When to Use Zeno](#when-to-use-zeno)
- [Modes](#modes)
- [Triggering Zeno (Natural Language Examples)](#triggering-zeno-natural-language-examples)
- [Indexing (Symbol + Dependency Map)](#indexing-symbol--dependency-map)
- [Budgets and Guardrails](#budgets-and-guardrails-default-behavior)
- [JSONL REPL Protocol](#jsonl-repl-protocol-summary)
- [Output Blocks](#output-blocks-required-for-persistence)
- [Persistence Artifacts](#persistence-artifacts-where-the-receipts-live)
- [Security and Privacy](#security-and-privacy-notes)
- [Performance Notes](#performance-notes)
- [Repo Layout](#repo-layout)
- [Choose Your Runtime](#choose-your-runtime)
- [How the Zeno Loop Works](#how-the-zeno-loop-works)
- [Evidence and Claims](#evidence-and-claims)
- [Pattern A (Persistence)](#pattern-a-persistence)
- [Pattern B (Telemetry)](#pattern-b-telemetry)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Next Steps](#next-steps)
- [Acknowledgments](#acknowledgments)

---

## Why Zeno? The Problem It Solves

**Picture this:** You need to understand a 500k-line codebase—trace a security vulnerability, audit dependency wiring, or map out the architecture. Traditional approaches hit hard limits fast.

### Without Zeno

```
📁 Your massive codebase (500k+ lines)
    ↓
🤖 "Paste the relevant files..."
    ↓
😤 Context window fills up after 3 files
    ↓
🔄 Model starts "forgetting" earlier context (context rot)
    ↓
❌ Hallucinated connections, missed dependencies
    ↓
🗑️ Unreliable analysis you can't verify or reproduce
```

### With Zeno

```
📁 Your massive codebase (500k+ lines)
    ↓
🔍 Zeno keeps corpus external in REPL server
    ↓
📎 Model pulls only the 50-100 lines it needs per query
    ↓
🧠 Fresh context window for each recursive inspection
    ↓
📋 Every claim backed by evidence with file:line citations
    ↓
✅ Auditable, reproducible analysis with receipts
```

The key insight from Recursive Language Models (RLMs) research: instead of stuffing everything into the prompt, treat the codebase as an **external environment** that the model can programmatically explore, decompose, and query recursively.

---

## What Makes Zeno Different

Zeno isn't just another RAG pipeline or code search tool. It's an **evidence-first analysis workflow** implementing the RLM paradigm—the same approach that achieved 2.7x accuracy improvements on long-context benchmarks by letting models manage their own context.

### The RLM Advantage

Traditional approaches suffer from "context rot"—as token count increases, the model's ability to accurately recall and reason degrades. RLMs solve this by:

1. **Externalizing context**: The corpus lives in a REPL server, not the prompt
2. **Recursive decomposition**: Complex queries split into sub-queries over smaller slices
3. **Programmatic exploration**: `grep`, `peek`, `read_file`—surgical retrieval, not bulk loading
4. **Evidence discipline**: No claim without a citation; every answer is verifiable

### Capability Comparison

| Capability | Zeno | RAG Pipelines | IDE Copilots | Code Search | Full-Context Models |
|:-----------|:----:|:-------------:|:------------:|:-----------:|:-------------------:|
| **Unbounded corpus size** | ✅ | ❌ | ❌ | ✅ | ❌ |
| **Evidence-cited claims** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Recursive decomposition** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Retrieval budgets** | ✅ | Partial | ❌ | ❌ | ❌ |
| **Claim-evidence ledger** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Multi-runtime support** | ✅ | Partial | ❌ | ❌ | ❌ |
| **Read-only by design** | ✅ | Varies | ❌ | ✅ | ✅ |
| **No external indexing** | ✅ | ❌ | ❌ | ❌ | ✅ |
| **Telemetry/replay audit** | ✅ | Partial | ❌ | ❌ | ❌ |

### Why This Matters

**RAG pipelines** chunk and embed your code, but semantic similarity doesn't capture execution flow, dependency graphs, or cross-file relationships. You get "related snippets," not traced evidence.

**IDE copilots** work great for local edits but struggle with architectural questions spanning hundreds of files. They optimize for autocompletion, not audit trails.

**Full-context models** (even with 200k+ tokens) degrade on complex retrieval tasks. Reported results are benchmark-specific: OOLONG shows +28.4% (GPT-5) and +33.3% (Qwen3-Coder), and some settings show up to 2x gains vs long-context scaffolds and up to 3x lower cost vs summarization baselines. Results vary by model and task. (Source: https://arxiv.org/abs/2512.24601)

**Zeno** gives you: every claim traced to `file:lines`, strict budgets preventing runaway costs, and reproducible analysis sessions persisted to disk.

---

## Architecture

### High-Level Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ZENO WORKFLOW                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────┐         ┌──────────────────┐         ┌───────────────┐   │
│   │             │         │                  │         │               │   │
│   │   USER      │────────▶│   LLM (Claude/   │────────▶│   JSONL REPL  │   │
│   │   QUERY     │         │   Codex)         │◀────────│   SERVER      │   │
│   │             │         │                  │         │               │   │
│   └─────────────┘         └────────┬─────────┘         └───────┬───────┘   │
│                                    │                           │           │
│                                    │ Zeno Blocks               │ Corpus    │
│                                    ▼                           ▼           │
│                           ┌──────────────────┐         ┌───────────────┐   │
│                           │                  │         │               │   │
│                           │   PERSISTENCE    │         │   YOUR        │   │
│                           │   LAYER          │         │   CODEBASE    │   │
│                           │                  │         │               │   │
│                           └──────────────────┘         └───────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### REPL Server Operations

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         JSONL REPL PROTOCOL                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────┐                                                           │
│   │ list_files  │───▶ Discover files matching patterns                      │
│   └─────────────┘                                                           │
│                                                                             │
│   ┌─────────────┐                                                           │
│   │    peek     │───▶ Tiny previews (first N lines)                         │
│   └─────────────┘                                                           │
│                                                                             │
│   ┌─────────────┐                                                           │
│   │  read_file  │───▶ Specific line ranges only                             │
│   └─────────────┘                                                           │
│                                                                             │
│   ┌─────────────┐                                                           │
│   │    grep     │───▶ Pattern-based narrowing                               │
│   └─────────────┘                                                           │
│                                                                             │
│   ┌─────────────┐                                                           │
│   │extract_sym  │───▶ Heuristic symbol extraction                           │
│   └─────────────┘                                                           │
│                                                                             │
│   ┌─────────────┐                                                           │
│   │    stat     │───▶ File size/timestamp checks                            │
│   └─────────────┘                                                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Evidence Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          EVIDENCE DISCIPLINE                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│                    ┌──────────────────────────────┐                         │
│                    │        ZENO RESPONSE         │                         │
│                    └──────────────┬───────────────┘                         │
│                                   │                                         │
│                    ┌──────────────┴───────────────┐                         │
│                    ▼              ▼               ▼                         │
│           ┌──────────────┐ ┌────────────┐ ┌─────────────┐                   │
│           │ STATE_UPDATE │ │  EVIDENCE  │ │   CLAIMS    │                   │
│           │    JSON      │ │   LEDGER   │ │   LEDGER    │                   │
│           └──────┬───────┘ └─────┬──────┘ └──────┬──────┘                   │
│                  │               │               │                          │
│                  ▼               ▼               ▼                          │
│           ┌──────────────────────────────────────────────┐                  │
│           │              PERSISTENCE LAYER               │                  │
│           │  .codex/zeno/  or  .claude/zeno/             │                  │
│           │                                              │                  │
│           │  ├── state/<thread-id>.json                  │                  │
│           │  ├── evidence/<thread-id>.jsonl              │                  │
│           │  ├── claims/<thread-id>.jsonl                │                  │
│           │  └── snapshots/<thread-id>/<turn-id>.json    │                  │
│           └──────────────────────────────────────────────┘                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Recursive Inspection Pattern

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      RECURSIVE DECOMPOSITION                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Complex Query: "How does auth flow from login to API call?"               │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  DEPTH 0: Root query                                                │   │
│   │  └─▶ grep "login" → identify entrypoints                            │   │
│   │      └─▶ peek auth/login.ts → confirm handler                       │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                              │                                              │
│                              ▼                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  DEPTH 1: Sub-query "trace session creation"                        │   │
│   │  └─▶ read_file auth/session.ts:40-80                                │   │
│   │      └─▶ grep "SessionStore" → find implementation                  │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                              │                                              │
│                              ▼                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  DEPTH 2: Sub-query "how does middleware validate?"                 │   │
│   │  └─▶ read_file middleware/auth.ts:10-45                             │   │
│   │      └─▶ capsule: "JWT validation using shared secret"              │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                              │                                              │
│                              ▼                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  CONSOLIDATE: Assemble cited report from capsules                   │   │
│   │  └─▶ Claim C1: "Login creates JWT" [E1: auth/login.ts:52-58]        │   │
│   │  └─▶ Claim C2: "Middleware validates" [E2: middleware/auth.ts:20-35]│   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Core Ideas

- **Externalize context**: Keep the corpus in a REPL server, not in the prompt.
- **Minimize retrieval**: Prefer `peek` and narrow `read_file` over whole-file loads.
- **Evidence discipline**: No evidence, no claim.
- **Recursive inspection**: Summarize slices, then consolidate into a report.

## The Name

Zeno of Elea is the philosopher who turned motion into a puzzle about cutting things in half forever. That's essentially what we do with giant prompts: split, split, split, then stitch the answer back together.

- Zeno's Dichotomy paradox divides a journey in half, then half again, forever
- The name signals infinite splitting + recursion, matching "unbounded context via recursive inspection"
- RLMs treat a too-long prompt as an external environment and repeatedly decompose it into smaller subproblems

---

## When to Use Zeno

- **Large repos** (hundreds or thousands of files)
- **Long logs or traces** where only a few lines matter
- **Audits** (security, concurrency, dependency wiring) that require citations
- **Any analysis** where you want reproducible, evidence-backed answers

---

## Modes

Zeno ships with six explicit operating modes. Each mode has a detailed playbook and output add-ons in `codex/zeno/references/modes.md` and `claude-code/claude/skills/zeno/references/modes.md`.

- **codebase-archaeology**: Trace where a function or symbol is defined and used across a monorepo with file:line citations.
- **security-audit**: Systematically scan for vulnerability patterns and build evidence chains.
- **architecture-mapping**: Recursively map entrypoints, lifecycle, and boundaries without forgetting context.
- **pr-review**: Review changed files and trace downstream impact in large repos.
- **skill-generation**: Analyze a tool repo and draft SKILL.md with accurate, cited docs.
- **deep-research**: Evidence-first research mode for large projects and specs.

Mode helper CLI (optional):
```bash
python3 codex/zeno/scripts/zeno_modes.py list
python3 codex/zeno/scripts/zeno_modes.py plan --mode codebase-archaeology --symbol MyFunc --format jsonl
```

---

## Triggering Zeno (Natural Language Examples)

Zeno activates when you explicitly ask for it or name a mode. These prompts work in Codex and Claude Code.

- codebase-archaeology: "Use Zeno codebase-archaeology to trace MyFunc across the repo with file:line citations."
- security-audit: "Run Zeno security-audit on src/ and build evidence chains for any risky patterns."
- architecture-mapping: "Use Zeno architecture-mapping to document entrypoints, routing, and lifecycle for the API service."
- pr-review: "Zeno pr-review these changed files: src/api.py, src/routes.py. Show downstream impact."
- skill-generation: "Use Zeno skill-generation on this repo and draft a SKILL.md with citations."
- deep-research: "Zeno deep-research this project and answer: how does auth flow through the system?"

If a mode needs inputs, include them in the request (symbol name, changed files, or research question).

---

## Indexing (Symbol + Dependency Map)

Optional: build a lightweight index to speed up archaeology, architecture mapping, and PR review impact analysis.

```bash
python3 codex/zeno/scripts/zeno_index.py --root /path/to/repo --out /tmp/zeno_index.json
```

See `codex/zeno/references/indexing.md` for details.

---

## Budgets and Guardrails (Default Behavior)

Default caps (unless you explicitly ask for deeper coverage):

| Resource | Per Section | Per Answer |
|:---------|:-----------:|:----------:|
| Retrieval ops | ≤12 | ≤30 |
| `read_file` lines | - | ≤2,000 total |
| `read_file` per call | - | ≤400 lines |
| `grep` hits | - | ≤200 per call |
| File capsules | - | ≤12 |
| Recursion depth | - | ≤2 |

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

Requests and responses are one JSON object per line (JSONL). See the protocol docs in `codex/zeno/references/protocol.md` or `claude-code/claude/skills/zeno/references/protocol.md`.

---

## Output Blocks (Required for Persistence)

Each Zeno response ends with three machine-parseable blocks:

```
===ZENO_STATE_UPDATE_JSON===
{ "thread_id":"...", "turn_id":"...", "mode":"read-only", "budgets":{...}, "high_level_summary":"..." }
===/ZENO_STATE_UPDATE_JSON===

===ZENO_EVIDENCE_LEDGER_JSONL===
{"evidence_id":"E1","kind":"read","path":"...","lines":[10,44],"why":"...","hash":"..."}
===/ZENO_EVIDENCE_LEDGER_JSONL===

===ZENO_CLAIM_LEDGER_JSONL===
{"claim_id":"C1","claim":"...","evidence":["E1"],"confidence":"high"}
===/ZENO_CLAIM_LEDGER_JSONL===
```

These blocks are how Pattern A persists evidence and claims reliably.

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

- Zeno is **read-only by design**; the server does not execute arbitrary code
- Default OTEL prompt logging is **off**; enable only if required
- Avoid logging secrets in evidence or claims; redact as needed

---

## Performance Notes

- Prefer narrow `grep` patterns and short `read_file` slices
- Use `stat` to skip huge or generated files
- Expect slower runs on very large repos; Zeno favors reliability over speed

---

## Repo Layout

```
$REPO_ROOT/
  README.md              # This master overview
  codex/                 # Codex-specific package and docs
    README.md
    zeno/                # Codex skill package
  claude-code/           # Claude Code-specific package and docs
    README.md
    claude/              # Visible Claude layout (copy to .claude for runtime)
```

---

## Choose Your Runtime

### Codex

Zeno is a Codex skill with an optional notify persistence helper and OTEL telemetry guidance.
- **Package:** `codex/zeno/`
- **Docs:** `codex/README.md`

**Quick Start (Codex):**

1. Install the skill:
   - Repo scope: copy `codex/zeno/` to `$REPO_ROOT/.codex/skills/zeno/`
   - User scope: copy `codex/zeno/` to `$CODEX_HOME/skills/zeno/`

2. Start the JSONL REPL server:
   ```bash
   python3 /ABS/PATH/zeno/scripts/zeno_server.py --root /path/to/repo --log /tmp/zeno_trace.jsonl
   ```

3. (Optional) Enable Pattern A and B in `~/.codex/config.toml`:
   ```toml
   notify = ["python3", "/ABS/PATH/zeno/scripts/notify_persist.py"]

   [history]
   max_bytes = 104857600

   [otel]
   environment = "prod"
   exporter = "otlp-http"
   log_user_prompt = false
   ```

### Claude Code

Zeno is a Claude Code skill paired with hooks for always-on persistence.
- **Package:** `claude-code/claude/skills/zeno/`
- **Docs:** `claude-code/README.md`

**Quick Start (Claude Code):**

1. Copy the visible layout into the runtime location:
   ```bash
   rsync -a claude-code/claude/ .claude/
   ```
   Or use the helper script:
   ```bash
   ./scripts/sync_claude.sh
   ```

2. Use the preconfigured settings (fast path) and refresh:
   - `.claude/settings.json` is already included when you copy `claude-code/claude/` to `.claude/`
   - Run `/hooks` to reload

   Manual merge option:
   - Merge `.claude/hooks/zeno.hooks.json` into `.claude/settings.json`
   - Optionally merge `.claude/settings.example.json` for OTEL env settings

3. (Optional) Start the JSONL REPL server (same as Codex)

---

## How the Zeno Loop Works

1. **Plan**: Identify entrypoints, configs, routing, and DI boundaries
2. **Retrieve**: `list`, `peek`, and `grep` to locate minimal evidence
3. **Read**: Pull small line ranges with `read_file`
4. **Recurse**: Summarize complex slices in capsules
5. **Consolidate**: Assemble a cited report and a wiring map

---

## Evidence and Claims

Zeno requires three machine-parseable blocks at the end of each response:
- `ZENO_STATE_UPDATE_JSON`
- `ZENO_EVIDENCE_LEDGER_JSONL`
- `ZENO_CLAIM_LEDGER_JSONL`

These are persisted as state and ledgers so that every claim can be traced to evidence.

---

## Pattern A (Persistence)

- **Codex**: `notify_persist.py` extracts Zeno blocks and writes `.codex/zeno/` artifacts
- **Claude Code**: hooks write `.claude/zeno/` artifacts on every turn

---

## Pattern B (Telemetry)

- Optional OTEL exporter captures tool-level events for replay and audit
- Default is privacy-first; prompt logging is opt-in

---

## Testing

- **Codex tests**: `codex/zeno/tests/`
- **Claude Code tests**: `claude-code/claude/skills/zeno/tests/`

Example:
```bash
cd /ABS/PATH/claude-code/claude/skills/zeno
python3 -m pytest -q
```

---

## Troubleshooting

- If ledgers are missing, confirm the Zeno blocks are emitted in the response
- **Codex**: check `.codex/zeno/notify.log`
- **Claude Code**: check `.claude/zeno/notify.log` and `/hooks` registration

---

## Next Steps

- See `codex/README.md` for Codex details
- See `claude-code/README.md` for Claude Code details

---

## Acknowledgments

This project is inspired by and references:

- Zhang et al., "Recursive Language Models" (arXiv:2512.24601v1): https://arxiv.org/abs/2512.24601v1
- Alex Zhang's reference implementation: https://github.com/alexzhang13/rlm
- Original announcement thread: https://x.com/a1zhang/status/2007566581409144852?s=46
- Prime Intellect's RLM research: https://www.primeintellect.ai/blog/rlm

Thank you to Alex Zhang and collaborators for the Zeno concept and open resources that informed this work.
