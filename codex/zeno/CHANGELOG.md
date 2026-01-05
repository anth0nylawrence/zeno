# Changelog

## 0.1.1
- Added notify checkpoint log (`.codex/zeno/notify.log`) for CLI tailing
- Added `zeno_context_bridge.py` for prompt-ready context carryover
- Documented checkpoint signal and context bridge usage

## 0.1.0
- Initial production-grade Zeno skill layout
- Pattern A notify persistence (state/evidence/claims)
- Pattern B OTEL guidance and collector config
- JSONL REPL server with safe grep, streaming reads, stat op, metrics
- Client CLI, log linting, evidence verification, log rotation
- Example fixtures and tests

## Acknowledgments
This skill is inspired by and references:
- Zhang et al., "Recursive Language Models" (arXiv:2512.24601v1): https://arxiv.org/abs/2512.24601v1
- Alex Zhang's reference implementation: https://github.com/alexzhang13/rlm
- Original announcement thread: https://x.com/a1zhang/status/2007566581409144852?s=46

Thank you to Alex Zhang and collaborators for the Zeno concept and open resources that informed this work.