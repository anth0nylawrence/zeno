# Zeno Indexing (Symbol + Dependency Map)

Zeno provides an optional lightweight indexer that scans a repo to extract:
- Symbol definitions (class, function, struct, etc.)
- Import/dependency lines (language-aware heuristics)

This index is intended to speed up codebase archaeology, architecture mapping, and PR review impact analysis.

## Script
- `scripts/zeno_index.py`

## Example
```bash
python3 scripts/zeno_index.py --root /path/to/repo --out /tmp/zeno_index.json
```

## Output
The JSON output includes:
- `symbols[]`: symbol name, kind, path, line, language
- `imports[]`: module, path, line, language, raw line
- `stats`: counts and bytes read

## Notes
- This is heuristic; it does not replace a full parser.
- You can cap file size, symbol count, and import count.
- Respect excludes to avoid generated or vendor files.

## Acknowledgments
This skill is inspired by and references:
- Zhang et al., "Recursive Language Models" (arXiv:2512.24601v1): https://arxiv.org/abs/2512.24601v1
- Alex Zhang's reference implementation: https://github.com/alexzhang13/rlm
- Original announcement thread: https://x.com/a1zhang/status/2007566581409144852?s=46

Thank you to Alex Zhang and collaborators for the Zeno concept and open resources that informed this work.
