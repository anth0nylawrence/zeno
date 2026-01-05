#!/usr/bin/env python3
"""Rotate JSONL history files by size."""

import argparse
import os
import time


DEFAULT_MAX_BYTES = 20 * 1024 * 1024
DEFAULT_KEEP = 5


def _rotate(path: str, max_bytes: int, keep: int) -> bool:
    if not os.path.exists(path):
        return False
    size = os.path.getsize(path)
    if size <= max_bytes:
        return False
    timestamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    rotated = f"{path}.{timestamp}"
    os.replace(path, rotated)
    open(path, "a", encoding="utf-8").close()

    if keep > 0:
        base = os.path.basename(path)
        dir_name = os.path.dirname(path) or "."
        candidates = [
            os.path.join(dir_name, name)
            for name in os.listdir(dir_name)
            if name.startswith(base + ".")
        ]
        candidates.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        for old in candidates[keep:]:
            try:
                os.remove(old)
            except OSError:
                pass
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Rotate JSONL files by size")
    parser.add_argument("--path", action="append", required=True, help="Path to JSONL file")
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    parser.add_argument("--keep", type=int, default=DEFAULT_KEEP)
    args = parser.parse_args()

    rotated_any = False
    for path in args.path:
        rotated_any = _rotate(path, args.max_bytes, args.keep) or rotated_any

    return 0 if rotated_any else 0


if __name__ == "__main__":
    raise SystemExit(main())