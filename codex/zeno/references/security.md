# Security and Privacy Posture

## Plain-English overview
ELI5: This section explains how to keep private information safe while the agent is reading files and writing logs.
Technical: It documents threat models, defaults, and mitigation strategies for the Zeno workflow.

---

## Threat model
ELI5: These are the ways the system could accidentally leak secrets or read the wrong files.
Technical:
- Path traversal: a request tries to read files outside the repo.
- Regex injection: complex regex can hang or spike CPU.
- Log exfiltration: evidence/claims/telemetry may expose sensitive paths or content.
- Over-collection: too much context or logs stored without retention rules.

---

## Defaults and guardrails
ELI5: The system is locked down by default.
Technical:
- `zeno_server.py` refuses paths outside `--root`.
- `grep` defaults to literal match; regex must be explicitly enabled.
- `otel.log_user_prompt = false` by default.
- Evidence and claims only store minimal slices and references.

---

## Redaction guidance
ELI5: If something looks sensitive, hide or shorten it before it goes into logs.
Technical:
- Avoid putting secrets or tokens inside Evidence or Claim ledgers.
- If file paths contain sensitive identifiers, replace with a stable alias.
- Prefer describing locations as `path:Lx-Ly` without quoting content when possible.

---

## Storage and retention
ELI5: Old logs should not stay forever.
Technical:
- Use `rotate_history.py` to keep ledgers under a size cap.
- Keep `.codex/zeno/` on encrypted disks when possible.
- Delete old snapshots periodically if they include sensitive content.

---

## OTEL privacy defaults
ELI5: Telemetry should not capture the user's full prompt by default.
Technical:
- Default `otel.log_user_prompt = false`.
- If you enable prompt logging, notify users and define retention and access policies.

## Acknowledgments
This skill is inspired by and references:
- Zhang et al., "Recursive Language Models" (arXiv:2512.24601v1): https://arxiv.org/abs/2512.24601v1
- Alex Zhang's reference implementation: https://github.com/alexzhang13/rlm
- Original announcement thread: https://x.com/a1zhang/status/2007566581409144852?s=46

Thank you to Alex Zhang and collaborators for the Zeno concept and open resources that informed this work.
