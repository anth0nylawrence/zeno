# Zeno JSONL Protocol (REPL Server)

This document defines the JSONL request/response protocol used by `scripts/zeno_server.py` and the logging schema for replay.

## Plain-English summary
One JSON object per line in, one JSON object per line out. Each request includes `id`, `op`, and `args`. Each response echoes `id` and returns either `ok: true` with a `result`, or `ok: false` with an `error`.

## Request envelope

```json
{"id":"req-1","op":"list_files","args":{"glob":"**/*.swift","max":200}}
```

Fields:
- `id` (string): client-generated request id.
- `op` (string): operation name.
- `args` (object): op-specific arguments.

Constraints:
- All paths must resolve under `--root`.
- If both `glob` and `regex` are present, `glob` takes precedence.

## Response envelope

```json
{"id":"req-1","ok":true,"result":{"files":["Blaze/Sources/App/AppCoordinator.swift"],"truncated":false,"metrics":{"time_ms":4,"bytes_read":0,"files_scanned":128}}}
```

If an error occurs:

```json
{"id":"req-1","ok":false,"error":{"message":"unknown op: foo"}}
```

Error schema:
- `id` (string|null)
- `ok` (false)
- `error.message` (string)

## Metrics schema (returned in result.metrics)
Every op returns a `metrics` object with:
- `time_ms` (int): elapsed time in milliseconds.
- `bytes_read` (int): total characters read from files (approx bytes).
- `files_scanned` (int): number of files scanned or inspected.
Optional fields may appear depending on op:
- `hits` (int): grep hits.
- `symbols` (int): symbols found.
- `lines_returned` (int): read_file lines returned.

## Operations

### list_files
List files under `--root` using a glob or regex.

Args:
- `glob` (string, optional): fnmatch-style glob (e.g., `**/*.swift`).
- `regex` (string, optional): regex to match relative paths.
- `max` (int, optional, default 500): max results returned.
- `max_files` (int, optional, default 20000): max files to scan.
- `include_hidden` (bool, optional, default false): include dotfiles.
- `exclude_dirs` (list, optional): directory names to skip.
- `exclude_globs` (list, optional): globs to skip.

Result:
- `files` (list): sorted relative paths.
- `truncated` (bool): true if `max` clipped results.
- `metrics` (object): time_ms, bytes_read, files_scanned.

### read_file
Read a slice of a file by line range.

Args:
- `path` (string, required): path relative to root (or absolute within root).
- `start_line` (int, optional, default 1): 1-based start.
- `end_line` (int, optional, default start_line): 1-based end.
- `max_lines` (int, optional, default 400): cap lines returned.

Result:
- `path`
- `start_line`
- `end_line`
- `total_lines`
- `truncated` (bool): true when request exceeds max_lines.
- `text` (string): joined lines.
- `metrics` (object): time_ms, bytes_read, files_scanned, lines_returned.

### peek
Read head/tail slices of a file.

Args:
- `path` (string, required)
- `head_lines` (int, optional, default 60)
- `tail_lines` (int, optional, default 60)

Result:
- `path`
- `total_lines`
- `head`: {`start_line`,`end_line`,`text`}
- `tail`: {`start_line`,`end_line`,`text`}
- `metrics` (object): time_ms, bytes_read, files_scanned.

### grep
Search across files. Default is literal substring match. Use `regex=true` to enable regex.

Args:
- `pattern` (string, required): literal pattern or regex.
- `regex` (bool, optional, default false): enable regex mode.
- `case_sensitive` (bool, optional, default true): case sensitivity.
- `paths` (list, optional): list of path globs to constrain search.
- `max_hits` (int, optional, default 200): cap hits.
- `max_files` (int, optional, default 20000): max files to scan.
- `max_bytes` (int, optional, default 2000000): skip files larger than this.
- `context` (int, optional, default 0): lines of context before/after.
- `include_hidden` (bool, optional, default false)
- `exclude_dirs` (list, optional)
- `exclude_globs` (list, optional)

Result:
- `hits`: list of `{path,line,text}` objects, optionally `context`.
- `truncated` (bool): true if hit cap reached.
- `metrics` (object): time_ms, bytes_read, files_scanned, hits.

### extract_symbols
Heuristic symbol extraction with regex patterns.

Args:
- `path` (string, required)
- `max_symbols` (int, optional, default 400)

Result:
- `path`
- `symbols`: list of `{kind,name,line}`
- `truncated` (bool)
- `metrics` (object): time_ms, bytes_read, files_scanned, symbols.

### stat
Return file metadata for one or more paths.

Args:
- `path` (string, optional): single path.
- `paths` (list, optional): list of paths.

Result:
- `items`: list of
  - `path`
  - `exists` (bool)
  - `size` (int, bytes)
  - `mtime` (float, epoch seconds)
  - `mtime_iso` (string, UTC)
  - `is_file` (bool)
  - `is_dir` (bool)
  - `error` (string, only when exists is false)
- `metrics` (object): time_ms, bytes_read, files_scanned.

## Limits and defaults
- max_lines default: 400
- max_hits default: 200
- max_files default: 20000
- max_bytes default: 2000000

## Path safety
All paths are resolved relative to `--root`. Paths outside the root are rejected.

## Determinism rules
- Always sort paths and hits.
- Cap outputs with max/max_hits/max_lines and set truncated.
- Never read outside --root.

## Recommended trajectory logging (JSONL)
Enable logging with `--log /path/to/zeno_trace.jsonl`. Each event is one JSON object.

Example events:

```json
{"ts":"2026-01-04T18:11:30Z","event":"request","id":"req-1","op":"list_files","args":{"glob":"**/*.swift","max":200}}
{"ts":"2026-01-04T18:11:30Z","event":"response","id":"req-1","op":"list_files","summary":{"count":143,"truncated":false,"metrics":{"time_ms":4,"bytes_read":0,"files_scanned":128}}}
{"ts":"2026-01-04T18:11:41Z","event":"request","id":"req-2","op":"read_file","args":{"path":"Blaze/Sources/App/AppCoordinator.swift","start_line":1,"end_line":220}}
{"ts":"2026-01-04T18:11:41Z","event":"response","id":"req-2","op":"read_file","summary":{"count":null,"truncated":false,"metrics":{"time_ms":6,"bytes_read":9840,"files_scanned":1,"lines_returned":220}}}
```

Optional extended events (produced by the agent, not the server):
- `subcall_start`, `subcall_end`
- `claim` with `evidence` paths and ranges

These enable replay and visualization of retrieval trajectories.

## Acknowledgments
This skill is inspired by and references:
- Zhang et al., "Recursive Language Models" (arXiv:2512.24601v1): https://arxiv.org/abs/2512.24601v1
- Alex Zhang's reference implementation: https://github.com/alexzhang13/rlm
- Original announcement thread: https://x.com/a1zhang/status/2007566581409144852?s=46

Thank you to Alex Zhang and collaborators for the Zeno concept and open resources that informed this work.
