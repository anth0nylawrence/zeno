#!/usr/bin/env python3
"""Claude Code UserPromptSubmit hook for Zeno context injection."""

import json

from zeno_hook_utils import (
    DEFAULT_CONTEXT_CLAIMS,
    DEFAULT_CONTEXT_EVIDENCE,
    load_payload,
    load_latest_state,
    zeno_root,
    tail_jsonl,
)


def _load_status(path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def main() -> int:
    payload = load_payload()
    root = zeno_root(payload)
    state_dir = root / "state"
    evidence_dir = root / "evidence"
    claims_dir = root / "claims"
    status_path = root / "status.json"

    status = _load_status(status_path)
    state = load_latest_state(state_dir)
    if not state:
        return 0

    thread_id = state.get("thread_id", "unknown")
    evidence = tail_jsonl(evidence_dir / f"{thread_id}.jsonl", DEFAULT_CONTEXT_EVIDENCE)
    claims = tail_jsonl(claims_dir / f"{thread_id}.jsonl", DEFAULT_CONTEXT_CLAIMS)

    print("[ZENO_CONTEXT_BRIDGE]")
    if status and not status.get("ok", True):
        print(f"warning: last persist failed: {status.get('message', '')}")
    print(f"thread_id: {thread_id}")
    print(f"summary: {state.get('high_level_summary', '')}")
    open_questions = state.get("open_questions") or []
    if open_questions:
        print("open_questions:")
        for question in open_questions:
            print(f"- {question}")
    if claims:
        print("recent_claims:")
        for item in claims:
            claim_id = item.get("claim_id", "")
            claim = item.get("claim", "")
            confidence = item.get("confidence", "")
            evidence_ids = item.get("evidence", [])
            print(f"- {claim_id} ({confidence}) {claim} -> {evidence_ids}")
    if evidence:
        print("recent_evidence:")
        for item in evidence:
            ev_id = item.get("evidence_id", "")
            kind = item.get("kind", "")
            if kind == "read":
                print(f"- {ev_id} read {item.get('path', '')}:{item.get('lines', [])}")
            elif kind == "grep":
                print(f"- {ev_id} grep {item.get('hit', '')}")
            else:
                print(f"- {ev_id} {kind}")
    print("Use this block as context for the next response.")
    print("[/ZENO_CONTEXT_BRIDGE]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())