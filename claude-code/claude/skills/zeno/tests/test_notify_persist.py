import json
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = str(ROOT / "scripts" / "notify_persist.py")


def test_notify_persist_writes_ledgers():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir) / "repo"
        repo_root.mkdir()
        (repo_root / ".git").mkdir()

        codex_home = Path(tmpdir) / "codex_home"
        codex_home.mkdir()
        history_path = codex_home / "history.jsonl"

        assistant_message = (
            "Summary.\n"
            "===ZENO_STATE_UPDATE_JSON===\n"
            "{ \"thread_id\":\"T1\", \"turn_id\":\"U1\", \"mode\":\"read-only\", \"budgets\":{}, "
            "\"high_level_summary\":\"x\", \"open_questions\":[], \"next_retrieval_plan\":[], "
            "\"timestamp\":\"2026-01-04T18:11:30Z\" }\n"
            "===/ZENO_STATE_UPDATE_JSON===\n"
            "\n===ZENO_EVIDENCE_LEDGER_JSONL===\n"
            "{\"evidence_id\":\"E1\",\"kind\":\"read\",\"path\":\"src/main.py\",\"lines\":[1,2],\"why\":\"x\",\"hash\":\"\",\"timestamp\":\"2026-01-04T18:11:30Z\"}\n"
            "===/ZENO_EVIDENCE_LEDGER_JSONL===\n"
            "\n===ZENO_CLAIM_LEDGER_JSONL===\n"
            "{\"claim_id\":\"C1\",\"claim\":\"y\",\"evidence\":[\"E1\"],\"confidence\":\"high\",\"timestamp\":\"2026-01-04T18:11:30Z\"}\n"
            "===/ZENO_CLAIM_LEDGER_JSONL===\n"
        )
        history_path.write_text(json.dumps({"role": "assistant", "content": assistant_message}) + "\n")

        payload = {
            "type": "agent-turn-complete",
            "thread-id": "T1",
            "turn-id": "U1",
            "cwd": str(repo_root),
            "last-assistant-message": assistant_message,
        }

        env = os.environ.copy()
        env["CODEX_HOME"] = str(codex_home)
        subprocess.run(["python3", SCRIPT, json.dumps(payload)], check=True, env=env)

        state_path = repo_root / ".codex" / "zeno" / "state" / "T1.json"
        evidence_path = repo_root / ".codex" / "zeno" / "evidence" / "T1.jsonl"
        claims_path = repo_root / ".codex" / "zeno" / "claims" / "T1.jsonl"

        assert state_path.exists()
        assert evidence_path.exists()
        assert claims_path.exists()