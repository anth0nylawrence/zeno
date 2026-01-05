# OpenTelemetry (Pattern B)

## Plain-English overview
ELI5: OTEL is a stream of small event records that show exactly which tools ran and what they returned.
Technical: Claude Code exports OTEL events via environment variables. A local collector writes JSONL for replay and indexing.

---

## Recommended Claude Code env
ELI5: Turn on telemetry without logging the full user prompt.
Technical:
```bash
export CLAUDE_CODE_ENABLE_TELEMETRY=1
export OTEL_METRICS_EXPORTER=otlp
export OTEL_LOGS_EXPORTER=otlp
export OTEL_EXPORTER_OTLP_PROTOCOL=grpc
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
export OTEL_LOG_USER_PROMPTS=0
```

---

## Collector setup
ELI5: The collector is a relay that saves events to a file so you can replay them later.
Technical:
- Use `configs/otel-collector.yaml`.
- It accepts OTLP via HTTP and gRPC.
- It writes JSONL to a local file path for audit and replay.

---

## What OTEL is used for
ELI5: It lets you answer: "Which grep made this claim?" and "Where did time go?"
Technical:
- Tool-level audit trails
- Budget enforcement across turns
- Latency tracing for slow operations
- Cross-checking Pattern A ledgers vs Pattern B events

---

## Offline operation
ELI5: If the network collector is down, Pattern A still saves the receipts.
Technical:
- Pattern A persists state and ledgers locally per turn.
- Pattern B is additive and can be disabled without losing checkpoints.

---

## Replay quickstart
ELI5: Filter the log to replay one run at a time.
Technical:
- If your collector writes to `~/.claude/otel/zeno-otel.jsonl`, filter by thread id:
```bash
jq 'select(.attributes[\"thread-id\"] == \"T1\")' ~/.claude/otel/zeno-otel.jsonl
```
- If you want per-thread files, split the stream:
```bash
python3 - <<'PY'
import json
from pathlib import Path

src = Path.home() / ".claude" / "otel" / "zeno-otel.jsonl"
out_dir = Path.home() / ".claude" / "otel" / "by-thread"
out_dir.mkdir(parents=True, exist_ok=True)

with src.open("r", encoding="utf-8", errors="replace") as handle:
    for line in handle:
        if not line.strip():
            continue
        obj = json.loads(line)
        attrs = obj.get("attributes") or {}
        thread_id = attrs.get("thread-id", "unknown")
        (out_dir / f"{thread_id}.jsonl").open("a", encoding="utf-8").write(line)
PY
```

## Acknowledgments
This skill is inspired by and references:
- Zhang et al., "Recursive Language Models" (arXiv:2512.24601v1): https://arxiv.org/abs/2512.24601v1
- Alex Zhang's reference implementation: https://github.com/alexzhang13/rlm
- Original announcement thread: https://x.com/a1zhang/status/2007566581409144852?s=46

Thank you to Alex Zhang and collaborators for the Zeno concept and open resources that informed this work.