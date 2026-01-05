#!/usr/bin/env python3
"""Claude Code PreCompact hook: snapshot before compaction."""

import time
from pathlib import Path

from zeno_hook_utils import (
    DEFAULT_CONTEXT_CLAIMS,
    DEFAULT_CONTEXT_EVIDENCE,
    atomic_write_json,
    get_thread_id,
    load_payload,
    load_latest_state,
    zeno_root,
    tail_jsonl,
    _utc_ts,
)


def main() -> int:
    payload = load_payload()
    root = zeno_root(payload)
    thread_id = get_thread_id(payload)

    state_dir = root / "state"
    evidence_dir = root / "evidence"
    claims_dir = root / "claims"

    state = load_latest_state(state_dir, thread_id)
    evidence = tail_jsonl(evidence_dir / f"{thread_id}.jsonl", DEFAULT_CONTEXT_EVIDENCE)
    claims = tail_jsonl(claims_dir / f"{thread_id}.jsonl", DEFAULT_CONTEXT_CLAIMS)

    timestamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    snapshot_dir = root / "snapshots" / thread_id / "precompact"
    snapshot_path = snapshot_dir / f"{timestamp}.json"

    payload_out = {
        "thread_id": thread_id,
        "timestamp": _utc_ts(),
        "payload": payload,
        "state": state,
        "evidence": evidence,
        "claims": claims,
    }

    atomic_write_json(snapshot_path, payload_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())