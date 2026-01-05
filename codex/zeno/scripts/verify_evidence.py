#!/usr/bin/env python3
"""Verify evidence references against the filesystem."""

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Tuple

HIT_RE = re.compile(r"^(.*):L(\d+)$")


def _load_jsonl(path: str) -> Tuple[List[Dict], List[str]]:
    items: List[Dict] = []
    errors: List[str] = []
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        for idx, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"{path}:{idx} invalid JSON: {exc}")
                continue
            if not isinstance(obj, dict):
                errors.append(f"{path}:{idx} not an object")
                continue
            items.append(obj)
    return items, errors


def _count_lines(path: str) -> int:
    count = 0
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        for _ in handle:
            count += 1
    return count


def _resolve(root: str, path: str) -> str:
    if os.path.isabs(path):
        return os.path.realpath(path)
    return os.path.realpath(os.path.join(root, path))


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify evidence ledger references")
    parser.add_argument("--root", required=True, help="Root directory for evidence paths")
    parser.add_argument("--evidence", required=True, help="Evidence JSONL path")
    args = parser.parse_args()

    evidence_items, errors = _load_jsonl(args.evidence)

    for item in evidence_items:
        evidence_id = item.get("evidence_id") or "unknown"
        kind = item.get("kind")
        if kind == "read":
            path = item.get("path")
            lines = item.get("lines")
            if not path or not isinstance(lines, list) or len(lines) != 2:
                errors.append(f"{evidence_id} invalid read evidence format")
                continue
            resolved = _resolve(args.root, path)
            if not os.path.exists(resolved):
                errors.append(f"{evidence_id} missing file: {path}")
                continue
            total = _count_lines(resolved)
            start, end = int(lines[0]), int(lines[1])
            if start < 1 or end < start or end > total:
                errors.append(f"{evidence_id} line range out of bounds: {path}:{start}-{end}")
        elif kind == "grep":
            hit = item.get("hit")
            if not hit or not isinstance(hit, str):
                errors.append(f"{evidence_id} missing grep hit")
                continue
            match = HIT_RE.match(hit)
            if not match:
                errors.append(f"{evidence_id} invalid hit format: {hit}")
                continue
            path, line_str = match.group(1), match.group(2)
            resolved = _resolve(args.root, path)
            if not os.path.exists(resolved):
                errors.append(f"{evidence_id} missing file: {path}")
                continue
            total = _count_lines(resolved)
            line_no = int(line_str)
            if line_no < 1 or line_no > total:
                errors.append(f"{evidence_id} line out of bounds: {path}:L{line_no}")
        else:
            errors.append(f"{evidence_id} unknown kind: {kind}")

    if errors:
        for err in errors:
            print(err, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())