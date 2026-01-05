#!/usr/bin/env python3
"""Lightweight symbol + dependency indexer for Zeno workflows."""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

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

DEFAULT_EXCLUDE_GLOBS = ["**/*.min.*", "**/*.map", "**/generated/**", "**/vendor/**"]

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

IMPORT_PATTERNS: Dict[str, List[re.Pattern]] = {
    "python": [
        re.compile(r"^\s*import\s+([A-Za-z0-9_\.]+)"),
        re.compile(r"^\s*from\s+([A-Za-z0-9_\.]+)\s+import\s+"),
    ],
    "javascript": [
        re.compile(r"^\s*import\s+.*?from\s+[\"']([^\"']+)[\"']"),
        re.compile(r"^\s*const\s+.*?=\s*require\([\"']([^\"']+)[\"']\)"),
    ],
    "typescript": [
        re.compile(r"^\s*import\s+.*?from\s+[\"']([^\"']+)[\"']"),
        re.compile(r"^\s*const\s+.*?=\s*require\([\"']([^\"']+)[\"']\)"),
    ],
    "swift": [re.compile(r"^\s*import\s+([A-Za-z0-9_\.]+)"),],
    "go": [
        re.compile(r"^\s*import\s+\"([^\"]+)\""),
        re.compile(r"^\s*\"([^\"]+)\""),
    ],
    "rust": [re.compile(r"^\s*use\s+([^;]+);"),],
    "java": [re.compile(r"^\s*import\s+([^;]+);"),],
    "ruby": [re.compile(r"^\s*require\s+[\"']([^\"']+)[\"']"),],
}

EXT_LANGUAGE = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".swift": "swift",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".rb": "ruby",
}


def _utc_ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _iter_files(
    root: Path,
    include_hidden: bool,
    exclude_dirs: Iterable[str],
    exclude_globs: Iterable[str],
    max_files: int,
) -> List[Path]:
    results: List[Path] = []
    exclude_dir_set = set(exclude_dirs)
    for dirpath, dirs, files in os.walk(root):
        if not include_hidden:
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            files = [f for f in files if not f.startswith(".")]
        dirs[:] = [d for d in dirs if d not in exclude_dir_set]
        for fname in files:
            full = Path(dirpath) / fname
            rel = full.relative_to(root)
            if any(fnmatch.fnmatchcase(str(rel), g) for g in exclude_globs):
                continue
            results.append(full)
            if len(results) >= max_files:
                return results
    return results


def _detect_language(path: Path) -> Optional[str]:
    return EXT_LANGUAGE.get(path.suffix.lower())


def _scan_file(
    path: Path,
    root: Path,
    max_bytes: int,
    max_symbols: int,
    max_imports: int,
) -> Tuple[List[Dict], List[Dict], int]:
    symbols: List[Dict] = []
    imports: List[Dict] = []
    bytes_read = 0
    language = _detect_language(path)
    if not language:
        return symbols, imports, bytes_read

    try:
        size = path.stat().st_size
    except OSError:
        return symbols, imports, bytes_read

    if size > max_bytes:
        return symbols, imports, bytes_read

    patterns = IMPORT_PATTERNS.get(language, [])
    rel_path = str(path.relative_to(root))

    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for idx, raw in enumerate(handle, start=1):
                bytes_read += len(raw)
                line = raw.rstrip("\n")
                for kind, regex in SYMBOL_PATTERNS:
                    match = regex.search(line)
                    if match:
                        symbols.append(
                            {
                                "kind": kind,
                                "name": match.group(1),
                                "path": rel_path,
                                "line": idx,
                                "language": language,
                            }
                        )
                        if len(symbols) >= max_symbols:
                            break
                for regex in patterns:
                    match = regex.search(line)
                    if match:
                        imports.append(
                            {
                                "module": match.group(1).strip(),
                                "path": rel_path,
                                "line": idx,
                                "language": language,
                                "raw": line.strip(),
                            }
                        )
                        if len(imports) >= max_imports:
                            break
                if len(symbols) >= max_symbols and len(imports) >= max_imports:
                    break
    except OSError:
        return symbols, imports, bytes_read

    return symbols, imports, bytes_read


def _write_output(out_path: Optional[Path], payload: Dict, fmt: str) -> None:
    text = ""
    if fmt == "jsonl":
        lines: List[str] = []
        for symbol in payload.get("symbols", []):
            lines.append(json.dumps({"type": "symbol", **symbol}, ensure_ascii=True))
        for imp in payload.get("imports", []):
            lines.append(json.dumps({"type": "import", **imp}, ensure_ascii=True))
        text = "\n".join(lines) + ("\n" if lines else "")
    else:
        text = json.dumps(payload, indent=2, ensure_ascii=True) + "\n"

    if out_path:
        out_path.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


def main() -> int:
    parser = argparse.ArgumentParser(description="Zeno symbol + dependency indexer")
    parser.add_argument("--root", required=True, help="Root directory to index")
    parser.add_argument("--out", help="Output file path (JSON or JSONL)")
    parser.add_argument("--format", choices=["json", "jsonl"], default="json")
    parser.add_argument("--include-hidden", action="store_true")
    parser.add_argument("--max-files", type=int, default=20000)
    parser.add_argument("--max-bytes", type=int, default=2_000_000)
    parser.add_argument("--max-symbols", type=int, default=10000)
    parser.add_argument("--max-imports", type=int, default=10000)
    args = parser.parse_args()

    root = Path(args.root).resolve()
    files = _iter_files(
        root,
        args.include_hidden,
        DEFAULT_EXCLUDE_DIRS,
        DEFAULT_EXCLUDE_GLOBS,
        args.max_files,
    )

    symbols: List[Dict] = []
    imports: List[Dict] = []
    bytes_read = 0

    for path in files:
        file_symbols, file_imports, file_bytes = _scan_file(
            path,
            root,
            args.max_bytes,
            args.max_symbols - len(symbols),
            args.max_imports - len(imports),
        )
        symbols.extend(file_symbols)
        imports.extend(file_imports)
        bytes_read += file_bytes
        if len(symbols) >= args.max_symbols and len(imports) >= args.max_imports:
            break

    payload = {
        "root": str(root),
        "generated_at": _utc_ts(),
        "files_scanned": len(files),
        "symbols": symbols,
        "imports": imports,
        "stats": {
            "symbols": len(symbols),
            "imports": len(imports),
            "bytes_read": bytes_read,
        },
    }

    out_path = Path(args.out).resolve() if args.out else None
    _write_output(out_path, payload, args.format)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
