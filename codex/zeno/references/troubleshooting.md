# Troubleshooting

## Plain-English overview
ELI5: If something looks wrong, check the three required blocks and the log files first.
Technical: This section lists common failure modes and their fixes.

---

## No state files written
ELI5: The helper did not see the required blocks.
Technical:
- Confirm the assistant output ended with the three Zeno blocks.
- Ensure `notify` is configured in `~/.codex/config.toml`.
- Check that `notify_persist.py` is executable and reachable.
- Check `.codex/zeno/notify.log` to confirm whether the hook is firing.

---

## Evidence or claims missing
ELI5: The receipts were not present or not parsed.
Technical:
- Validate the block markers and JSON syntax.
- Run `scripts/log_lint.py` against the ledger files.
- Check `~/.codex/history.jsonl` for the last assistant message.

---

## Context bridge shows no data
ELI5: The memory card has nothing to print yet.
Technical:
- Ensure `.codex/zeno/state/<thread-id>.json` exists.
- Run `scripts/zeno_context_bridge.py --zeno-root /path/to/repo/.codex/zeno`.
- If multiple threads exist, pass `--thread-id`.

---

## OTEL events not appearing
ELI5: The event stream is turned off or not connected.
Technical:
- Verify `[otel] exporter` in `config.toml`.
- Ensure the collector is running with `configs/otel-collector.yaml`.
- Confirm the collector file exporter path is writable.

---

## Grep too slow
ELI5: You are searching too much at once.
Technical:
- Narrow `paths` and reduce `max_files`.
- Use literal grep (default) and avoid regex unless needed.
- Increase `max_bytes` only when necessary.

---

## Evidence verification failures
ELI5: The receipt points to a file or line that does not exist.
Technical:
- Run `scripts/verify_evidence.py --root <repo> --evidence <ledger>`.
- Confirm that the file path and line ranges are accurate.
- Regenerate evidence entries with correct ranges.

## Acknowledgments
This skill is inspired by and references:
- Zhang et al., "Recursive Language Models" (arXiv:2512.24601v1): https://arxiv.org/abs/2512.24601v1
- Alex Zhang's reference implementation: https://github.com/alexzhang13/rlm
- Original announcement thread: https://x.com/a1zhang/status/2007566581409144852?s=46

Thank you to Alex Zhang and collaborators for the Zeno concept and open resources that informed this work.