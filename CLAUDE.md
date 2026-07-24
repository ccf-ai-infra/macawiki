# Macawiki guidance for Claude Code

Macawiki is an evidence-first MXMACA knowledge base designed for local AI agent consumption (Claude Code, Codex, OpenCode). Read `AGENTS.md` before editing corpus content and activate the `macawiki` skill for MXMACA questions.

## Guiding principles

- **Local agent first**: Macawiki targets local AI agent workflows (Claude Code `/macawiki`, Codex `$macawiki`, OpenCode skill). Do not add server/API/Docker deployment layers — keep the toolchain CLI-native and file-based. Agents interact via CLI subprocess (`python3 scripts/query.py`, etc.), not HTTP endpoints.
- **Zero external dependencies**: All query, validation, and indexing tools use Python stdlib only. Do not introduce pip dependencies without explicit maintainer approval and a documented fallback path.
- **Evidence-first, version-scoped**: Every claim must state hardware, MXMACA/framework version, confidence, and source traceability.

## Workflow

- Search before answering: `python3 scripts/query.py "<terms>" --compact`.
- Trace claims: `python3 scripts/get_page.py <page-id> --follow-sources`.
- State hardware, MXMACA/framework version, confidence, and missing evidence.
- Never invent C500, TileLang, or MXMACA++ benchmark results.
- Run `make all` before proposing repository changes.
- **GitLink PR 目标**: 提 PR 时目标仓库始终是 `ccf-ai-infra/macawiki`（origin 上游），不要推到 `topshare/macawiki`（个人 fork）。Git remote 中 `origin` = `ccf-ai-infra/macawiki`，`topshare` = 个人 fork。
