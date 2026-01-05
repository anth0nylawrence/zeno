#!/usr/bin/env python3
"""Tiny JSONL REPL server for read-only corpus access."""

import argparse
import fnmatch
import json
import os
import re
import sys
import time
from collections import deque
from typing import Dict, Iterable, List, Tuple

DEFAULT_MAX_FILES = 20000
DEFAULT_MAX_LINES = 400
DEFAULT_MAX_HITS = 200
DEFAULT_MAX_BYTES = 2_000_000
DEFAULT_EXCLUDE_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    ".next",
    ".turbo",
    ".cache",
    ".pytest_cache",
}

SYMBOL_PATTERNS: List[Tuple[str, re.Pattern]] = [
    ("class", re.compile(r"^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)")),
    ("struct", re.compile(r"^\s*struct\s+([A-Za-z_][A-Za-z0-9_]*)")),
    ("enum", re.compile(r"^\s*enum\s+([A-Za-z_][A-Za-z0-9_]*)")),
    ("protocol", re.compile(r"^\s*protocol\s+([A-Za-z_][A-Za-z0-9_]*)")),
    ("extension", re.compile(r"^\s*extension\s+([A-Za-z_][A-Za-z0-9_]*)")),
    ("func", re.compile(r"^\s*func\s+([A-Za-z_][A-Za-z0-9_]*)")),
    ("def", re.compile(r"^\s*def\s+([A-Za-z_][A-Za-z0-9_]*)")),
    ("function", re.compile(r"^\s*function\s+([A-Za-z_][A-Za-z0-9_]*)")),
    ("interface", re.compile(r"^\s*interface\s+([A-Za-z_][A-Za-z0-9_]*)")),
    ("type", re.compile(r"^\s*type\s+([A-Za-z_][A-Za-z0-9_]*)")),
    ("const", re.compile(r"^\s*const\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\(")),
]


def _utc_ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _now_ms() -> int:
    return int(time.monotonic() * 1000)


def _write_json(obj: Dict) -> None:
    sys.stdout.write(json.dumps(obj, ensure_ascii=True) + "\n")
    sys.stdout.flush()


def _log(log_handle, event: Dict) -> None:
    if not log_handle:
        return
    log_handle.write(json.dumps(event, ensure_ascii=True) + "\n")
    log_handle.flush()


def _realpath(path: str) -> str:
    return os.path.realpath(path)


class ZenoServer:
    def __init__(self, root: str, log_handle) -> None:
        self.root = _realpath(root)
        self.log_handle = log_handle

    def _resolve(self, path: str) -> str:
        if os.path.isabs(path):
            candidate = _realpath(path)
        else:
            candidate = _realpath(os.path.join(self.root, path))
        if candidate == self.root:
            return candidate
        if not candidate.startswith(self.root + os.sep):
            raise ValueError("path outside root")
        return candidate

    def _rel(self, path: str) -> str:
        return os.path.relpath(path, self.root)

    def _iter_files(
        self,
        include_hidden: bool,
        exclude_dirs: Iterable[str],
        exclude_globs: Iterable[str],
        max_files: int,
    ) -> Tuple[List[str], int]:
        results: List[str] = []
        scanned = 0
        exclude_dir_set = set(exclude_dirs)
        for root, dirs, files in os.walk(self.root):
            if not include_hidden:
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                files = [f for f in files if not f.startswith(".")]
            dirs[:] = [d for d in dirs if d not in exclude_dir_set]
            for fname in files:
                full = os.path.join(root, fname)
                rel = os.path.relpath(full, self.root)
                scanned += 1
                if any(fnmatch.fnmatchcase(rel, g) for g in exclude_globs):
                    continue
                results.append(rel)
                if len(results) >= max_files:
                    return sorted(results), scanned
        return sorted(results), scanned

    def list_files(self, args: Dict) -> Dict:
        start_ms = _now_ms()
        glob_pat = args.get("glob")
        regex_pat = args.get("regex")
        max_n = int(args.get("max", 500))
        include_hidden = bool(args.get("include_hidden", False))
        exclude_dirs = args.get("exclude_dirs") or []
        exclude_globs = args.get("exclude_globs") or []
        exclude_dirs = list(set(exclude_dirs).union(DEFAULT_EXCLUDE_DIRS))
        max_files = int(args.get("max_files", DEFAULT_MAX_FILES))
        files, scanned = self._iter_files(include_hidden, exclude_dirs, exclude_globs, max_files)

        matched: List[str] = []
        if glob_pat:
            for rel in files:
                if fnmatch.fnmatchcase(rel, glob_pat):
                    matched.append(rel)
        elif regex_pat:
            regex = re.compile(regex_pat)
            for rel in files:
                if regex.search(rel):
                    matched.append(rel)
        else:
            matched = files

        truncated = len(matched) > max_n
        result = {"files": matched[:max_n], "truncated": truncated}
        result["metrics"] = {
            "time_ms": _now_ms() - start_ms,
            "bytes_read": 0,
            "files_scanned": scanned,
        }
        return result

    def read_file(self, args: Dict) -> Dict:
        start_ms = _now_ms()
        path = args.get("path")
        if not path:
            raise ValueError("missing path")
        start_line = int(args.get("start_line", 1))
        end_line = int(args.get("end_line", start_line))
        max_lines = int(args.get("max_lines", DEFAULT_MAX_LINES))

        resolved = self._resolve(path)
        start_line = max(1, start_line)
        end_line = max(start_line, end_line)
        max_end_line = min(end_line, start_line + max_lines - 1)
        truncated = (end_line - start_line + 1) > max_lines

        excerpt: List[str] = []
        total_lines = 0
        bytes_read = 0
        with open(resolved, "r", encoding="utf-8", errors="replace") as handle:
            for idx, raw in enumerate(handle, start=1):
                total_lines = idx
                bytes_read += len(raw)
                line = raw.rstrip("\n")
                if idx < start_line:
                    continue
                if idx > max_end_line:
                    continue
                excerpt.append(line)

        if total_lines < start_line:
            end_line = total_lines
            excerpt = []
            truncated = False
        else:
            end_line = min(total_lines, max_end_line)

        result = {
            "path": self._rel(resolved),
            "start_line": start_line,
            "end_line": end_line,
            "total_lines": total_lines,
            "truncated": truncated,
            "text": "\n".join(excerpt),
        }
        result["metrics"] = {
            "time_ms": _now_ms() - start_ms,
            "bytes_read": bytes_read,
            "files_scanned": 1,
            "lines_returned": len(excerpt),
        }
        return result

    def peek(self, args: Dict) -> Dict:
        start_ms = _now_ms()
        path = args.get("path")
        if not path:
            raise ValueError("missing path")
        head_lines = int(args.get("head_lines", 60))
        tail_lines = int(args.get("tail_lines", 60))
        resolved = self._resolve(path)

        head: List[str] = []
        tail = deque(maxlen=max(0, tail_lines))
        total_lines = 0
        bytes_read = 0
        with open(resolved, "r", encoding="utf-8", errors="replace") as handle:
            for idx, raw in enumerate(handle, start=1):
                total_lines = idx
                bytes_read += len(raw)
                line = raw.rstrip("\n")
                if idx <= head_lines:
                    head.append(line)
                if tail_lines > 0:
                    tail.append(line)

        tail_list = list(tail)
        tail_start = max(1, total_lines - len(tail_list) + 1) if total_lines else 0

        result = {
            "path": self._rel(resolved),
            "total_lines": total_lines,
            "head": {
                "start_line": 1 if total_lines else 0,
                "end_line": len(head),
                "text": "\n".join(head),
            },
            "tail": {
                "start_line": tail_start,
                "end_line": total_lines,
                "text": "\n".join(tail_list),
            },
        }
        result["metrics"] = {
            "time_ms": _now_ms() - start_ms,
            "bytes_read": bytes_read,
            "files_scanned": 1,
        }
        return result

    def grep(self, args: Dict) -> Dict:
        start_ms = _now_ms()
        pattern = args.get("pattern")
        if not pattern:
            raise ValueError("missing pattern")
        paths = args.get("paths")
        max_hits = int(args.get("max_hits", DEFAULT_MAX_HITS))
        context = int(args.get("context", 0))
        include_hidden = bool(args.get("include_hidden", False))
        exclude_dirs = args.get("exclude_dirs") or []
        exclude_globs = args.get("exclude_globs") or []
        exclude_dirs = list(set(exclude_dirs).union(DEFAULT_EXCLUDE_DIRS))
        regex_enabled = bool(args.get("regex", False))
        case_sensitive = bool(args.get("case_sensitive", True))

        max_files = int(args.get("max_files", DEFAULT_MAX_FILES))
        max_bytes = int(args.get("max_bytes", DEFAULT_MAX_BYTES))
        all_files, scanned = self._iter_files(include_hidden, exclude_dirs, exclude_globs, max_files)
        selected: List[str] = []
        if paths:
            for rel in all_files:
                if any(fnmatch.fnmatchcase(rel, p) or rel == p for p in paths):
                    selected.append(rel)
        else:
            selected = all_files

        if regex_enabled:
            flags = 0 if case_sensitive else re.IGNORECASE
            regex = re.compile(pattern, flags)

            def is_match(line: str) -> bool:
                return bool(regex.search(line))

        else:
            needle = pattern if case_sensitive else pattern.lower()

            def is_match(line: str) -> bool:
                hay = line if case_sensitive else line.lower()
                return needle in hay

        hits = []
        bytes_read = 0
        files_scanned = 0
        for rel in selected:
            full = self._resolve(rel)
            files_scanned += 1
            try:
                size = os.path.getsize(full)
            except OSError:
                continue
            if size > max_bytes:
                continue
            try:
                with open(full, "r", encoding="utf-8", errors="replace") as handle:
                    prev_lines = deque(maxlen=context)
                    pending: deque = deque()
                    line_iter = enumerate(handle, start=1)
                    while True:
                        try:
                            idx, raw = pending.popleft() if pending else next(line_iter)
                        except StopIteration:
                            break
                        bytes_read += len(raw)
                        line = raw.rstrip("\n")
                        if is_match(line):
                            hit = {
                                "path": rel,
                                "line": idx,
                                "text": line,
                            }
                            if context > 0:
                                ctx_lines = list(prev_lines)
                                ctx_lines.append({"line": idx, "text": line})
                                future = []
                                for _ in range(context):
                                    try:
                                        next_idx, next_raw = next(line_iter)
                                    except StopIteration:
                                        break
                                    bytes_read += len(next_raw)
                                    next_line = next_raw.rstrip("\n")
                                    future.append({"line": next_idx, "text": next_line})
                                    pending.append((next_idx, next_raw))
                                if future:
                                    ctx_lines.extend(future)
                                hit["context"] = ctx_lines
                            hits.append(hit)
                            if len(hits) >= max_hits:
                                result = {"hits": hits, "truncated": True}
                                result["metrics"] = {
                                    "time_ms": _now_ms() - start_ms,
                                    "bytes_read": bytes_read,
                                    "files_scanned": files_scanned,
                                    "hits": len(hits),
                                }
                                return result
                        prev_lines.append({"line": idx, "text": line})
            except OSError:
                continue

        result = {"hits": hits, "truncated": False}
        result["metrics"] = {
            "time_ms": _now_ms() - start_ms,
            "bytes_read": bytes_read,
            "files_scanned": files_scanned,
            "hits": len(hits),
        }
        return result

    def extract_symbols(self, args: Dict) -> Dict:
        start_ms = _now_ms()
        path = args.get("path")
        if not path:
            raise ValueError("missing path")
        max_symbols = int(args.get("max_symbols", 400))
        resolved = self._resolve(path)

        symbols = []
        bytes_read = 0
        with open(resolved, "r", encoding="utf-8", errors="replace") as handle:
            for idx, raw in enumerate(handle, start=1):
                bytes_read += len(raw)
                line = raw.rstrip("\n")
                for kind, regex in SYMBOL_PATTERNS:
                    match = regex.search(line)
                    if match:
                        symbols.append({"kind": kind, "name": match.group(1), "line": idx})
                        if len(symbols) >= max_symbols:
                            result = {"path": self._rel(resolved), "symbols": symbols, "truncated": True}
                            result["metrics"] = {
                                "time_ms": _now_ms() - start_ms,
                                "bytes_read": bytes_read,
                                "files_scanned": 1,
                                "symbols": len(symbols),
                            }
                            return result
        result = {"path": self._rel(resolved), "symbols": symbols, "truncated": False}
        result["metrics"] = {
            "time_ms": _now_ms() - start_ms,
            "bytes_read": bytes_read,
            "files_scanned": 1,
            "symbols": len(symbols),
        }
        return result

    def stat(self, args: Dict) -> Dict:
        start_ms = _now_ms()
        path = args.get("path")
        paths = list(args.get("paths") or [])
        if path:
            paths.insert(0, path)
        if not paths:
            raise ValueError("missing path")

        items = []
        for raw_path in paths:
            resolved = self._resolve(raw_path)
            try:
                st = os.stat(resolved)
            except OSError as exc:
                items.append({"path": raw_path, "exists": False, "error": str(exc)})
                continue
            items.append(
                {
                    "path": self._rel(resolved),
                    "exists": True,
                    "size": st.st_size,
                    "mtime": st.st_mtime,
                    "mtime_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(st.st_mtime)),
                    "is_file": os.path.isfile(resolved),
                    "is_dir": os.path.isdir(resolved),
                }
            )

        result = {"items": items}
        result["metrics"] = {
            "time_ms": _now_ms() - start_ms,
            "bytes_read": 0,
            "files_scanned": len(items),
        }
        return result


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="JSONL REPL server for Zeno workflows")
    parser.add_argument("--root", required=True, help="Root directory to serve")
    parser.add_argument("--log", help="Optional JSONL log file path")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    log_handle = None
    if args.log:
        log_handle = open(args.log, "a", encoding="utf-8")
    server = ZenoServer(args.root, log_handle)

    ops = {
        "list_files": server.list_files,
        "read_file": server.read_file,
        "grep": server.grep,
        "peek": server.peek,
        "extract_symbols": server.extract_symbols,
        "stat": server.stat,
    }

    for raw in sys.stdin:
        line = raw.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError as exc:
            _write_json({"id": None, "ok": False, "error": {"message": str(exc)}})
            continue

        req_id = request.get("id")
        op = request.get("op")
        args_dict = request.get("args") or {}
        _log(log_handle, {"ts": _utc_ts(), "event": "request", "id": req_id, "op": op, "args": args_dict})

        if op not in ops:
            error = {"message": f"unknown op: {op}"}
            _write_json({"id": req_id, "ok": False, "error": error})
            _log(log_handle, {"ts": _utc_ts(), "event": "error", "id": req_id, "error": error})
            continue

        try:
            result = ops[op](args_dict)
            response = {"id": req_id, "ok": True, "result": result}
            _write_json(response)
            metrics = result.get("metrics", {})
            _log(
                log_handle,
                {
                    "ts": _utc_ts(),
                    "event": "response",
                    "id": req_id,
                    "op": op,
                    "summary": {
                        "truncated": result.get("truncated"),
                        "count": len(result.get("files", []))
                        or len(result.get("hits", []))
                        or len(result.get("symbols", []))
                        or len(result.get("items", []))
                        or None,
                        "metrics": metrics,
                    },
                },
            )
        except Exception as exc:  # noqa: BLE001
            error = {"message": str(exc)}
            _write_json({"id": req_id, "ok": False, "error": error})
            _log(log_handle, {"ts": _utc_ts(), "event": "error", "id": req_id, "error": error})

    if log_handle:
        log_handle.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())