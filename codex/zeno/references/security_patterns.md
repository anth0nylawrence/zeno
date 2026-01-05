# Zeno Security Pattern Packs

Zeno security-audit mode uses a lightweight pattern pack to triage common risky constructs. This is not a full static analysis engine; it is a fast, evidence-first pre-audit.

## How it is used
- The pack is consumed by `scripts/zeno_modes.py` when `--mode security-audit` is used.
- Each pattern becomes a `grep` retrieval op with a severity and category.
- The audit report must treat results as hypotheses until confirmed with file context.

## Pack location
- JSON pack: `references/security_patterns.json`

## Fields
Each pattern has:
- `id`: stable identifier
- `category`: code-exec, command-injection, deserialization, auth, sql-injection, secrets
- `severity`: high, medium, low
- `pattern`: grep pattern (literal unless `regex: true`)
- `languages`: logical language tags
- `globs`: file globs to search
- `description`: short rationale
- `example`: minimal example

## Extending the pack
Add new patterns to `security_patterns.json`. Keep patterns narrow to reduce false positives, and default to literal matching unless regex is required.

## Caveats
- Pattern matches are not vulnerabilities by default.
- Always read surrounding context and build evidence chains.
- If a pattern is too noisy, tighten the glob or the pattern.

## Acknowledgments
This skill is inspired by and references:
- Zhang et al., "Recursive Language Models" (arXiv:2512.24601v1): https://arxiv.org/abs/2512.24601v1
- Alex Zhang's reference implementation: https://github.com/alexzhang13/rlm
- Original announcement thread: https://x.com/a1zhang/status/2007566581409144852?s=46

Thank you to Alex Zhang and collaborators for the Zeno concept and open resources that informed this work.
