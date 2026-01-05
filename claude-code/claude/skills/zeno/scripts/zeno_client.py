#!/usr/bin/env python3
"""Tiny client CLI for the Zeno JSONL server."""

import argparse
import json
import os
import subprocess
import sys
import time
from collections import deque
from typing import Dict


def _load_args(json_text: str | None) -> Dict:
    if not json_text:
        return {}
    try:
        return json.loads(json_text)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid --args JSON: {exc}")


def _send_request(args: argparse.Namespace) -> int:
    request_id = args.id or f"req-{int(time.time())}"

    if args.request:
        try:
            payload = json.loads(args.request)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Invalid --request JSON: {exc}")
    else:
        payload = {
            "id": request_id,
            "op": args.op,
            "args": _load_args(args.args),
        }

    server_path = os.path.join(os.path.dirname(__file__), "zeno_server.py")
    cmd = ["python3", server_path, "--root", args.root]
    if args.log:
        cmd += ["--log", args.log]

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    assert proc.stdin is not None
    assert proc.stdout is not None

    proc.stdin.write(json.dumps(payload) + "\n")
    proc.stdin.flush()
    proc.stdin.close()

    response = proc.stdout.readline()
    if not response:
        return 1

    if args.pretty:
        try:
            data = json.loads(response)
        except json.JSONDecodeError:
            print(response.strip())
        else:
            print(json.dumps(data, indent=2))
    else:
        print(response.strip())

    return proc.wait(timeout=5)


def _tail_file(args: argparse.Namespace) -> int:
    path = args.log
    if not os.path.exists(path):
        raise SystemExit(f"Log file not found: {path}")

    lines = int(args.lines or 0)
    follow = bool(args.follow)

    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        if lines > 0:
            buf = deque(maxlen=lines)
            for line in handle:
                buf.append(line)
            for line in buf:
                print(line.rstrip("\n"))
        else:
            for line in handle:
                print(line.rstrip("\n"))

        if not follow:
            return 0

        while True:
            line = handle.readline()
            if line:
                print(line.rstrip("\n"))
                continue
            time.sleep(0.2)


def main() -> int:
    parser = argparse.ArgumentParser(description="Zeno client CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    send = sub.add_parser("send", help="Send a single JSONL request")
    send.add_argument("--root", required=True, help="Root directory for the server")
    send.add_argument("--op", help="Operation name")
    send.add_argument("--args", help="JSON string for args")
    send.add_argument("--id", help="Request id")
    send.add_argument("--log", help="Log file path for the server")
    send.add_argument("--pretty", action="store_true", help="Pretty print JSON response")
    send.add_argument("--request", help="Raw JSON request (overrides --op/--args)")

    tail = sub.add_parser("tail", help="Tail a JSONL log file")
    tail.add_argument("--log", required=True, help="Log file path")
    tail.add_argument("--lines", type=int, default=0, help="Print last N lines before follow")
    tail.add_argument("--follow", action="store_true", help="Follow new lines")

    args = parser.parse_args()
    if args.command == "send":
        if not args.request and not args.op:
            raise SystemExit("--op is required unless --request is provided")
        return _send_request(args)
    if args.command == "tail":
        return _tail_file(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())