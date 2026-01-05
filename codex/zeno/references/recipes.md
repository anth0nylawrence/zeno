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

## Acknowledgments
This skill is inspired by and references:
- Zhang et al., "Recursive Language Models" (arXiv:2512.24601v1): https://arxiv.org/abs/2512.24601v1
- Alex Zhang's reference implementation: https://github.com/alexzhang13/rlm
- Original announcement thread: https://x.com/a1zhang/status/2007566581409144852?s=46

Thank you to Alex Zhang and collaborators for the Zeno concept and open resources that informed this work.
