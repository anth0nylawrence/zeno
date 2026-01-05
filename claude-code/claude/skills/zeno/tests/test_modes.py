import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = str(ROOT / "scripts" / "zeno_modes.py")


def test_modes_list_contains_core_modes():
    result = subprocess.run(["python3", SCRIPT, "list"], capture_output=True, text=True)
    assert result.returncode == 0
    out = result.stdout
    assert "codebase-archaeology" in out
    assert "security-audit" in out
    assert "architecture-mapping" in out


def test_modes_plan_jsonl():
    result = subprocess.run(
        ["python3", SCRIPT, "plan", "--mode", "codebase-archaeology", "--format", "jsonl"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert lines
    payload = json.loads(lines[0])
    assert "op" in payload
    assert "args" in payload
