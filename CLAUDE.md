# Macawiki guidance for Claude Code

Macawiki is an evidence-first MXMACA knowledge base. Read `AGENTS.md` before editing corpus content and activate the `macawiki` skill for MXMACA questions.

- Search before answering: `python3 scripts/query.py "<terms>" --compact`.
- Trace claims: `python3 scripts/get_page.py <page-id> --follow-sources`.
- State hardware, MXMACA/framework version, confidence, and missing evidence.
- Never invent C500, TileLang, or MXMACA++ benchmark results.
- Run `make all` before proposing repository changes.
