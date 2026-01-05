import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = str(ROOT / "scripts" / "log_lint.py")


def _write_jsonl(path: Path, items):
    path.write_text("\n".join(json.dumps(item) for item in items) + "\n")


def test_log_lint_ok():
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        evidence = base / "evidence.jsonl"
        claims = base / "claims.jsonl"
        _write_jsonl(
            evidence,
            [
                {
                    "evidence_id": "E1",
                    "kind": "read",
                    "path": "src/main.py",
                    "lines": [1, 2],
                    "why": "x",
                    "timestamp": "2026-01-04T18:11:30Z",
                }
            ],
        )
        _write_jsonl(
            claims,
            [
                {
                    "claim_id": "C1",
                    "claim": "entrypoint",
                    "evidence": ["E1"],
                    "confidence": "high",
                    "timestamp": "2026-01-04T18:11:30Z",
                }
            ],
        )
        result = subprocess.run(["python3", SCRIPT, "--evidence", str(evidence), "--claims", str(claims)])
        assert result.returncode == 0


def test_log_lint_missing_evidence():
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        evidence = base / "evidence.jsonl"
        claims = base / "claims.jsonl"
        _write_jsonl(
            evidence,
            [
                {
                    "evidence_id": "E1",
                    "kind": "read",
                    "path": "src/main.py",
                    "lines": [1, 2],
                    "why": "x",
                    "timestamp": "2026-01-04T18:11:30Z",
                }
            ],
        )
        _write_jsonl(
            claims,
            [
                {
                    "claim_id": "C1",
                    "claim": "entrypoint",
                    "evidence": ["E2"],
                    "confidence": "high",
                    "timestamp": "2026-01-04T18:11:30Z",
                }
            ],
        )
        result = subprocess.run(["python3", SCRIPT, "--evidence", str(evidence), "--claims", str(claims)])
        assert result.returncode == 2