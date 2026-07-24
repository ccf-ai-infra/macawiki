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
   # Precise multi-term search (all terms must match -- default AND mode):
   python3 scripts/query.py "性能分析" --compact --signal-log
   python3 scripts/query.py --component mcprofiler --type wiki-pattern --signal-log
   python3 scripts/query.py --hardware c500 --version unspecified --signal-log

   # Broad multi-concept search (any term may match -- OR mode, better recall):
   python3 scripts/query.py "性能 基线 算子" --mode or --compact --signal-log
   ```

   Prefer `--mode or` for broad topic exploration or when a multi-word AND query returns zero results.

   # Fuzzy search with n-gram similarity (when exact search fails):
   python3 scripts/query.py "kernel" "tuning" "roofline" --fuzzy --compact --signal-log
   python3 scripts/query.py "算子" "优化" "内存" --auto-fuzzy --compact --signal-log

   Use `--fuzzy` for approximate matching or `--auto-fuzzy` to automatically
   fall back when exact AND/OR returns zero results.

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
- Keep TileLang results that have not passed correctness + timing gates as `not_comparable`.
- Keep MXMACA++ results as `not_run` until the MXMACA++ backend is connected to a captured C500 environment.
- Use standardized status terms defined in `docs/hardware-validation.md`: `verified`, `recorded`, `implemented`, `not_run`, `not_comparable`.
- Say that the corpus has no reliable conclusion when evidence is absent.
- Never assume CUDA behavior is identical on MXMACA.

## Performance optimization (C500/MXMACA only)

When running on a MetaX C500 with MXMACA, capture environment data and track query efficiency:

```bash
# Check if this is a C500/MXMACA environment
python3 scripts/env_detector.py

# Run queries with token tracking
python3 scripts/query.py "performance baseline" --mode or --signal-log --token-estimate

# Probe the environment before running benchmarks
python3 scripts/env_detector.py --snapshot

# Analyze collected signals
make signals          # aggregate incoming query signals
make token-report     # identify expensive query patterns
make env-probe        # capture hardware/software fingerprint
make evolve           # full self-evolution cycle (env + signals + auto-fix preview)
```

Performance signals and token tracking are captured automatically when
``--signal-log`` is used.  On non-MXMACA systems a host-based fingerprint
is used in place of the C500 hardware fingerprint, so records from
different machines are never merged.

## Maintenance

Run all checks before proposing corpus changes:

```bash
python3 scripts/validate.py
python3 scripts/generate_indices.py --check
python3 -m unittest discover -s tests -v
```

Keep detailed schemas in `references/schema.md` and usage patterns in `references/examples.md`; load them only when needed.
