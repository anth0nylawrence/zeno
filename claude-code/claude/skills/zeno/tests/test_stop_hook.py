import json
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = str(ROOT / "scripts" / "stop.py")


def test_stop_hook_persists_ledgers():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir) / "repo"
        repo_root.mkdir()
        (repo_root / ".git").mkdir()

        transcript = repo_root / "transcript.jsonl"
        assistant_message = (
            "Summary.\n"
            "===ZENO_STATE_UPDATE_JSON===\n"
            "{ \"thread_id\":\"T1\", \"turn_id\":\"U1\", \"mode\":\"read-only\", \"budgets\":{}, "
            "\"high_level_summary\":\"x\", \"open_questions\":[], \"next_retrieval_plan\":[], "
            "\"timestamp\":\"2026-01-04T18:11:30Z\" }\n"
            "===/ZENO_STATE_UPDATE_JSON===\n"
            "\n===ZENO_EVIDENCE_LEDGER_JSONL===\n"
            "{\"evidence_id\":\"E1\",\"kind\":\"read\",\"path\":\"README.md\",\"lines\":[1,1],\"why\":\"demo\",\"hash\":\"\",\"timestamp\":\"2026-01-04T18:11:30Z\"}\n"
            "===/ZENO_EVIDENCE_LEDGER_JSONL===\n"
            "\n===ZENO_CLAIM_LEDGER_JSONL===\n"
            "{\"claim_id\":\"C1\",\"claim\":\"demo\",\"evidence\":[\"E1\"],\"confidence\":\"high\",\"timestamp\":\"2026-01-04T18:11:30Z\"}\n"
            "===/ZENO_CLAIM_LEDGER_JSONL===\n"
        )
        transcript.write_text(json.dumps({"role": "assistant", "content": assistant_message}) + "\n")

        payload = {
            "type": "Stop",
            "thread-id": "T1",
            "turn-id": "U1",
            "cwd": str(repo_root),
            "transcript_path": str(transcript),
        }

        env = os.environ.copy()
        env["CLAUDE_PROJECT_DIR"] = str(repo_root)
        result = subprocess.run(
            ["python3", SCRIPT],
            input=json.dumps(payload),
            text=True,
            env=env,
            check=False,
        )
        assert result.returncode == 0

        base = repo_root / ".claude" / "zeno"
        assert (base / "state" / "T1.json").exists()
        assert (base / "evidence" / "T1.jsonl").exists()
        assert (base / "claims" / "T1.jsonl").exists()
        assert (base / "notify.log").exists()