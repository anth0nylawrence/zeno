# Zeno Recipes (Copy/Paste)

This file provides ready-to-run retrieval plans for common stacks. Each recipe is a minimal set of JSONL requests to discover entrypoints, lifecycle, and wiring.

## Swift app entrypoint discovery
Goal: find App entrypoint, scene setup, and top-level navigation.

Requests (JSONL):
```json
{"id":"swift-1","op":"list_files","args":{"glob":"**/*.swift","max":200}}
{"id":"swift-2","op":"grep","args":{"pattern":"@main","paths":["**/*.swift"],"max_hits":50}}
{"id":"swift-3","op":"grep","args":{"pattern":"AppDelegate","paths":["**/*.swift"],"max_hits":50}}
{"id":"swift-4","op":"grep","args":{"pattern":"SceneDelegate","paths":["**/*.swift"],"max_hits":50}}
{"id":"swift-5","op":"grep","args":{"pattern":"App","paths":["**/*.swift"],"max_hits":50,"regex":true}}
```

Then read the minimal blocks around the @main App type or AppDelegate to map the lifecycle.

## Node CLI routing
Goal: find CLI entry, command registration, and handler wiring.

Requests (JSONL):
```json
{"id":"node-1","op":"list_files","args":{"glob":"**/*.js","max":200}}
{"id":"node-2","op":"list_files","args":{"glob":"**/*.ts","max":200}}
{"id":"node-3","op":"grep","args":{"pattern":"#!/usr/bin/env node","paths":["**/*.js","**/*.ts"],"max_hits":50}}
{"id":"node-4","op":"grep","args":{"pattern":"commander","paths":["**/*.js","**/*.ts"],"max_hits":50}}
{"id":"node-5","op":"grep","args":{"pattern":"yargs","paths":["**/*.js","**/*.ts"],"max_hits":50}}
```

Then read the small blocks that define commands and their handlers.

## Python service wiring
Goal: find entrypoints, ASGI/WSGI app creation, and routing.

Requests (JSONL):
```json
{"id":"py-1","op":"list_files","args":{"glob":"**/*.py","max":200}}
{"id":"py-2","op":"grep","args":{"pattern":"if __name__ == \"__main__\"","paths":["**/*.py"],"max_hits":50}}
{"id":"py-3","op":"grep","args":{"pattern":"FastAPI","paths":["**/*.py"],"max_hits":50}}
{"id":"py-4","op":"grep","args":{"pattern":"Flask","paths":["**/*.py"],"max_hits":50}}
{"id":"py-5","op":"grep","args":{"pattern":"uvicorn","paths":["**/*.py"],"max_hits":50}}
```

Then read the app factory or route registration blocks.

## Rust crate structure
Goal: locate entrypoints, lib modules, and main wiring.

Requests (JSONL):
```json
{"id":"rs-1","op":"list_files","args":{"glob":"Cargo.toml","max":20}}
{"id":"rs-2","op":"list_files","args":{"glob":"**/*.rs","max":200}}
{"id":"rs-3","op":"grep","args":{"pattern":"fn main","paths":["**/*.rs"],"max_hits":50}}
{"id":"rs-4","op":"grep","args":{"pattern":"mod ","paths":["**/*.rs"],"max_hits":50}}
```

Then read main.rs and lib.rs slices to build the module map.

## Codebase archaeology (trace symbol usage)
Goal: find definition and usage of a symbol across a large repo.

Requests (JSONL):
```json
{"id":"arch-1","op":"list_files","args":{"glob":"**/*.{py,js,ts,go,java,rb,swift,rs}","max":400}}
{"id":"arch-2","op":"grep","args":{"pattern":"def <SYMBOL>","paths":["**/*.py"],"max_hits":50}}
{"id":"arch-3","op":"grep","args":{"pattern":"<SYMBOL>","paths":["**/*.{py,js,ts}"],"max_hits":200}}
```

Then read the definition block and sample representative call sites.

## Security audit (pattern triage)
Goal: scan for common risky patterns with evidence.

Requests (JSONL):
```json
{"id":"sec-1","op":"grep","args":{"pattern":"eval(","paths":["**/*.js","**/*.ts"],"max_hits":50}}
{"id":"sec-2","op":"grep","args":{"pattern":"subprocess","paths":["**/*.py"],"max_hits":50}}
{"id":"sec-3","op":"grep","args":{"pattern":"yaml.load","paths":["**/*.py"],"max_hits":50}}
{"id":"sec-4","op":"grep","args":{"pattern":"jwt.decode","paths":["**/*.py","**/*.js","**/*.ts"],"max_hits":50}}
```

Then read the minimal context around each hit and build Source -> Validation -> Sink chains where visible.

## PR review (impact tracing)
Goal: review a set of changed files with usage tracing.

Requests (JSONL):
```json
{"id":"pr-1","op":"read_file","args":{"path":"<CHANGED_FILE>","start_line":1,"end_line":200,"max_lines":200}}
{"id":"pr-2","op":"grep","args":{"pattern":"<CHANGED_SYMBOL>","paths":["**/*.{py,js,ts,go,java,rb,swift,rs}"],"max_hits":100}}
```

Then read downstream call sites to assess impact.

## Skill generation (draft SKILL.md)
Goal: draft a SKILL.md from a new tool repo with evidence.

Requests (JSONL):
```json
{"id":"skill-1","op":"list_files","args":{"glob":"**/README*","max":50}}
{"id":"skill-2","op":"list_files","args":{"glob":"**/*.{md,txt}","max":200}}
{"id":"skill-3","op":"grep","args":{"pattern":"Usage","paths":["**/*.md"],"max_hits":50}}
```

Then read the usage sections and CLI entrypoints to draft SKILL.md with citations.

## Deep research (evidence-first)
Goal: answer a large research question without hallucination.

Requests (JSONL):
```json
{"id":"research-1","op":"list_files","args":{"glob":"**/*.{md,txt}","max":200}}
{"id":"research-2","op":"grep","args":{"pattern":"<KEY_TERM>","paths":["**/*.{md,txt}"],"max_hits":100}}
{"id":"research-3","op":"read_file","args":{"path":"<DOC_PATH>","start_line":1,"end_line":160,"max_lines":160}}
```

Then consolidate claims with an evidence ledger.

## Acknowledgments
This skill is inspired by and references:
- Zhang et al., "Recursive Language Models" (arXiv:2512.24601v1): https://arxiv.org/abs/2512.24601v1
- Alex Zhang's reference implementation: https://github.com/alexzhang13/rlm
- Original announcement thread: https://x.com/a1zhang/status/2007566581409144852?s=46

Thank you to Alex Zhang and collaborators for the Zeno concept and open resources that informed this work.
