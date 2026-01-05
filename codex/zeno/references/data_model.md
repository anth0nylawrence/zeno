# Zeno Data Model

## Plain-English overview
ELI5: This file defines the shapes of the receipts (evidence), the statements (claims), and the progress snapshot (state) so tools can read them reliably.
Technical: These schemas define the canonical JSON structures emitted by the agent and persisted by `notify_persist.py`.

---

## Evidence item
ELI5: A receipt that says where a fact came from.
Technical: A JSON object with a stable ID and location reference.

Required fields:
- `evidence_id` (string): unique ID, e.g. "E12".
- `kind` (string): "read" or "grep".
- `why` (string): one-line reason this evidence supports a claim.
- `timestamp` (string): UTC ISO timestamp.

Fields for kind = "read":
- `path` (string): file path relative to repo root.
- `lines` (array[int,int]): [start_line, end_line].

Fields for kind = "grep":
- `pattern` (string): pattern used.
- `hit` (string): "path:L123".

Optional fields:
- `hash` (string): content hash, if computed.

Example:
```json
{"evidence_id":"E1","kind":"read","path":"src/main.py","lines":[10,24],"why":"Shows the FastAPI app initialization","hash":"","timestamp":"2026-01-04T18:11:30Z"}
```

---

## Claim item
ELI5: A statement that must point to the receipts that prove it.
Technical: A JSON object with a claim ID and list of evidence IDs.

Required fields:
- `claim_id` (string): unique ID, e.g. "C3".
- `claim` (string): the assertion.
- `evidence` (array[string]): list of evidence IDs.
- `confidence` (string): "high", "med", "low".
- `timestamp` (string): UTC ISO timestamp.

Example:
```json
{"claim_id":"C1","claim":"The app starts via FastAPI in app.py","evidence":["E1"],"confidence":"high","timestamp":"2026-01-04T18:11:40Z"}
```

---

## State update
ELI5: A compact summary of progress and next steps at the end of each turn.
Technical: A JSON object emitted in ZENO_STATE_UPDATE_JSON and persisted per thread.

Required fields:
- `thread_id` (string)
- `turn_id` (string)
- `mode` (string): "read-only"
- `budgets` (object)
- `high_level_summary` (string)
- `open_questions` (array[string])
- `next_retrieval_plan` (array[object])
- `timestamp` (string)

Budgets schema (recommended):
- `retrieval_ops_max` (int)
- `retrieval_ops_used` (int)
- `read_lines_max` (int)
- `read_lines_used` (int)
- `grep_hits_max` (int)
- `grep_hits_used` (int)

Next retrieval plan item (recommended):
- `op` (string)
- `args` (object)
- `purpose` (string)

Example:
```json
{
  "thread_id":"T1",
  "turn_id":"U4",
  "mode":"read-only",
  "budgets":{
    "retrieval_ops_max":30,
    "retrieval_ops_used":12,
    "read_lines_max":2000,
    "read_lines_used":740,
    "grep_hits_max":200,
    "grep_hits_used":55
  },
  "high_level_summary":"Mapped entrypoints and routing for the service",
  "open_questions":["Where is auth middleware registered?"],
  "next_retrieval_plan":[
    {"op":"grep","args":{"pattern":"Auth","paths":["**/*.py"],"max_hits":50},"purpose":"Locate auth wiring"}
  ],
  "timestamp":"2026-01-04T18:11:55Z"
}
```

## Acknowledgments
This skill is inspired by and references:
- Zhang et al., "Recursive Language Models" (arXiv:2512.24601v1): https://arxiv.org/abs/2512.24601v1
- Alex Zhang's reference implementation: https://github.com/alexzhang13/rlm
- Original announcement thread: https://x.com/a1zhang/status/2007566581409144852?s=46

Thank you to Alex Zhang and collaborators for the Zeno concept and open resources that informed this work.
