#!/usr/bin/env python3
"""Mode-aware plan generator for Zeno workflows."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, Iterable, List


LANG_GLOBS: Dict[str, List[str]] = {
    "python": ["**/*.py"],
    "javascript": ["**/*.js"],
    "typescript": ["**/*.ts"],
    "node": ["**/*.js", "**/*.ts"],
    "swift": ["**/*.swift"],
    "rust": ["**/*.rs"],
    "go": ["**/*.go"],
    "java": ["**/*.java"],
    "ruby": ["**/*.rb"],
    "default": ["**/*.{py,js,ts,go,java,rb,swift,rs}"]
}

MODE_DESCRIPTIONS = {
    "codebase-archaeology": "Trace symbol definitions and usages with file:line evidence.",
    "security-audit": "Pattern-based vulnerability triage with evidence chains.",
    "architecture-mapping": "Map entrypoints, lifecycle, and boundaries with citations.",
    "pr-review": "Review changed files and downstream impacts with evidence (Git-aware).",
    "skill-generation": "Draft SKILL.md from a new tool repo using citations.",
    "deep-research": "Evidence-first research on large projects without hallucination.",
}

DEFAULT_SECURITY_PACK = Path(__file__).resolve().parents[1] / "references" / "security_patterns.json"


def _globs(language: str | None) -> List[str]:
    if not language:
        return LANG_GLOBS["default"]
    return LANG_GLOBS.get(language.lower(), LANG_GLOBS["default"])


def _expand(pattern: str, replacements: Dict[str, str]) -> str:
    value = pattern
    for key, repl in replacements.items():
        value = value.replace(f"<{key}>", repl)
    return value


def _load_security_pack(path: Path) -> List[Dict]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("patterns", [])


def _git_changed_files(root: Path, base: str | None, head: str | None) -> List[str]:
    cmd = ["git", "-C", str(root), "diff", "--name-only"]
    if base and head:
        cmd.append(f"{base}...{head}")
    elif base:
        cmd.append(base)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _build_ops(mode: str, args: argparse.Namespace) -> List[Dict]:
    symbol = args.symbol or "<SYMBOL>"
    key_term = args.key_term or "<KEY_TERM>"
    changed_files = args.changed or []
    globs = _globs(args.language)

    replacements = {
        "SYMBOL": symbol,
        "KEY_TERM": key_term,
    }

    if mode == "codebase-archaeology":
        return [
            {"id": "arch-1", "op": "list_files", "args": {"glob": globs[0], "max": 400}, "purpose": "scope files"},
            {"id": "arch-2", "op": "grep", "args": {"pattern": _expand("def <SYMBOL>", replacements), "paths": globs, "max_hits": 50}, "purpose": "find definitions"},
            {"id": "arch-3", "op": "grep", "args": {"pattern": _expand("<SYMBOL>", replacements), "paths": globs, "max_hits": 200}, "purpose": "find usages"},
        ]

    if mode == "security-audit":
        pack_path = Path(args.pack).resolve() if args.pack else DEFAULT_SECURITY_PACK
        patterns = _load_security_pack(pack_path)
        if args.max_patterns:
            patterns = patterns[: args.max_patterns]
        ops = [{"id": "sec-1", "op": "list_files", "args": {"glob": globs[0], "max": 400}, "purpose": "scope files"}]
        for idx, item in enumerate(patterns, start=2):
            paths = item.get("globs") or globs
            op_args = {"pattern": item.get("pattern", ""), "paths": paths, "max_hits": 50}
            if item.get("regex"):
                op_args["regex"] = True
            ops.append({
                "id": f"sec-{idx}",
                "op": "grep",
                "args": op_args,
                "purpose": f"{item.get('category','pattern')}:{item.get('id','')}:{item.get('severity','')}".strip(":"),
            })
        return ops

    if mode == "architecture-mapping":
        return [
            {"id": "archmap-1", "op": "list_files", "args": {"glob": "**/README*", "max": 50}, "purpose": "overview docs"},
            {"id": "archmap-2", "op": "list_files", "args": {"glob": globs[0], "max": 400}, "purpose": "source inventory"},
            {"id": "archmap-3", "op": "grep", "args": {"pattern": "main", "paths": globs, "max_hits": 100}, "purpose": "entrypoints"},
            {"id": "archmap-4", "op": "grep", "args": {"pattern": "router|routes|routing", "paths": globs, "max_hits": 100, "regex": True}, "purpose": "routing"},
        ]

    if mode == "pr-review":
        ops = []
        if args.git or args.base or args.head:
            git_root = Path(args.git_root).resolve() if args.git_root else Path.cwd()
            changed_files = _git_changed_files(git_root, args.base, args.head)
        for idx, path in enumerate(changed_files, start=1):
            ops.append({
                "id": f"pr-{idx}",
                "op": "read_file",
                "args": {"path": path, "start_line": 1, "end_line": 200, "max_lines": 200},
                "purpose": "review changed file",
            })
        if not ops:
            ops.append({
                "id": "pr-1",
                "op": "read_file",
                "args": {"path": "<CHANGED_FILE>", "start_line": 1, "end_line": 200, "max_lines": 200},
                "purpose": "review changed file",
            })
        ops.append({
            "id": "pr-usage",
            "op": "grep",
            "args": {"pattern": _expand("<SYMBOL>", replacements), "paths": globs, "max_hits": 100},
            "purpose": "find downstream usage",
        })
        return ops

    if mode == "skill-generation":
        return [
            {"id": "skill-1", "op": "list_files", "args": {"glob": "**/README*", "max": 50}, "purpose": "docs"},
            {"id": "skill-2", "op": "list_files", "args": {"glob": "**/*.{md,txt}", "max": 200}, "purpose": "docs inventory"},
            {"id": "skill-3", "op": "grep", "args": {"pattern": "Usage|CLI|Command", "paths": ["**/*.md"], "max_hits": 50, "regex": True}, "purpose": "usage sections"},
        ]

    if mode == "deep-research":
        return [
            {"id": "research-1", "op": "list_files", "args": {"glob": "**/*.{md,txt}", "max": 200}, "purpose": "docs inventory"},
            {"id": "research-2", "op": "grep", "args": {"pattern": _expand("<KEY_TERM>", replacements), "paths": ["**/*.{md,txt}"], "max_hits": 100}, "purpose": "key term hits"},
            {"id": "research-3", "op": "read_file", "args": {"path": "<DOC_PATH>", "start_line": 1, "end_line": 160, "max_lines": 160}, "purpose": "read target section"},
        ]

    raise SystemExit(f"Unknown mode: {mode}")


def _print_jsonl(ops: Iterable[Dict]) -> None:
    for op in ops:
        sys.stdout.write(json.dumps(op, ensure_ascii=True) + "\n")


def _print_text(mode: str, ops: Iterable[Dict]) -> None:
    sys.stdout.write(f"Mode: {mode}\n")
    for op in ops:
        sys.stdout.write(f"- {op['id']}: {op['op']} {json.dumps(op['args'], ensure_ascii=True)} ({op.get('purpose','')})\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Zeno mode plan generator")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List available modes")

    describe = sub.add_parser("describe", help="Describe a mode")
    describe.add_argument("--mode", required=True, choices=sorted(MODE_DESCRIPTIONS))

    plan = sub.add_parser("plan", help="Generate a plan for a mode")
    plan.add_argument("--mode", required=True, choices=sorted(MODE_DESCRIPTIONS))
    plan.add_argument("--language", help="Language hint (python, node, swift, rust, go, java, ruby)")
    plan.add_argument("--symbol", help="Symbol name for archaeology or PR review")
    plan.add_argument("--key-term", help="Key term for deep research")
    plan.add_argument("--changed", nargs="*", help="Changed files for PR review")
    plan.add_argument("--format", choices=["jsonl", "json", "text"], default="jsonl")
    plan.add_argument("--git", action="store_true", help="Use git diff to populate changed files")
    plan.add_argument("--git-root", help="Git repo root for pr-review")
    plan.add_argument("--base", help="Base ref for git diff (e.g., origin/main)")
    plan.add_argument("--head", help="Head ref for git diff")
    plan.add_argument("--pack", help="Security pattern pack JSON path")
    plan.add_argument("--max-patterns", type=int, help="Limit number of security patterns")

    args = parser.parse_args()

    if args.command == "list":
        for name in sorted(MODE_DESCRIPTIONS):
            sys.stdout.write(f"{name}: {MODE_DESCRIPTIONS[name]}\n")
        return 0

    if args.command == "describe":
        sys.stdout.write(f"{args.mode}: {MODE_DESCRIPTIONS[args.mode]}\n")
        return 0

    if args.command == "plan":
        ops = _build_ops(args.mode, args)
        if args.format == "jsonl":
            _print_jsonl(ops)
        elif args.format == "json":
            payload = {"mode": args.mode, "ops": ops}
            sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")
        else:
            _print_text(args.mode, ops)
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
