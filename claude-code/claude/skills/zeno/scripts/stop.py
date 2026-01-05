#!/usr/bin/env python3
"""Claude Code Stop hook: persist state/evidence/claims from transcript."""

import json
import os
import time
from pathlib import Path

from zeno_hook_utils import (
    DEFAULT_LEDGER_MAX_BYTES,
    DEFAULT_TAIL_LINES,
    append_jsonl,
    atomic_write_json,
    default_state,
    file_lock,
    get_thread_id,
    get_turn_id,
    load_payload,
    normalize_claims,
    normalize_evidence,
    parse_blocks,
    read_transcript_incremental,
    zeno_root,
    rotate_if_needed,
    write_status,
    _last_assistant_message,
    _read_transcript_tail,
    _utc_ts,
)


def _append_notify_log(path: Path, message: str) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(message.rstrip("\n") + "\n")
            handle.flush()
            os.fsync(handle.fileno())
    except OSError:
        return


def main() -> int:
    payload = load_payload()
    root = zeno_root(payload)
    state_dir = root / "state"
    evidence_dir = root / "evidence"
    claims_dir = root / "claims"
    snapshot_dir = root / "snapshots"
    cursor_dir = root / "cursors"
    status_path = root / "status.json"
    notify_log = root / "notify.log"
    lock_path = root / ".lock"

    thread_id = get_thread_id(payload)
    turn_id = get_turn_id(payload)

    state_block = None
    evidence_items = []
    claim_items = []

    try:
        root.mkdir(parents=True, exist_ok=True)
        with file_lock(lock_path):
            cursor_path = cursor_dir / f"{thread_id}.json"
            objs, _ = read_transcript_incremental(payload, cursor_path)

            last_message = _last_assistant_message(objs)
            if not last_message:
                transcript_path = payload.get("transcript_path") or payload.get("transcript-path")
                if transcript_path:
                    tail_objs = _read_transcript_tail(Path(transcript_path), DEFAULT_TAIL_LINES)
                    last_message = _last_assistant_message(tail_objs)

            if last_message:
                state_block, evidence_items, claim_items = parse_blocks(last_message)

            state = state_block or default_state(payload)
            state.setdefault("thread_id", thread_id)
            state.setdefault("turn_id", turn_id)
            state.setdefault("timestamp", _utc_ts())

            evidence_items = normalize_evidence(evidence_items)
            claim_items = normalize_claims(claim_items)

            state_path = state_dir / f"{thread_id}.json"
            evidence_path = evidence_dir / f"{thread_id}.jsonl"
            claims_path = claims_dir / f"{thread_id}.jsonl"
            snapshot_path = snapshot_dir / thread_id / f"{turn_id}.json"

            max_bytes = int(os.environ.get("ZENO_LEDGER_MAX_BYTES", DEFAULT_LEDGER_MAX_BYTES))
            rotate_if_needed(evidence_path, max_bytes)
            rotate_if_needed(claims_path, max_bytes)

            atomic_write_json(state_path, state)
            append_jsonl(evidence_path, evidence_items)
            append_jsonl(claims_path, claim_items)

            snapshot_payload = {
                "thread_id": thread_id,
                "turn_id": turn_id,
                "timestamp": _utc_ts(),
                "payload": payload,
                "state": state,
                "evidence": evidence_items,
                "claims": claim_items,
                "state_block_present": bool(state_block),
            }
            atomic_write_json(snapshot_path, snapshot_payload)

            log_line = (
                f"{_utc_ts()} zeno_checkpoint thread_id={thread_id} turn_id={turn_id} "
                f"evidence={len(evidence_items)} claims={len(claim_items)} state_block={bool(state_block)}"
            )
            _append_notify_log(notify_log, log_line)

        write_status(status_path, True, "ok", payload)
        return 0
    except Exception as exc:  # noqa: BLE001
        write_status(status_path, False, str(exc), payload)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())