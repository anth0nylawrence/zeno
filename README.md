<img src="assets/zeno.png" width="50%" alt="Zeno">

# Zeno

## Plain-English context (start here)
ELI5: Zeno is a way to read huge codebases without stuffing them into the model's memory. It keeps the big files outside the model, pulls only the few lines needed, and keeps receipts so every claim can be traced back to evidence.
Technical: Zeno is an evidence-first, read-only workflow for large corpora. It pairs a JSONL REPL server (list_files/read_file/peek/grep/extract_symbols) with strict budgets and a claim-evidence ledger. It supports both Codex and Claude Code with persistence (Pattern A) and optional telemetry (Pattern B).

## What Zeno is (and is not)
- Zeno is a disciplined analysis workflow for large corpora; it is not a code editor.
- Zeno is read-only by default; it does not modify files unless you explicitly request edits later.
- Zeno values auditability over speed: every claim must cite evidence.

## Core ideas
- Externalize context: keep the corpus in a REPL server, not in the prompt.
- Minimize retrieval: prefer peek and narrow reads over whole-file loads.
- Evidence discipline: no evidence, no claim.
- Recursive inspection: summarize slices, then consolidate into a report.

## Why Zeno?
ELI5: Zeno is the philosopher who turned motion into a puzzle about cutting things in half forever. That is basically what we do with giant prompts: split, split, split, then stitch the answer back together.
Technical:
- Zeno of Elea is a philosophical patron for recursive decomposition: https://en.wikipedia.org/wiki/Zeno_of_Elea
- Zeno’s Dichotomy paradox divides a journey in half, then half again, and again, forever.
- Zeno’s name signals infinite splitting + recursion, which matches “unbounded context via recursive inspection.”
- RLMs treat a too-long prompt as an external environment and repeatedly decompose it into smaller subproblems until the final answer is assembled.

## When to use Zeno
- Large repos (hundreds or thousands of files).
- Long logs or traces where only a few lines matter.
- Audits (security, concurrency, dependency wiring) that require citations.
- Any analysis where you want reproducible, evidence-backed answers.

## Budgets and guardrails (default behavior)
Default caps (unless the user explicitly asks for deeper coverage):
- Retrieval ops: <= 30 per answer, <= 12 per section.
- `read_file`: <= 400 lines per call, <= 2,000 lines total per answer.
- `grep`: <= 200 hits per call; narrow patterns if truncated.
- Recursion: <= 12 file capsules, depth <= 2.
- If budgets are hit: stop, summarize, and provide a next retrieval plan.

## JSONL REPL protocol (summary)
Core operations exposed by the server:
- `list_files` for discovery.
- `peek` for tiny previews.
- `read_file` for specific line ranges.
- `grep` for pattern-based narrowing.
- `extract_symbols` for heuristic symbol lists.
- `stat` for file size and timestamp checks.

Requests and responses are one JSON object per line (JSONL). See the protocol docs in `codex/zeno/references/protocol.md` or `claude-code/claude/skills/zeno/references/protocol.md`.

## Output blocks (required for persistence)
Each Zeno response ends with three machine-parseable blocks:
```
===ZENO_STATE_UPDATE_JSON===
{ \"thread_id\":\"...\", \"turn_id\":\"...\", \"mode\":\"read-only\", \"budgets\":{...}, \"high_level_summary\":\"...\" }
===/ZENO_STATE_UPDATE_JSON===

===ZENO_EVIDENCE_LEDGER_JSONL===
{\"evidence_id\":\"E1\",\"kind\":\"read\",\"path\":\"...\",\"lines\":[10,44],\"why\":\"...\",\"hash\":\"...\"}
===/ZENO_EVIDENCE_LEDGER_JSONL===

===ZENO_CLAIM_LEDGER_JSONL===
{\"claim_id\":\"C1\",\"claim\":\"...\",\"evidence\":[\"E1\"],\"confidence\":\"high\"}
===/ZENO_CLAIM_LEDGER_JSONL===
```
These blocks are how Pattern A persists evidence and claims reliably.

## Persistence artifacts (where the receipts live)
Codex (notify-based):
```
.codex/zeno/
  state/<thread-id>.json
  evidence/<thread-id>.jsonl
  claims/<thread-id>.jsonl
  snapshots/<thread-id>/<turn-id>.json
  notify.log
```
Claude Code (hooks-based):
```
.claude/zeno/
  state/<thread-id>.json
  evidence/<thread-id>.jsonl
  claims/<thread-id>.jsonl
  snapshots/<thread-id>/<turn-id>.json
  notify.log
```

## Security and privacy notes
- Zeno is read-only by design; the server does not execute arbitrary code.
- Default OTEL prompt logging is off; enable only if required.
- Avoid logging secrets in evidence or claims; redact as needed.

## Performance notes
- Prefer narrow `grep` patterns and short `read_file` slices.
- Use `stat` to skip huge or generated files.
- Expect slower runs on very large repos; Zeno favors reliability over speed.

## Repo layout
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

## Choose your runtime

### Codex
Zeno is a Codex skill with an optional notify persistence helper and OTEL telemetry guidance.
- Package: `codex/zeno/`
- Docs: `codex/README.md`

Quick start (Codex):
1) Install the skill:
   - Repo scope: copy `codex/zeno/` to `$REPO_ROOT/.codex/skills/zeno/`
   - User scope: copy `codex/zeno/` to `$CODEX_HOME/skills/zeno/`
2) Start the JSONL REPL server:
```
python3 /ABS/PATH/zeno/scripts/zeno_server.py --root /path/to/repo --log /tmp/zeno_trace.jsonl
```
3) (Optional) Enable Pattern A and B in `~/.codex/config.toml`:
```
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
- Package: `claude-code/claude/skills/zeno/`
- Docs: `claude-code/README.md`

Quick start (Claude Code):
1) Copy the visible layout into the runtime location:
```
rsync -a claude-code/claude/ .claude/
```
Or use the helper script:
```
./scripts/sync_claude.sh
```
2) Merge hooks into settings and refresh:
   - Merge `.claude/hooks/zeno.hooks.json` into `.claude/settings.json`.
   - Run `/hooks` to reload.
3) (Optional) Start the JSONL REPL server (same as Codex).

## How the Zeno loop works
1) Plan: identify entrypoints, configs, routing, and DI boundaries.
2) Retrieve: list, peek, and grep to locate the minimal evidence.
3) Read: pull small line ranges with read_file.
4) Recurse: summarize complex slices in capsules.
5) Consolidate: assemble a cited report and a wiring map.

## Evidence and claims
Zeno requires three machine-parseable blocks at the end of each response:
- `ZENO_STATE_UPDATE_JSON`
- `ZENO_EVIDENCE_LEDGER_JSONL`
- `ZENO_CLAIM_LEDGER_JSONL`

These are persisted as state and ledgers so that every claim can be traced to evidence.

## Pattern A (persistence)
- Codex: `notify_persist.py` extracts Zeno blocks and writes `.codex/zeno/` artifacts.
- Claude Code: hooks write `.claude/zeno/` artifacts on every turn.

## Pattern B (telemetry)
- Optional OTEL exporter captures tool-level events for replay and audit.
- Default is privacy-first; prompt logging is opt-in.

## Testing
- Codex tests: `codex/zeno/tests/`
- Claude Code tests: `claude-code/claude/skills/zeno/tests/`

Example:
```
cd /ABS/PATH/claude-code/claude/skills/zeno
python3 -m pytest -q
```

## Troubleshooting
- If ledgers are missing, confirm the Zeno blocks are emitted in the response.
- Codex: check `.codex/zeno/notify.log`.
- Claude Code: check `.claude/zeno/notify.log` and `/hooks` registration.

## Next steps
- See `codex/README.md` for Codex details.
- See `claude-code/README.md` for Claude Code details.

## Acknowledgments
This project is inspired by and references:
- Zhang et al., "Recursive Language Models" (arXiv:2512.24601v1): https://arxiv.org/abs/2512.24601v1
- Alex Zhang's reference implementation: https://github.com/alexzhang13/rlm
- Original announcement thread: https://x.com/a1zhang/status/2007566581409144852?s=46

Thank you to Alex Zhang and collaborators for the Zeno concept and open resources that informed this work.
