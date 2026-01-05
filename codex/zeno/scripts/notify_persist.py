#!/usr/bin/env python3
"""Persist Zeno state/evidence/claims on agent-turn-complete notifications."""

import json
import os
import re
import sys
import tempfile
import time
from collections import deque
from typing import Any, Dict, List, Optional, Tuple

STATE_START = "===ZENO_STATE_UPDATE_JSON==="
STATE_END = "===/ZENO_STATE_UPDATE_JSON==="
EVIDENCE_START = "===ZENO_EVIDENCE_LEDGER_JSONL==="
EVIDENCE_END = "===/ZENO_EVIDENCE_LEDGER_JSONL==="
CLAIMS_START = "===ZENO_CLAIM_LEDGER_JSONL==="
CLAIMS_END = "===/ZENO_CLAIM_LEDGER_JSONL==="

DEFAULT_LEDGER_MAX_BYTES = 20 * 1024 * 1024
DEFAULT_HISTORY_TAIL_LINES = 500


def _utc_ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _safe_id(value: Optional[str]) -> str:
    if not value:
        return "unknown"
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", str(value))
    return safe or "unknown"


def _read_history_tail(history_path: str, max_lines: int) -> List[str]:
    if not os.path.exists(history_path):
        return []
    buf = deque(maxlen=max_lines)
    with open(history_path, "r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            buf.append(line)
    return list(buf)


def _last_assistant_from_history(lines: List[str]) -> Optional[str]:
    last_message = None
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            if obj.get("role") == "assistant" and isinstance(obj.get("content"), str):
                last_message = obj["content"]
            if isinstance(obj.get("message"), dict):
                msg = obj["message"]
                if msg.get("role") == "assistant" and isinstance(msg.get("content"), str):
                    last_message = msg["content"]
            if isinstance(obj.get("assistant_message"), str):
                last_message = obj["assistant_message"]
    return last_message


def _extract_block(text: str, start: str, end: str) -> Optional[str]:
    if not text:
        return None
    start_idx = text.rfind(start)
    if start_idx == -1:
        return None
    start_idx += len(start)
    end_idx = text.find(end, start_idx)
    if end_idx == -1:
        return None
    return text[start_idx:end_idx].strip()


def _parse_state_block(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _parse_jsonl_block(text: str) -> List[Dict[str, Any]]:
    if not text:
        return []
    items: List[Dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            items.append(obj)
    return items


def _find_repo_root(cwd: str) -> str:
    cur = os.path.abspath(cwd)
    while True:
        if os.path.isdir(os.path.join(cur, ".git")):
            return cur
        if os.path.isdir(os.path.join(cur, ".codex")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return cwd
        cur = parent


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _atomic_write_json(path: str, payload: Dict[str, Any]) -> None:
    _ensure_dir(os.path.dirname(path))
    fd, tmp_path = tempfile.mkstemp(prefix=".tmp-", dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=True, indent=2))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def _append_jsonl(path: str, items: List[Dict[str, Any]]) -> None:
    if not items:
        return
    _ensure_dir(os.path.dirname(path))
    with open(path, "a", encoding="utf-8") as handle:
        for item in items:
            handle.write(json.dumps(item, ensure_ascii=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _append_notify_log(path: str, message: str) -> None:
    try:
        _ensure_dir(os.path.dirname(path))
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(message.rstrip("\n") + "\n")
            handle.flush()
            os.fsync(handle.fileno())
    except OSError:
        return


def _rotate_if_needed(path: str, max_bytes: int) -> None:
    if not os.path.exists(path):
        return
    size = os.path.getsize(path)
    if size <= max_bytes:
        return
    timestamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    rotated = f"{path}.{timestamp}"
    os.replace(path, rotated)


def _normalize_evidence(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    now = _utc_ts()
    normalized = []
    for item in items:
        item = dict(item)
        item.setdefault("timestamp", now)
        item.setdefault("hash", "")
        normalized.append(item)
    return normalized


def _normalize_claims(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    now = _utc_ts()
    normalized = []
    for item in items:
        item = dict(item)
        item.setdefault("timestamp", now)
        item.setdefault("confidence", "")
        normalized.append(item)
    return normalized


def _default_state(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "thread_id": payload.get("thread-id") or payload.get("thread_id") or "unknown",
        "turn_id": payload.get("turn-id") or payload.get("turn_id") or "unknown",
        "cwd": payload.get("cwd") or "",
        "mode": "read-only",
        "budgets": payload.get("budgets") or {},
        "high_level_summary": "",
        "open_questions": [],
        "next_retrieval_plan": [],
        "timestamp": _utc_ts(),
    }


def main() -> int:
    if len(sys.argv) < 2:
        print("notify_persist.py expects a JSON payload in argv[1]", file=sys.stderr)
        return 2

    try:
        payload = json.loads(sys.argv[1])
    except json.JSONDecodeError as exc:
        print(f"invalid JSON payload: {exc}", file=sys.stderr)
        return 2

    event_type = payload.get("type")
    if event_type != "agent-turn-complete":
        return 0

    codex_home = os.environ.get("CODEX_HOME", os.path.expanduser("~/.codex"))
    history_path = os.path.join(codex_home, "history.jsonl")
    history_tail = _read_history_tail(history_path, DEFAULT_HISTORY_TAIL_LINES)

    last_assistant_message = payload.get("last-assistant-message") or payload.get("last_assistant_message")
    if not last_assistant_message:
        last_assistant_message = _last_assistant_from_history(history_tail)

    state_block = _extract_block(last_assistant_message or "", STATE_START, STATE_END)
    evidence_block = _extract_block(last_assistant_message or "", EVIDENCE_START, EVIDENCE_END)
    claims_block = _extract_block(last_assistant_message or "", CLAIMS_START, CLAIMS_END)

    state = _parse_state_block(state_block) or _default_state(payload)
    evidence_items = _normalize_evidence(_parse_jsonl_block(evidence_block))
    claim_items = _normalize_claims(_parse_jsonl_block(claims_block))

    thread_id = _safe_id(state.get("thread_id") or payload.get("thread-id") or payload.get("thread_id"))
    turn_id = _safe_id(state.get("turn_id") or payload.get("turn-id") or payload.get("turn_id"))

    cwd = payload.get("cwd") or os.getcwd()
    repo_root = _find_repo_root(cwd)
    zeno_root = os.path.join(repo_root, ".codex", "zeno")
    state_path = os.path.join(zeno_root, "state", f"{thread_id}.json")
    evidence_path = os.path.join(zeno_root, "evidence", f"{thread_id}.jsonl")
    claims_path = os.path.join(zeno_root, "claims", f"{thread_id}.jsonl")
    snapshot_path = os.path.join(zeno_root, "snapshots", thread_id, f"{turn_id}.json")
    notify_log_path = os.environ.get("ZENO_NOTIFY_LOG") or os.path.join(zeno_root, "notify.log")

    state_payload = dict(state)
    state_payload.setdefault("thread_id", thread_id)
    state_payload.setdefault("turn_id", turn_id)
    state_payload.setdefault("cwd", cwd)
    state_payload.setdefault("timestamp", _utc_ts())

    _atomic_write_json(state_path, state_payload)

    max_bytes = int(os.environ.get("ZENO_LEDGER_MAX_BYTES", DEFAULT_LEDGER_MAX_BYTES))
    _rotate_if_needed(evidence_path, max_bytes)
    _rotate_if_needed(claims_path, max_bytes)

    _append_jsonl(evidence_path, evidence_items)
    _append_jsonl(claims_path, claim_items)

    snapshot_payload = {
        "thread_id": thread_id,
        "turn_id": turn_id,
        "payload": payload,
        "state": state_payload,
        "evidence": evidence_items,
        "claims": claim_items,
    }
    _atomic_write_json(snapshot_path, snapshot_payload)

    log_line = (
        f"{_utc_ts()} zeno_checkpoint thread_id={thread_id} turn_id={turn_id} "
        f"evidence={len(evidence_items)} claims={len(claim_items)} state_block={bool(state_block)}"
    )
    _append_notify_log(notify_log_path, log_line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())