[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Claude Code Compatible](https://img.shields.io/badge/Claude%20Code-Compatible-blue)](https://claude.ai/code)
[![Built with AI](https://img.shields.io/badge/Built%20with-AI%20%F0%9F%A4%96-blueviolet)](https://claude.ai/)  [![Built with AI](https://img.shields.io/badge/Built%20with-AI%20%F0%9F%A4%96-blueviolet)](https://claude.ai/)
[![Docs](https://img.shields.io/badge/Docs-Read%20the%20manual-brightgreen)](../../../../README.md)
[![JSONL](https://img.shields.io/badge/Protocol-JSONL-1f6feb)](#jsonl-repl-protocol-summary)
[![OpenTelemetry](https://img.shields.io/badge/Telemetry-OpenTelemetry-8A2BE2)](../../../../codex/zeno/references/otel.md)
[![Codex Compatible](https://img.shields.io/badge/Codex-Compatible-blue)](https://platform.openai.com/)
[![Read-Only](https://img.shields.io/badge/Mode-Read--Only-ff69b4)](#budgets-and-guardrails-default-behavior)
[![Evidence-First](https://img.shields.io/badge/Policy-Evidence--First-2ea44f)](#output-blocks-required-for-persistence)

# Zeno Skill for Claude Code

<p align="center"><img src="../../../../assets/zeno.png" width="50%" alt="Zeno"></p>

## Table of Contents
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
- [JSONL REPL protocol (summary)](#jsonl-repl-protocol-summary)
- [Budgets and guardrails (default behavior)](#budgets-and-guardrails-default-behavior)
- [Output blocks (required for persistence)](#output-blocks-required-for-persistence)

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
2) Copy hooks config into your settings:
   - See `.claude/hooks/zeno.hooks.json` for the exact hook commands.
   - Merge the contents into `.claude/settings.json` or `~/.claude/settings.json`.
3) Refresh hooks in Claude Code: run `/hooks` and confirm Zeno hooks are listed.
4) (Optional) Start the JSONL REPL server for retrieval:
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

Thank you to Alex Zhang and collaborators for the Zeno concept and open resources that informed this work.
