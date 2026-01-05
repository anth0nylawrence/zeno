#!/usr/bin/env python3
"""Shared helpers for Claude Code Zeno hooks."""

import json
import os
import time
from collections import deque
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

STATE_START = "===ZENO_STATE_UPDATE_JSON==="
STATE_END = "===/ZENO_STATE_UPDATE_JSON==="
EVIDENCE_START = "===ZENO_EVIDENCE_LEDGER_JSONL==="
EVIDENCE_END = "===/ZENO_EVIDENCE_LEDGER_JSONL==="
CLAIMS_START = "===ZENO_CLAIM_LEDGER_JSONL==="
CLAIMS_END = "===/ZENO_CLAIM_LEDGER_JSONL==="

DEFAULT_LEDGER_MAX_BYTES = 20 * 1024 * 1024
DEFAULT_TAIL_LINES = 500
DEFAULT_CONTEXT_EVIDENCE = 5
DEFAULT_CONTEXT_CLAIMS = 5


def _utc_ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def load_payload() -> Dict[str, Any]:
    raw = os.sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def get_project_dir(payload: Dict[str, Any]) -> Path:
    env_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if env_dir:
        return Path(env_dir)
    for key in ("project_dir", "project-dir", "cwd"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return Path(value)
    return Path.cwd()


def zeno_root(payload: Dict[str, Any]) -> Path:
    env_root = os.environ.get("ZENO_ROOT")
    if env_root:
        return Path(env_root)
    return get_project_dir(payload) / ".claude" / "zeno"


def _safe_id(value: Optional[str]) -> str:
    if not value:
        return "unknown"
    safe = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in str(value))
    return safe or "unknown"


def get_thread_id(payload: Dict[str, Any]) -> str:
    for key in ("thread-id", "thread_id", "session-id", "session_id", "conversation-id", "conversation_id"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return _safe_id(value)
    return "unknown"


def get_turn_id(payload: Dict[str, Any]) -> str:
    for key in ("turn-id", "turn_id", "message-id", "message_id"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return _safe_id(value)
    return _safe_id(str(int(time.time())))


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    ensure_dir(path.parent)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True, indent=2))
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    tmp_path.replace(path)


def append_jsonl(path: Path, items: Iterable[Dict[str, Any]]) -> None:
    items = list(items)
    if not items:
        return
    ensure_dir(path.parent)
    with path.open("a", encoding="utf-8") as handle:
        for item in items:
            handle.write(json.dumps(item, ensure_ascii=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def rotate_if_needed(path: Path, max_bytes: int) -> None:
    if not path.exists():
        return
    size = path.stat().st_size
    if size <= max_bytes:
        return
    timestamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    rotated = path.with_name(path.name + f".{timestamp}")
    path.replace(rotated)


@contextmanager
def file_lock(lock_path: Path, timeout_s: float = 2.0):
    start = time.time()
    lock_fd = None
    while True:
        try:
            lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(lock_fd, str(os.getpid()).encode("utf-8"))
            break
        except FileExistsError:
            if time.time() - start > timeout_s:
                lock_fd = None
                break
            time.sleep(0.1)
    try:
        yield lock_fd is not None
    finally:
        if lock_fd is not None:
            os.close(lock_fd)
            try:
                lock_path.unlink()
            except OSError:
                pass


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


def parse_blocks(message: str) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    state_block = _extract_block(message, STATE_START, STATE_END)
    evidence_block = _extract_block(message, EVIDENCE_START, EVIDENCE_END)
    claims_block = _extract_block(message, CLAIMS_START, CLAIMS_END)

    state = None
    if state_block:
        try:
            state = json.loads(state_block)
        except json.JSONDecodeError:
            state = None

    evidence_items = []
    if evidence_block:
        for line in evidence_block.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                evidence_items.append(obj)

    claim_items = []
    if claims_block:
        for line in claims_block.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                claim_items.append(obj)

    return state, evidence_items, claim_items


def default_state(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "thread_id": payload.get("thread-id") or payload.get("thread_id") or payload.get("session-id") or payload.get("session_id") or "unknown",
        "turn_id": payload.get("turn-id") or payload.get("turn_id") or "unknown",
        "mode": "read-only",
        "budgets": {},
        "high_level_summary": "",
        "open_questions": [],
        "next_retrieval_plan": [],
        "timestamp": _utc_ts(),
    }


def normalize_evidence(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    now = _utc_ts()
    normalized = []
    for item in items:
        item = dict(item)
        item.setdefault("timestamp", now)
        item.setdefault("hash", "")
        normalized.append(item)
    return normalized


def normalize_claims(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    now = _utc_ts()
    normalized = []
    for item in items:
        item = dict(item)
        item.setdefault("timestamp", now)
        item.setdefault("confidence", "")
        normalized.append(item)
    return normalized


def _last_assistant_message(objs: Iterable[Dict[str, Any]]) -> Optional[str]:
    last = None
    for obj in objs:
        if not isinstance(obj, dict):
            continue
        if obj.get("role") == "assistant" and isinstance(obj.get("content"), str):
            last = obj["content"]
        msg = obj.get("message")
        if isinstance(msg, dict) and msg.get("role") == "assistant" and isinstance(msg.get("content"), str):
            last = msg["content"]
        if isinstance(obj.get("assistant_message"), str):
            last = obj["assistant_message"]
    return last


def _read_transcript_tail(path: Path, max_lines: int) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    buf = deque(maxlen=max_lines)
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            buf.append(line)
    objs = []
    for line in buf:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        objs.append(obj)
    return objs


def read_transcript_incremental(payload: Dict[str, Any], cursor_path: Path) -> Tuple[List[Dict[str, Any]], int]:
    transcript = payload.get("transcript_path") or payload.get("transcript-path")
    if not transcript:
        return [], 0
    path = Path(transcript)
    if not path.exists():
        return [], 0

    offset = 0
    if cursor_path.exists():
        try:
            data = json.loads(cursor_path.read_text(encoding="utf-8"))
            if data.get("path") == str(path):
                offset = int(data.get("offset", 0))
        except Exception:
            offset = 0

    size = path.stat().st_size
    if offset > size:
        offset = 0

    objs: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        handle.seek(offset)
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            objs.append(obj)
        offset = handle.tell()

    ensure_dir(cursor_path.parent)
    cursor_path.write_text(json.dumps({"path": str(path), "offset": offset, "timestamp": _utc_ts()}), encoding="utf-8")
    return objs, offset


def load_latest_state(state_dir: Path, thread_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    if thread_id:
        candidate = state_dir / f"{thread_id}.json"
        if candidate.exists():
            return json.loads(candidate.read_text(encoding="utf-8"))
    if not state_dir.exists():
        return None
    candidates = list(state_dir.glob("*.json"))
    if not candidates:
        return None
    latest = max(candidates, key=lambda p: p.stat().st_mtime)
    return json.loads(latest.read_text(encoding="utf-8"))


def tail_jsonl(path: Path, max_items: int) -> List[Dict[str, Any]]:
    if max_items <= 0 or not path.exists():
        return []
    buf: deque = deque(maxlen=max_items)
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                buf.append(obj)
    return list(buf)


def write_status(status_path: Path, ok: bool, message: str, payload: Dict[str, Any]) -> None:
    data = {
        "ok": ok,
        "message": message,
        "timestamp": _utc_ts(),
        "thread_id": get_thread_id(payload),
        "turn_id": get_turn_id(payload),
    }
    try:
        atomic_write_json(status_path, data)
    except OSError:
        return