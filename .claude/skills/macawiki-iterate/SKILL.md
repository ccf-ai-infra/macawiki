---
name: macawiki-iterate
description: Continuously improve and evaluate Macawiki's measurable value for Claude: maintain knowledge and benchmark integrity, run loaded-vs-unloaded evaluations with token accounting, expand held-out MXMACA ecosystem tasks, optimize the skill and corpus from failures, and repeat until evidence shows no worthwhile safe improvement remains or an external blocker is reached. Use only when a maintainer explicitly requests Macawiki iteration or value optimization.
argument-hint: "[status|next|run|foundation|eval|ecosystem|report]"
disable-model-invocation: true
---

# Macawiki iteration control

You are in the Macawiki repository executing a **resumable, evidence-first, unbounded value optimization loop**. Do not treat "reach N cycles" as a goal; every iteration must target a falsifiable hypothesis, modify a small batch, and decide from real regression or A/B results.

Parameters (`/macawiki-iterate <param>`):

- `status`: read state, champion, backlog, and blockers — no file changes.
- `next`: execute one highest-priority full cycle. Default when no param given.
- `run`: continue cycles until external blocker, budget stop, or "no worthwhile safe improvement remains."
- `foundation`: prioritize fact/baseline/schema/test/repro fixes.
- `eval`: prioritize Claude loaded-vs-unloaded eval and cost analysis.
- `ecosystem`: prioritize MXMACA upstream/downstream held-out engineering tasks.
- `report`: recompute existing results and update decision report without changing skill or corpus.

## Per-cycle algorithm

1. Read `AGENTS.md`, `CLAUDE.md`, root `SKILL.md`, `docs/source-and-license-policy.md`
2. Run `make all` as pre-check baseline
3. Read `evals/claude/iteration-state.json` — pick highest priority backlog item
4. Form a single falsifiable hypothesis
5. Prepare PR branch: `bash scripts/prepare_pr.sh <type> "<description>"` (if committing changes)
6. Execute minimal related changes (one cluster)
7. Run `make all` + `make check-advisory` + any targeted tests
8. Accept (metrics improved, no regression) or reject (no gain, instability, negative transfer)
9. Write cycle report to `evals/claude/reports/cycle-NNN.md`
10. Update `evals/claude/iteration-state.json`
11. For `next`: stop here. For `run`: continue to next cycle.

## Key constraints

- Do NOT modify `benchmarks/results/*.json` unless actually re-running on C500
- Do NOT hand-edit `queries/` — use `python3 scripts/generate_indices.py`
- Do NOT use CUDA/NVIDIA behavior as MXMACA fact
- Do NOT push, PR, comment upstream, or publish without explicit authorization
- Do NOT `git reset --hard` or `git checkout --` to revert
- Keep each cycle small: one hypothesis, one change cluster, clear acceptance
- Real Claude API calls only with `MACAWIKI_RUN_PAID_EVAL=1` or explicit user auth
