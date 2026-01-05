[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Claude Code Compatible](https://img.shields.io/badge/Claude%20Code-Compatible-blue)](https://claude.ai/code)
[![Built with AI](https://img.shields.io/badge/Built%20with-AI%20%F0%9F%A4%96-blueviolet)](https://claude.ai/)  [![Built with AI](https://img.shields.io/badge/Built%20with-AI%20%F0%9F%A4%96-blueviolet)](https://claude.ai/)

# Zeno for Claude Code (Project Scope)

<p align="center"><img src="../assets/zeno.png" width="50%" alt="Zeno"></p>

## Table of Contents
- [Introduction](#introduction)
- [Why Zeno?](#why-zeno)
- [Folder layout](#folder-layout)
- [Quick start](#quick-start)
- [Verification](#verification)
- [Acknowledgments](#acknowledgments)


## Introduction
Zeno is a way to read huge codebases without stuffing them into the model's memory. It keeps the big files outside the model, pulls only the few lines needed, and keeps receipts so every claim can be traced back to evidence.
Technical: This repo stores the Claude Code layout in `claude/` for visibility. Claude Code itself expects `.claude/` at runtime, so copy `claude/` to `.claude/` before use.

For the full project overview, see `../README.md`.

## Why Zeno?
ELI5: Zeno is the philosopher who turned motion into a puzzle about cutting things in half forever. That is basically what we do with giant prompts: split, split, split, then stitch the answer back together.
Technical:
- Zeno of Elea is a philosophical patron for recursive decomposition: https://en.wikipedia.org/wiki/Zeno_of_Elea
- Zeno’s Dichotomy paradox divides a journey in half, then half again, and again, forever.
- Zeno’s name signals infinite splitting + recursion, which matches “unbounded context via recursive inspection.”
- RLMs treat a too-long prompt as an external environment and repeatedly decompose it into smaller subproblems until the final answer is assembled.

## Folder layout
```
claude/               # Repo-visible Claude Code layout (copy to .claude/)
  skills/zeno/        # Skill manual + scripts + references
  hooks/zeno.hooks.json
  settings.example.json
  zeno/               # Output artifacts (state/evidence/claims)
```

## Quick start
1) Copy the visible folder into the runtime location:
   - `rsync -a claude/ .claude/`
   - or from repo root: `./scripts/sync_claude.sh`
2) Merge `.claude/hooks/zeno.hooks.json` into `.claude/settings.json`.
3) Optionally merge `.claude/settings.example.json` for OTEL env settings.
4) Run `/hooks` in Claude Code to refresh hook registrations.

## Verification
- Run `claude --debug` and confirm hooks fire.
- Check `.claude/zeno/notify.log` after a turn.

## Acknowledgments
This skill is inspired by and references:
- Zhang et al., "Recursive Language Models" (arXiv:2512.24601v1): https://arxiv.org/abs/2512.24601v1
- Alex Zhang's reference implementation: https://github.com/alexzhang13/rlm
- Original announcement thread: https://x.com/a1zhang/status/2007566581409144852?s=46

Thank you to Alex Zhang and collaborators for the Zeno concept and open resources that informed this work.
