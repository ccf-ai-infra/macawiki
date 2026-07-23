# Macawiki v0.3 charter

## Purpose

Build an auditable, evidence-first MXMACA knowledge base that helps humans and AI agents retrieve version-scoped facts, reproduce operator evaluations, and refuse unsupported conclusions.

## Approved v0.3 scope

- Repository structure and governance rules (AGENTS.md, SKILL.md, CLAUDE.md).
- Dependency-free schema, validation, query, page-read, grep, index, install, doctor, and status tools.
- A curated set of public source records and synthesis wiki pages with explicit version scope.
- Operator evaluation scaffolding: PyTorch baseline, TileLang candidate, MXMACA++ contract, compare tool, and C500 result provenance.
- Claude Code and Codex skill adapters (in-repo, user-level, project-level).
- Agent value proxy evaluation (deterministic retrieval, negative-trigger, forbidden-claim guards).
- No bulk ingestion, unsanctioned benchmarking, or upstream automation without maintainer approval.

## Current state (v0.3)

- 14 pages (8 sources, 6 wiki) with validated schemas and generated indices.
- 38 automated tests covering schema, contracts, evidence integrity, and transpose workloads.
- 9 agent-value cases (7 positive + 2 negative) with deterministic retrieval proxy.
- C500 benchmarks: 7 case slots with status records (5 comparable, 2 not_comparable), MXMACA++ not_run.
- Iteration infrastructure: state file, cycle reports, macawiki-iterate skill.

## Proposed next review

Maintainers should review MXMACA++ SDK availability, Claude API paid authorization status, source freshness, and Tier 1 ecosystem project scope before expanding beyond v0.3.
