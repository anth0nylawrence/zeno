[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Claude Code Compatible](https://img.shields.io/badge/Claude%20Code-Compatible-blue)](https://claude.ai/code)
[![Docs](https://img.shields.io/badge/Docs-Read%20the%20manual-brightgreen)](../../../../README.md)
[![JSONL](https://img.shields.io/badge/Protocol-JSONL-1f6feb)](#jsonl-repl-protocol-summary)
[![OpenTelemetry](https://img.shields.io/badge/Telemetry-OpenTelemetry-8A2BE2)](../../../../codex/zeno/references/otel.md)
[![Codex Compatible](https://img.shields.io/badge/Codex-Compatible-blue)](https://platform.openai.com/)
[![Read-Only](https://img.shields.io/badge/Mode-Read--Only-ff69b4)](#budgets-and-guardrails-default-behavior)
[![Evidence-First](https://img.shields.io/badge/Policy-Evidence--First-2ea44f)](#output-blocks-required-for-persistence)

# Zeno Skill for Claude Code

<p align="center"><img src="../../../../assets/zeno.png" width="50%" alt="Zeno"></p>

> **Recursive decomposition for unbounded codebase analysis.** Zeno is an evidence-first, read-only workflow that lets AI models analyze massive codebases without context rot -- by keeping the corpus external and pulling only what is needed.

## Table of Contents
- [Why Zeno? The Problem It Solves](#why-zeno-the-problem-it-solves)
- [What Makes Zeno Different](#what-makes-zeno-different)
- [Architecture](#architecture)
- [Core Ideas](#core-ideas)
- [The Name](#the-name)
- [When to Use Zeno](#when-to-use-zeno)
- [Modes](#modes)
- [Triggering Zeno (Natural Language Examples)](#triggering-zeno-natural-language-examples)
- [Budgets and Guardrails (Default Behavior)](#budgets-and-guardrails-default-behavior)
- [JSONL REPL Protocol (Summary)](#jsonl-repl-protocol-summary)
- [Output Blocks (Required for Persistence)](#output-blocks-required-for-persistence)
- [Persistence Artifacts (Where the Receipts Live)](#persistence-artifacts-where-the-receipts-live)
- [Security and Privacy Notes](#security-and-privacy-notes)
- [Performance Notes](#performance-notes)
- [Introduction](#introduction)
- [What you are installing](#what-you-are-installing)
- [Install locations (Claude Code discovery)](#install-locations-claude-code-discovery)
- [Quick start](#quick-start)
- [Pattern A: hook-based persistence (always-on)](#pattern-a-hook-based-persistence-always-on)
- [Hook payload (stdin JSON + transcript_path)](#hook-payload-stdin-json-transcriptpath)
- [CLI checkpoint signal](#cli-checkpoint-signal)
- [Context bridge (carry forward Zeno state)](#context-bridge-carry-forward-zeno-state)
- [Flags and help](#flags-and-help)
- [Pattern B: Claude Code telemetry (OTEL)](#pattern-b-claude-code-telemetry-otel)
- [Settings example (hooks + env)](#settings-example-hooks-env)
- [Verification playbook](#verification-playbook)
- [Non-interactive mode](#non-interactive-mode)
- [What the skill enforces](#what-the-skill-enforces)
- [Scripts included](#scripts-included)
- [References](#references)
- [Tests](#tests)
- [Security and privacy](#security-and-privacy)
- [Troubleshooting](#troubleshooting)
- [Acknowledgments](#acknowledgments)

---

## Why Zeno? The Problem It Solves

Zeno targets long-context analysis where a model must understand a large codebase without loading it all at once. It keeps the corpus external and pulls only the small slices needed to answer each question.
For the full narrative and diagrams, see ../../../../README.md.

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

## Modes

Zeno ships with six explicit operating modes. Each mode has a detailed playbook and output add-ons in `claude-code/claude/skills/zeno/references/modes.md`.

- codebase-archaeology: Trace where a function or symbol is defined and used across a monorepo with file:line citations.
- security-audit: Systematically scan for vulnerability patterns and build evidence chains.
- architecture-mapping: Recursively map entrypoints, lifecycle, and boundaries without forgetting context.
- pr-review: Review changed files and trace downstream impact in large repos.
- skill-generation: Analyze a tool repo and draft SKILL.md with accurate, cited docs.
- deep-research: Evidence-first research mode for large projects and specs.

Mode helper CLI (optional):
```bash
python3 claude-code/claude/skills/zeno/scripts/zeno_modes.py list
python3 claude-code/claude/skills/zeno/scripts/zeno_modes.py plan --mode codebase-archaeology --symbol MyFunc --format jsonl
```

---

## Triggering Zeno (Natural Language Examples)

Zeno activates when you explicitly ask for it or name a mode.

- codebase-archaeology: `Use Zeno codebase-archaeology to trace MyFunc across the repo with file:line citations.`
- security-audit: `Run Zeno security-audit on src/ and build evidence chains for any risky patterns.`
- architecture-mapping: `Use Zeno architecture-mapping to document entrypoints, routing, and lifecycle for the API service.`
- pr-review: `Zeno pr-review these changed files: src/api.py, src/routes.py. Show downstream impact.`
- skill-generation: `Use Zeno skill-generation on this repo and draft a SKILL.md with citations.`
- deep-research: `Zeno deep-research this project and answer: how does auth flow through the system?`

If a mode needs inputs, include them in the request (symbol name, changed files, or research question).

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
Technical: This repo stores the Claude Code package under `claude/` for visibility on GitHub. Claude Code itself expects `.claude/`, so copy `claude/` to `.claude/` before you run the hooks.

## What you are installing
ELI5: You are installing a rulebook plus a set of always-on helpers.
Technical: The package includes SKILL.md, hook scripts for SessionStart/UserPromptSubmit/Stop/PreCompact/PostToolUse, a JSONL REPL server, OTEL guidance, log linting, evidence verification, and example fixtures.

## Install locations (Claude Code discovery)
ELI5: Claude Code reads skills from a specific folder inside your project.
Technical:
- Repo-visible (this package): `$REPO_ROOT/claude/skills/zeno/`
- Runtime (required by Claude Code): `$REPO_ROOT/.claude/skills/zeno/`
- User scope: `~/.claude/skills/zeno/SKILL.md`

## Quick start
ELI5: Turn on the hooks, then start using the skill.
Technical:
1) Copy the visible folder into the runtime location:
   - `rsync -a claude/ .claude/`
2) Use the preconfigured settings file (fast path):
   - `.claude/settings.json` is already included when you copy `claude/` to `.claude/`.
3) If you want to merge manually:
   - See `.claude/hooks/zeno.hooks.json` for the exact hook commands.
   - Merge the contents into `.claude/settings.json` or `~/.claude/settings.json`.
4) Refresh hooks in Claude Code: run `/hooks` and confirm Zeno hooks are listed.
5) (Optional) Start the JSONL REPL server for retrieval:
```bash
python3 .claude/skills/zeno/scripts/zeno_server.py --root /path/to/repo --log /tmp/zeno_trace.jsonl
```
If you have not copied yet, run the same command from `claude/skills/zeno/` instead.

## Pattern A: hook-based persistence (always-on)
ELI5: A helper saves the receipts every turn, automatically.
Technical:
- `Stop` hook parses the transcript and writes state/evidence/claims to `.claude/zeno/`.
- `UserPromptSubmit` injects the memory bridge into the next prompt.
- `PreCompact` snapshots state before compaction.
- `PostToolUse` optionally captures tool outputs/diffs.
- `SessionStart` emits a small header once per session.

### Expected artifacts
```
.claude/zeno/
  state/<thread-id>.json
  evidence/<thread-id>.jsonl
  claims/<thread-id>.jsonl
  snapshots/<thread-id>/<turn-id>.json
  snapshots/<thread-id>/precompact/<timestamp>.json
  cursors/<thread-id>.json
  tool_events/<thread-id>.jsonl
  notify.log
  status.json
```

## Hook payload (stdin JSON + transcript_path)
ELI5: Claude Code sends a small note to each hook so it knows what just happened.
Technical: Hooks receive a JSON payload on stdin. When available, it includes `transcript_path`. Scripts must parse it incrementally and maintain cursor offsets.

## CLI checkpoint signal
ELI5: You can watch “checkpoint saved” messages live in another terminal.
Technical:
```bash
tail -f /path/to/repo/.claude/zeno/notify.log
```
Each line looks like:
```
2026-01-04T18:11:30Z zeno_checkpoint thread_id=T1 turn_id=U4 evidence=2 claims=2 state_block=True
```

## Context bridge (carry forward Zeno state)
ELI5: This prints a small memory card you can paste into the next prompt.
Technical:
```bash
python3 .claude/skills/zeno/scripts/zeno_context_bridge.py --zeno-root /path/to/repo/.claude/zeno
```
If you have not copied yet, adjust the script path to `claude/skills/zeno/`.
Optional flags:
- `--thread-id T1` to select a specific thread
- `--max-evidence 5` / `--max-claims 5` to control size
- `--json` for machine-readable output

## Flags and help
ELI5: The helper scripts accept flags; `--help` shows them.
Technical:
```bash
python3 .claude/skills/zeno/scripts/zeno_context_bridge.py --help
python3 .claude/skills/zeno/scripts/zeno_client.py --help
```
If you have not copied yet, adjust the script path to `claude/skills/zeno/`.
Common flags:
- `zeno_context_bridge.py`: `--zeno-root`, `--thread-id`, `--max-evidence`, `--max-claims`, `--json`
- `zeno_client.py`: `send|tail`, `--op`, `--args`, `--request`, `--pretty`, `--log`, `--lines`, `--follow`

## Pattern B: Claude Code telemetry (OTEL)
ELI5: This is a live event stream of tool usage for replay and audit.
Technical:
- Enable telemetry via environment variables or `.claude/settings.json` `env`.
- Use the provided collector config at `configs/otel-collector.yaml`.
- Prompt logging is opt-in only.

Environment example:
```bash
export CLAUDE_CODE_ENABLE_TELEMETRY=1
export OTEL_METRICS_EXPORTER=otlp
export OTEL_LOGS_EXPORTER=otlp
export OTEL_EXPORTER_OTLP_PROTOCOL=grpc
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
# Optional: export OTEL_LOG_USER_PROMPTS=1
```

## Settings example (hooks + env)
ELI5: This is a ready-to-copy settings file.
Technical: See `.claude/settings.example.json` (after copying) and merge into your actual settings file.

## Verification playbook
ELI5: Check that the helpers are really running.
Technical:
1) Run `/hooks` to confirm hooks are registered.
2) Run `claude --debug` and confirm each hook executes.
3) Confirm `.claude/zeno/state/` and `.claude/zeno/notify.log` update after a turn.
4) Ensure `UserPromptSubmit` output appears in the prompt context.

## Non-interactive mode
ELI5: This still works if Claude runs in automation.
Technical: Hooks run in interactive sessions and automation runs as long as settings and env are configured.

## What the skill enforces
ELI5: It forces Claude to show its work and stop if it is guessing.
Technical:
- Read-only behavior
- Budgets for retrieval and line counts
- Evidence Ledger and Claim Ledger
- Strict output schema
- Mandatory end-of-turn JSON/JSONL blocks

## Scripts included
ELI5: These scripts are the tools that make the system reliable.
Technical:
- `scripts/session_start.py`: SessionStart hook
- `scripts/user_prompt_submit.py`: UserPromptSubmit hook
- `scripts/stop.py`: Stop hook persistence
- `scripts/precompact.py`: PreCompact snapshot
- `scripts/post_tool_use.py`: PostToolUse audit
- `scripts/zeno_server.py`: JSONL REPL server
- `scripts/zeno_client.py`: JSONL client
- `scripts/zeno_context_bridge.py`: emit a summary block for the next prompt
- `scripts/log_lint.py`: validate ledgers and budgets
- `scripts/rotate_history.py`: rotate JSONL files by size
- `scripts/verify_evidence.py`: validate evidence references against disk
- `scripts/notify_persist.py`: legacy Codex notify helper (not used in Claude Code)

## References
ELI5: These docs explain the data formats, security, and operations.
Technical:
- `references/protocol.md`: JSONL protocol and op schemas
- `references/data_model.md`: canonical evidence/claim/state schemas
- `references/security.md`: threat model and privacy defaults
- `references/otel.md`: OTEL setup and collector guidance
- `references/troubleshooting.md`: common issues and fixes
- `references/recipes.md`: copy/paste retrieval recipes

## Tests
ELI5: Tests make sure the receipt system works.
Technical:
```bash
cd .claude/skills/zeno
python3 -m pytest -q
```
If you have not copied yet, run tests from `claude/skills/zeno` instead.

## Security and privacy
ELI5: Do not leak secrets into logs.
Technical:
- Default OTEL prompt logging is off.
- Avoid logging secrets in evidence/claims.
- Use redaction if paths include sensitive identifiers.

## Troubleshooting
ELI5: If something fails, check the log and the block format.
Technical:
- Ensure the assistant emitted all three Zeno blocks in the right order.
- Check `.claude/zeno/` outputs and `notify.log`.
- Run `scripts/log_lint.py` to catch structural errors.

## Acknowledgments
This skill is inspired by and references:
- Zhang et al., "Recursive Language Models" (arXiv:2512.24601v1): https://arxiv.org/abs/2512.24601v1
- Alex Zhang's reference implementation: https://github.com/alexzhang13/rlm
- Original announcement thread: https://x.com/a1zhang/status/2007566581409144852?s=46
- Prime Intellect's RLM research: https://www.primeintellect.ai/blog/rlm

Thank you to Alex Zhang and collaborators for the Zeno concept and open resources that informed this work.
