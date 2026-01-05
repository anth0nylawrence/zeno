import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = str(ROOT / "scripts" / "zeno_index.py")


def test_index_basic():
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        src = base / "src"
        src.mkdir()
        (src / "app.py").write_text("""\nimport os\n\nclass Demo:\n    pass\n\n\ndef run():\n    return 1\n""", encoding="utf-8")
        out_path = base / "index.json"
        result = subprocess.run(
            ["python3", SCRIPT, "--root", str(base), "--out", str(out_path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        data = json.loads(out_path.read_text(encoding="utf-8"))
        assert data["stats"]["symbols"] >= 2
        assert data["stats"]["imports"] >= 1
