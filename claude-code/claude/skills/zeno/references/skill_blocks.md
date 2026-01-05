# Zeno Mandatory Output Blocks (Claude Code)

When the Zeno skill is active, the assistant must end every response with three machine-parseable blocks in this exact order. These are parsed by the `Stop` hook and persisted to `.claude/zeno/`.

Hard rules:
- Blocks must be valid JSON/JSONL with no commentary inside.
- Order must be preserved.
- No trailing commas.

Required format:

```
===ZENO_STATE_UPDATE_JSON===
{ "thread_id":"T1", "turn_id":"U4", "mode":"read-only", "budgets":{"retrieval_ops_max":30,"retrieval_ops_used":12,"read_lines_max":2000,"read_lines_used":740,"grep_hits_max":200,"grep_hits_used":55}, "high_level_summary":"Mapped entrypoints and routing", "open_questions":["Where is auth middleware registered?"], "next_retrieval_plan":[{"op":"grep","args":{"pattern":"Auth","paths":["**/*.py"],"max_hits":50},"purpose":"Locate auth wiring"}] }
===/ZENO_STATE_UPDATE_JSON===

===ZENO_EVIDENCE_LEDGER_JSONL===
{"evidence_id":"E1","kind":"read","path":"src/app.py","lines":[10,44],"why":"Defines the FastAPI app construction","hash":"","timestamp":"2026-01-04T18:11:30Z"}
{"evidence_id":"E2","kind":"grep","pattern":"AuthMiddleware","hit":"src/security.py:L123","why":"Shows auth middleware registration","hash":"","timestamp":"2026-01-04T18:11:30Z"}
===/ZENO_EVIDENCE_LEDGER_JSONL===

===ZENO_CLAIM_LEDGER_JSONL===
{"claim_id":"C1","claim":"App starts in app.py with FastAPI","evidence":["E1"],"confidence":"high","timestamp":"2026-01-04T18:11:30Z"}
{"claim_id":"C2","claim":"Auth middleware registers in security.py","evidence":["E2"],"confidence":"med","timestamp":"2026-01-04T18:11:30Z"}
===/ZENO_CLAIM_LEDGER_JSONL===
```

If you are missing any field, leave it as an empty string or empty list rather than omitting the field.
