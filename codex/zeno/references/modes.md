# Zeno Modes (Detailed Spec)

This document defines the six supported Zeno modes. Each mode is a structured operating profile with a goal, inputs, default retrieval plan, output schema additions, and guardrails. Treat these as strict playbooks.

## Mode Index
- codebase-archaeology
- security-audit
- architecture-mapping
- pr-review
- skill-generation
- deep-research

---

## Mode: codebase-archaeology

### Goal
Trace where a symbol is defined and used across a large repo, with file:line citations and evidence chains.

### Inputs
- symbol (required)
- language or file globs (optional)
- paths (optional: scope the search)
- symbol_type (optional: function, class, method, constant)

### Default retrieval plan
1) list_files for target language or glob
2) grep for definition patterns (language-aware)
3) read_file the minimal definition block
4) grep for usage references
5) read_file snippets for each usage cluster

### Optional accelerator (index)
If the repo is large, precompute a lightweight index:
```bash
python3 scripts/zeno_index.py --root /path/to/repo --out /tmp/zeno_index.json
```
Use the index to narrow which files to grep and read.

### Output additions
- Definition capsule: file, signature, docstring, evidence
- Usage table: path, line, context, evidence id
- Usage graph hints: caller -> callee edges when visible
- Coverage statement: number of files scanned, hits, read lines

### Guardrails
- Avoid false positives: differentiate definition vs usage.
- If symbol is overloaded, split by module or namespace.
- If grep is truncated, narrow by paths or symbol type.

### JSONL plan (example)
```json
{"id":"arch-1","op":"list_files","args":{"glob":"**/*.py","max":400}}
{"id":"arch-2","op":"grep","args":{"pattern":"def my_symbol","paths":["**/*.py"],"max_hits":50}}
{"id":"arch-3","op":"read_file","args":{"path":"src/module.py","start_line":120,"end_line":180,"max_lines":120}}
{"id":"arch-4","op":"grep","args":{"pattern":"my_symbol","paths":["**/*.py"],"max_hits":200}}
```

---

## Mode: security-audit

### Goal
Triage common vulnerability patterns with explicit evidence chains. Produce a prioritized risk list with citations and next-evidence steps.

### Inputs
- language or file globs (optional)
- paths (optional)
- audit_focus (optional: auth, injection, secrets, crypto, deserialization, transport)

### Default retrieval plan
1) list_files for likely code and config
2) grep for high-risk sinks
3) grep for auth/validation guards
4) read_file around each hit for context
5) build evidence chains: source -> transform -> sink

### Pattern packs
Security patterns are defined in `references/security_patterns.json`. You can override the pack used by `zeno_modes.py`:
```bash
python3 scripts/zeno_modes.py plan --mode security-audit --pack /path/to/security_patterns.json --format jsonl
```

### Output additions
- Risk table with severity, evidence, and suggested follow-up
- Evidence chains: Source -> Validation -> Sink with citations
- Coverage statement with counts and exclusions

### Guardrails
- Heuristic only; do not claim exploitability without evidence.
- Prefer literal grep; enable regex only when necessary.
- If secrets are found, redact values in the report.

### Baseline patterns (language-agnostic)
- exec / eval: "eval(", "exec(", "Function(", "new Function("
- shell: "os.system", "subprocess", "child_process", "Runtime.getRuntime().exec"
- deserialization: "pickle.load", "yaml.load", "ObjectInputStream", "marshal.load"
- SQL: "SELECT " +, "INSERT " +, "UPDATE " +, "WHERE " +
- HTTP client: "requests.get", "fetch(", "axios", "http.Get"
- auth: "jwt.decode", "verify=False", "AllowAll", "disableAuth"
- filesystem: "../", "..\\", "path.join(" + user input

### JSONL plan (example)
```json
{"id":"sec-1","op":"list_files","args":{"glob":"**/*.{py,js,ts,go,java,rb}","max":400}}
{"id":"sec-2","op":"grep","args":{"pattern":"eval(","paths":["**/*.js","**/*.ts"],"max_hits":50}}
{"id":"sec-3","op":"grep","args":{"pattern":"subprocess","paths":["**/*.py"],"max_hits":50}}
{"id":"sec-4","op":"grep","args":{"pattern":"jwt.decode","paths":["**/*.py","**/*.js","**/*.ts"],"max_hits":50}}
```

---

## Mode: architecture-mapping

### Goal
Recursively map entrypoints, runtime lifecycle, and module boundaries without losing context. Produce a coherent system map with citations.

### Inputs
- language or stack (optional)
- scope (optional: service name or folder)

### Default retrieval plan
1) list_files for manifests and entrypoints
2) grep for main/bootstrap/router
3) read_file for entrypoints and routing
4) extract_symbols for core modules
5) grep for dependency wiring and config

### Optional accelerator (index)
If the repo is large, precompute a lightweight index:
```bash
python3 scripts/zeno_index.py --root /path/to/repo --out /tmp/zeno_index.json
```
Use the index to prioritize key modules and wiring paths.

### Output additions
- System map with lifecycle steps and evidence
- Component boundaries and responsibilities
- Data flow notes and call graph hints
- Coverage statement

### Guardrails
- No claims about full architecture without evidence.
- If multiple entrypoints exist, treat each separately.

---

## Mode: pr-review

### Goal
Review changes in large repos with full context: understand what changed, where it is used, and what could break.

### Inputs
- changed_files (required list)
- optional patch excerpt or commit message
- language or stack (optional)

### Git-aware option
You can auto-populate changed files from git:
```bash
python3 scripts/zeno_modes.py plan --mode pr-review --git --base origin/main --format jsonl
```

### Default retrieval plan
1) read_file each changed file around modified areas
2) grep for call sites and usage of changed symbols
3) read_file of downstream callers
4) check tests or docs related to changed files

### Output additions
- Change summary with evidence
- Impact map: changed file -> dependents
- Risk list: runtime, migration, API, test coverage
- Suggested follow-ups

### Guardrails
- If changed_files not provided, request it.
- Do not speculate about behavior without call-site evidence.

---

## Mode: skill-generation

### Goal
Analyze a new tool repo and draft an accurate SKILL.md with constraints, tools, and guardrails.

### Inputs
- target repo path
- tool name and summary (optional)
- allowed tools policy (optional)

### Default retrieval plan
1) list_files for docs, CLI entrypoints, and configs
2) read_file for README/usage and CLI help
3) extract_symbols for core modules
4) grep for configuration, environment variables, and limits

### Output additions
- Draft SKILL.md with YAML frontmatter
- Usage examples and guardrails with citations
- Limitations and safety notes

### Guardrails
- No tool claims without evidence in docs or code.
- If behavior is unclear, add Open Questions.

---

## Mode: deep-research

### Goal
Perform evidence-first research on a large project without hallucinating. Provide a structured report and claim ledger.

### Inputs
- research question
- scope or time budget

### Default retrieval plan
1) list_files for docs and overview materials
2) read_file for architecture and design docs
3) grep for key terms from the research question
4) read_file targeted sections
5) consolidate into claim-evidence ledger

### Output additions
- Research summary with claims and evidence
- Evidence ledger and open questions
- Next retrieval plan

### Guardrails
- Separate verified facts from hypotheses.
- Report coverage: files sampled, lines read, greps performed.

---

## Mode realism and appeal

- codebase-archaeology: high appeal, practical today, minimal risk.
- security-audit: high appeal, but must be framed as heuristic triage.
- architecture-mapping: high appeal for onboarding and systems review.
- pr-review: high appeal for large repos; requires changed_files list.
- skill-generation: medium appeal; requires strict evidence discipline.
- deep-research: high appeal for large projects with docs and specs.

---

## Acknowledgments
This skill is inspired by and references:
- Zhang et al., "Recursive Language Models" (arXiv:2512.24601v1): https://arxiv.org/abs/2512.24601v1
- Alex Zhang's reference implementation: https://github.com/alexzhang13/rlm
- Original announcement thread: https://x.com/a1zhang/status/2007566581409144852?s=46

Thank you to Alex Zhang and collaborators for the Zeno concept and open resources that informed this work.
