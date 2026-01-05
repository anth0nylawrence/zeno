import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = str(ROOT / "scripts" / "verify_evidence.py")


def _write_jsonl(path: Path, items) -> None:
    path.write_text("\n".join(json.dumps(item) for item in items) + "\n", encoding="utf-8")


def test_verify_evidence_ok():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        src = root / "src"
        src.mkdir()
        target = src / "main.py"
        target.write_text("line1\nline2\nline3\n", encoding="utf-8")

        evidence = root / "evidence.jsonl"
        _write_jsonl(
            evidence,
            [
                {"evidence_id": "E1", "kind": "read", "path": "src/main.py", "lines": [1, 2]},
                {"evidence_id": "E2", "kind": "grep", "hit": "src/main.py:L2"},
            ],
        )

        result = subprocess.run(
            ["python3", SCRIPT, "--root", str(root), "--evidence", str(evidence)],
            check=False,
        )
        assert result.returncode == 0


def test_verify_evidence_out_of_bounds():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        src = root / "src"
        src.mkdir()
        target = src / "main.py"
        target.write_text("line1\nline2\n", encoding="utf-8")

        evidence = root / "evidence.jsonl"
        _write_jsonl(
            evidence,
            [
                {"evidence_id": "E1", "kind": "read", "path": "src/main.py", "lines": [1, 5]},
            ],
        )

        result = subprocess.run(
            ["python3", SCRIPT, "--root", str(root), "--evidence", str(evidence)],
            check=False,
        )
        assert result.returncode == 2