#!/usr/bin/env python3
"""Emit a context-bridge snippet from the latest Zeno state/evidence/claims."""

import argparse
import json
import os
import time
from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Optional


def _utc_ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _find_repo_root(start: Path) -> Optional[Path]:
    for parent in [start, *start.parents]:
        if (parent / ".git").is_dir() or (parent / ".codex").is_dir():
            return parent
    return None


def _default_zeno_root() -> Path:
    env_root = os.environ.get("ZENO_ROOT")
    if env_root:
        return Path(env_root)
    repo_root = _find_repo_root(Path.cwd())
    if repo_root:
        return repo_root / ".codex" / "zeno"
    return Path(os.path.expanduser("~/.codex/zeno"))


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        return json.load(handle)


def _tail_jsonl(path: Path, max_items: int) -> List[Dict[str, Any]]:
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


def _latest_state_path(state_dir: Path) -> Optional[Path]:
    if not state_dir.exists():
        return None
    candidates = list(state_dir.glob("*.json"))
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _format_text(
    state: Dict[str, Any],
    evidence: List[Dict[str, Any]],
    claims: List[Dict[str, Any]],
) -> str:
    lines = [
        "[ZENO_CONTEXT_BRIDGE]",
        f"thread_id: {state.get('thread_id', '')}",
        f"turn_id: {state.get('turn_id', '')}",
        f"timestamp: {state.get('timestamp', _utc_ts())}",
        f"summary: {state.get('high_level_summary', '')}",
    ]
    open_questions = state.get("open_questions") or []
    if open_questions:
        lines.append("open_questions:")
        for question in open_questions:
            lines.append(f"- {question}")

    if evidence:
        lines.append("recent_evidence:")
        for item in evidence:
            ev_id = item.get("evidence_id", "")
            kind = item.get("kind", "")
            if kind == "read":
                path = item.get("path", "")
                lines_range = item.get("lines", [])
                lines.append(f"- {ev_id} read {path}:{lines_range} why={item.get('why', '')}")
            elif kind == "grep":
                hit = item.get("hit", "")
                lines.append(f"- {ev_id} grep {hit} why={item.get('why', '')}")
            else:
                lines.append(f"- {ev_id} {kind}")

    if claims:
        lines.append("recent_claims:")
        for item in claims:
            claim_id = item.get("claim_id", "")
            confidence = item.get("confidence", "")
            evidence_ids = item.get("evidence", [])
            lines.append(
                f"- {claim_id} ({confidence}) {item.get('claim', '')} -> {evidence_ids}"
            )

    lines.append("Use this block as a preamble for the next prompt.")
    lines.append("[/ZENO_CONTEXT_BRIDGE]")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Emit an Zeno context bridge snippet")
    parser.add_argument("--zeno-root", help="Path to .codex/zeno")
    parser.add_argument("--thread-id", help="Thread id to load")
    parser.add_argument("--max-evidence", type=int, default=5)
    parser.add_argument("--max-claims", type=int, default=5)
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text")
    args = parser.parse_args()

    zeno_root = Path(args.zeno_root) if args.zeno_root else _default_zeno_root()
    state_dir = zeno_root / "state"
    evidence_dir = zeno_root / "evidence"
    claims_dir = zeno_root / "claims"

    if args.thread_id:
        state_path = state_dir / f"{args.thread_id}.json"
    else:
        state_path = _latest_state_path(state_dir)

    if not state_path or not state_path.exists():
        print(f"State file not found under {state_dir}", file=os.sys.stderr)
        return 2

    state = _load_json(state_path)
    thread_id = state.get("thread_id") or args.thread_id or ""
    evidence_path = evidence_dir / f"{thread_id}.jsonl"
    claims_path = claims_dir / f"{thread_id}.jsonl"

    evidence = _tail_jsonl(evidence_path, args.max_evidence)
    claims = _tail_jsonl(claims_path, args.max_claims)

    if args.json:
        payload = {
            "thread_id": thread_id,
            "turn_id": state.get("turn_id", ""),
            "timestamp": state.get("timestamp", _utc_ts()),
            "summary": state.get("high_level_summary", ""),
            "open_questions": state.get("open_questions", []),
            "recent_evidence": evidence,
            "recent_claims": claims,
        }
        print(json.dumps(payload, indent=2))
        return 0

    print(_format_text(state, evidence, claims))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())