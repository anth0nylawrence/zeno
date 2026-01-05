<p align="center"><img src="../../assets/zeno.png" width="50%" alt="Zeno"></p>

# Zeno Skill

## Plain-English context
ELI5: This skill lets a coding agent read a huge codebase without stuffing the whole thing into its memory. It keeps the big files in a separate "library" and only checks out the exact pages it needs, then writes down receipts for every claim.
Technical: This is a production-grade Codex skill for evidence-first, read-only analysis over large corpora using a JSONL REPL server, per-turn persistence (Pattern A), and OpenTelemetry telemetry (Pattern B).

## What you are installing
ELI5: You are installing a "rulebook" and a set of helper scripts that make sure the agent stays honest and leaves an audit trail.
Technical: The skill package includes SKILL.md, a JSONL REPL server, notify persistence, OTEL config, log linting, evidence verification, example fixtures, and tests.

## Install locations (Codex discovery)
ELI5: Codex looks in a few specific places for skills, so put the folder there.
Technical:
- Repo scope: `$REPO_ROOT/.codex/skills/zeno/`
- User scope: `$CODEX_HOME/skills/zeno/` (default `~/.codex/skills/zeno/`)
- Admin scope (optional): `/etc/codex/skills/zeno/`

## Quick start
ELI5: Start the librarian, then ask tiny questions instead of big ones.
Technical:
1) Start the REPL server:
```bash
python3 /ABS/PATH/zeno/scripts/zeno_server.py --root /path/to/repo --log /tmp/zeno_trace.jsonl
```
2) Send a request (one JSON per line):
```json
{"id":"req-1","op":"list_files","args":{"glob":"**/*.swift","max":200}}
```
3) Use the results to produce a cited report and end with the mandatory Zeno blocks.

## Pattern A: per-turn persistence (notify)
ELI5: After every agent turn, a helper saves the current state and receipts so nothing is lost.
Technical:
- Configure `notify` to call `scripts/notify_persist.py`.
- The script extracts the three Zeno blocks from the last assistant message and stores them in `.codex/zeno/`.
- It also saves a per-turn snapshot for replay.
- Codex history (`~/.codex/history.jsonl`) is treated as the ground-truth fallback if blocks are missing.
- A checkpoint line is appended to `.codex/zeno/notify.log` on each turn.

## Notify payload (what the hook receives)
ELI5: Codex sends a tiny summary note after each turn so the helper knows what just happened.
Technical: The notify hook receives a single JSON argument with fields like:
- `type` (event name, currently `agent-turn-complete`)
- `thread-id` / `turn-id`
- `cwd`
- `input-messages`
- `last-assistant-message`
`notify_persist.py` reads the last assistant message (and history tail if needed) to extract the three Zeno blocks.

### Expected artifacts
```
.codex/zeno/
  state/<thread-id>.json
  evidence/<thread-id>.jsonl
  claims/<thread-id>.jsonl
  snapshots/<thread-id>/<turn-id>.json
  notify.log
```

## CLI checkpoint signal
ELI5: You can watch a live “checkpoint saved” stream in another terminal.
Technical:
```bash
tail -f /path/to/repo/.codex/zeno/notify.log
```
Each line looks like:
```
2026-01-04T18:11:30Z zeno_checkpoint thread_id=T1 turn_id=U4 evidence=2 claims=2 state_block=True
```

## Pattern B: high-fidelity telemetry (OTEL)
ELI5: This is a live event stream of tool usage so you can replay what happened later.
Technical:
- Enable OTEL in `~/.codex/config.toml`.
- Run the collector from `configs/otel-collector.yaml`.
- The collector writes JSONL for replay and audit.
- Pattern A is the authoritative checkpoint even if OTEL is down.
- Pattern B adds high-resolution tool-level detail for audits and analytics.

## Context bridge (carry forward Zeno state)
ELI5: This prints a small “memory card” you can paste into the next prompt.
Technical:
```bash
python3 scripts/zeno_context_bridge.py --zeno-root /path/to/repo/.codex/zeno
```
Optional flags:
- `--thread-id T1` to select a specific thread
- `--max-evidence 5` / `--max-claims 5` to control size
- `--json` for machine-readable output

## Flags and help
ELI5: The helper scripts accept flags; `--help` shows them.
Technical:
```bash
python3 scripts/zeno_context_bridge.py --help
python3 scripts/zeno_client.py --help
```
Common flags:
- `zeno_context_bridge.py`: `--zeno-root`, `--thread-id`, `--max-evidence`, `--max-claims`, `--json`
- `zeno_client.py`: `send|tail`, `--op`, `--args`, `--request`, `--pretty`, `--log`, `--lines`, `--follow`

## Non-interactive mode (automation)
ELI5: This still works even if Codex runs in the background.
Technical: The notify hook and OTEL export work in interactive TUI sessions and `codex exec` automation runs, as long as the config keys are set.

## Config: minimal example (verbatim)
ELI5: This tells Codex to save a checkpoint after every turn and to keep a history buffer.
Technical:
```toml
# ~/.codex/config.toml

notify = ["python3", "/ABS/PATH/zeno/scripts/notify_persist.py"]

[history]
max_bytes = 104857600 # 100 MiB (drops oldest entries when compacting)

[otel]
environment = "prod"
exporter = "otlp-http"
log_user_prompt = false  # privacy default
```

## What the skill enforces
ELI5: It forces the agent to show its work and stop if it is guessing.
Technical:
- Read-only behavior
- Budgets for retrieval and line counts
- Evidence Ledger and Claim Ledger
- Strict output schema
- Mandatory end-of-turn JSON/JSONL blocks

## Scripts included
ELI5: These scripts are the "tools" that make the system reliable.
Technical:
- `scripts/zeno_server.py`: JSONL REPL server
- `scripts/notify_persist.py`: persistence on `agent-turn-complete`
- `scripts/zeno_client.py`: tiny CLI for requests and log tailing
- `scripts/zeno_context_bridge.py`: emit a summary block for the next prompt
- `scripts/log_lint.py`: validate ledgers and budgets
- `scripts/rotate_history.py`: rotate JSONL files by size
- `scripts/verify_evidence.py`: validate evidence references against disk

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
ELI5: Tests make sure the "receipt" system works.
Technical:
```bash
cd /ABS/PATH/zeno
python3 -m pytest -q
```

## Security and privacy
ELI5: Do not leak secrets into logs.
Technical:
- Default `otel.log_user_prompt = false`.
- Avoid logging secrets in evidence/claims.
- Use redaction if paths include sensitive identifiers.

## Troubleshooting
ELI5: If something fails, check the log and the block format.
Technical:
- Ensure the assistant emitted all three Zeno blocks in the right order.
- Check `~/.codex/history.jsonl` and `.codex/zeno/` outputs.
- Run `scripts/log_lint.py` to catch structural errors.

## Acknowledgments
This skill is inspired by and references:
- Zhang et al., "Recursive Language Models" (arXiv:2512.24601v1): https://arxiv.org/abs/2512.24601v1
- Alex Zhang's reference implementation: https://github.com/alexzhang13/rlm
- Original announcement thread: https://x.com/a1zhang/status/2007566581409144852?s=46

Thank you to Alex Zhang and collaborators for the Zeno concept and open resources that informed this work.
