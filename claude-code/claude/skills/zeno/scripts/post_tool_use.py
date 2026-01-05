#!/usr/bin/env python3
"""Claude Code PostToolUse hook: append tool output events."""

from pathlib import Path

from zeno_hook_utils import (
    DEFAULT_LEDGER_MAX_BYTES,
    append_jsonl,
    get_thread_id,
    load_payload,
    zeno_root,
    rotate_if_needed,
    _utc_ts,
)


def main() -> int:
    payload = load_payload()
    root = zeno_root(payload)
    thread_id = get_thread_id(payload)

    tool_dir = root / "tool_events"
    tool_path = tool_dir / f"{thread_id}.jsonl"

    event = {
        "timestamp": _utc_ts(),
        "thread_id": thread_id,
        "payload": payload,
    }

    rotate_if_needed(tool_path, DEFAULT_LEDGER_MAX_BYTES)
    append_jsonl(tool_path, [event])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())