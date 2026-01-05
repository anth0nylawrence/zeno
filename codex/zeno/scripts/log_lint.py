#!/usr/bin/env python3
"""Lint evidence/claim ledgers for consistency and budget violations."""

import argparse
import json
import sys
from typing import Dict, List, Tuple


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


def _load_json(path: str) -> Tuple[Dict, List[str]]:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return json.load(handle), []
    except Exception as exc:  # noqa: BLE001
        return {}, [f"{path} invalid JSON: {exc}"]


def _validate_evidence(items: List[Dict]) -> List[str]:
    errors: List[str] = []
    seen = set()
    for idx, item in enumerate(items, start=1):
        evidence_id = item.get("evidence_id")
        if not evidence_id:
            errors.append(f"evidence line {idx} missing evidence_id")
            continue
        if evidence_id in seen:
            errors.append(f"duplicate evidence_id: {evidence_id}")
        seen.add(evidence_id)
        kind = item.get("kind")
        if not kind:
            errors.append(f"evidence {evidence_id} missing kind")
        if kind == "read":
            if not item.get("path") or not item.get("lines"):
                errors.append(f"evidence {evidence_id} missing path/lines")
        if kind == "grep":
            if not item.get("pattern") and not item.get("hit"):
                errors.append(f"evidence {evidence_id} missing pattern/hit")
    return errors


def _validate_claims(items: List[Dict], evidence_ids: set) -> List[str]:
    errors: List[str] = []
    for idx, item in enumerate(items, start=1):
        claim_id = item.get("claim_id")
        if not claim_id:
            errors.append(f"claim line {idx} missing claim_id")
        evidence = item.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"claim {claim_id or idx} missing evidence list")
            continue
        missing = [ev for ev in evidence if ev not in evidence_ids]
        if missing:
            errors.append(f"claim {claim_id or idx} references missing evidence: {missing}")
    return errors


def _validate_budgets(state: Dict) -> List[str]:
    errors: List[str] = []
    budgets = state.get("budgets")
    if not isinstance(budgets, dict):
        return errors
    pairs = [
        ("retrieval_ops_used", "retrieval_ops_max"),
        ("read_lines_used", "read_lines_max"),
        ("grep_hits_used", "grep_hits_max"),
    ]
    for used_key, max_key in pairs:
        used = budgets.get(used_key)
        limit = budgets.get(max_key)
        if used is None or limit is None:
            continue
        try:
            if int(used) > int(limit):
                errors.append(f"budget violation: {used_key}={used} > {max_key}={limit}")
        except (TypeError, ValueError):
            errors.append(f"budget values invalid for {used_key}/{max_key}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint Zeno evidence/claim ledgers")
    parser.add_argument("--evidence", required=True, help="Evidence JSONL path")
    parser.add_argument("--claims", required=True, help="Claims JSONL path")
    parser.add_argument("--state", help="State JSON path")
    args = parser.parse_args()

    errors: List[str] = []
    evidence_items, evidence_errors = _load_jsonl(args.evidence)
    claim_items, claim_errors = _load_jsonl(args.claims)
    errors.extend(evidence_errors)
    errors.extend(claim_errors)

    errors.extend(_validate_evidence(evidence_items))
    evidence_ids = {item.get("evidence_id") for item in evidence_items if item.get("evidence_id")}
    errors.extend(_validate_claims(claim_items, evidence_ids))

    if args.state:
        state, state_errors = _load_json(args.state)
        errors.extend(state_errors)
        errors.extend(_validate_budgets(state))

    if errors:
        for err in errors:
            print(err, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())