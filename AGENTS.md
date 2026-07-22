# Macawiki repository instructions

Macawiki is an evidence-first MXMACA knowledge base for humans and AI agents.

## Safety and scope

- Use only public sources unless a maintainer explicitly approves another source class.
- Do not copy access-controlled, confidential, login-only, or license-unclear documents into the repository.
- Prefer metadata, summaries, and links over verbatim reproduction.
- Do not treat CUDA or NVIDIA behavior as MXMACA fact without MXMACA-specific evidence.
- Do not publish, comment, open issues, or create pull requests in upstream projects without explicit user authorization.

## Corpus rules

- `sources/` contains single-source records. Keep statements faithful to that source.
- `wiki/` contains multi-source synthesis. Every material claim must trace to `sources` IDs.
- Use JSON-compatible YAML in frontmatter and `data/*.yaml`; this keeps v0.1 dependency-free.
- Do not hand-edit `queries/`; regenerate it with `python3 scripts/generate_indices.py`.
- Add aliases and vocabulary through reviewed changes to `data/aliases.yaml` and `data/tags.yaml`.
- Never assign `verified` automatically. A maintainer must approve it.
- Bind code facts to a commit SHA and version-sensitive facts to explicit versions.
- Mark unknown version or hardware scope as `unspecified`; do not infer it.
- Defer license-unclear artifacts instead of importing them.

## Required checks

Run these from the repository root:

```bash
python3 scripts/validate.py
python3 scripts/generate_indices.py --check
python3 -m unittest discover -s tests -v
python3 scripts/repo_status.py
```

## Review expectations

Keep batches small. For corpus additions, report sources, version scope, confidence, generated versus handwritten files, validation results, and unresolved questions.
