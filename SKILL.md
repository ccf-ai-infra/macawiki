---
name: macawiki
description: Query and trace version-scoped MXMACA knowledge for installation, programming, profiling, diagnostics, framework adaptation, kernel optimization, operator evaluation, migration, and MetaX-MACA community repositories. Use when an Agent needs evidence-backed MXMACA answers, reproducible PyTorch/TileLang/MXMACA++ comparison plans, or relevant Macawiki pages and sources. Do not use for generic GPU questions with no MXMACA connection or non-public MetaX material.
---

# Macawiki

Use the repository-local knowledge base to answer MXMACA questions with explicit evidence and version scope.

## Query workflow

1. For broad questions, read `references/primer.md`.
2. Search the corpus:

   ```bash
   python3 scripts/query.py "性能分析" --compact
   python3 scripts/query.py --component mcprofiler --type wiki-pattern
   python3 scripts/query.py --hardware c500 --version unspecified
   ```

3. Read an exact page and its evidence:

   ```bash
   python3 scripts/get_page.py pattern-establish-performance-baseline --follow-sources
   ```

4. For symbols or error text, run:

   ```bash
   python3 scripts/grep_wiki.py "mcProfiler|roofline"
   ```

5. Before changing corpus content, read `AGENTS.md` and `references/schema.md`.

For operator comparison work, read `benchmarks/README.md` and
`docs/hardware-validation.md` before selecting a backend or reporting results.

## Answer contract

- Cite page IDs and repository paths.
- Cite source IDs or public URLs for factual claims.
- State hardware and MXMACA/framework version scope.
- Distinguish `verified`, `source-reported`, `corroborated`, `inferred`, and `experimental` claims.
- Treat performance figures without complete benchmark metadata as non-comparable.
- Label CPU-only PyTorch runs as workflow checks, never as C500 performance evidence.
- Keep TileLang and MXMACA++ results `not_run` until their implementations execute in the same captured C500 environment.
- Say that the corpus has no reliable conclusion when evidence is absent.
- Never assume CUDA behavior is identical on MXMACA.

## Maintenance

Run all checks before proposing corpus changes:

```bash
python3 scripts/validate.py
python3 scripts/generate_indices.py --check
python3 -m unittest discover -s tests -v
```

Keep detailed schemas in `references/schema.md` and usage patterns in `references/examples.md`; load them only when needed.
