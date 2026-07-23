# Cycle 001: Fix accum bug + strengthen compare_benchmarks

| Field | Value |
|-------|-------|
| Cycle ID | 1 |
| Status | accepted |
| Date | 2026-07-22 |
| Hypothesis | Fixing tl_quantize undefined `accum` and strengthening compare_benchmarks.py with schema/case/timing validation, missing case detection, and not_comparable reporting will eliminate known static defects and prevent future silent comparison errors. |
| Workstream | foundation |

## Changes

### Fix: `benchmarks/tilelang_candidate.py:178`

Added `accum = T.float32` (same pattern as `tl_layer_norm` at line 108) before the quantize kernel body. Two `T.Cast(accum, ...)` calls at lines 178-179 previously referenced an undefined name.

### Rewrite: `scripts/compare_benchmarks.py`

Enhanced from 47-line minimal comparator to a multi-gate validator:

1. **Top-level schema**: validates `status`, `environment`, `cases` are present; `cases` is a list
2. **Environment validation**: checks `environment_fingerprint` exists in both
3. **Per-case schema**: validates `case_id`, `operator`, `correctness`, `timing` and their sub-fields
4. **Timing contract**: `median_ms` must be positive numeric
5. **Missing case detection**: reports `baseline_only` and `candidate_only` lists
6. **Operator contract**: checks `operator`, `shape`, `dtype`, `warmup`, `iterations` match between baseline and candidate for same case_id
7. **Correctness gate**: both must pass
8. **Speedup**: only computed when all gates pass

### New tests: `tests/test_repository.py`

12 new tests covering:
- Missing status/environment/cases rejection
- Non-list cases rejection
- Missing case_id field detection
- Negative and zero median_ms rejection
- Case mismatch detection (baseline_only / candidate_only)
- Contract mismatch detection (shape, operator)
- Valid input acceptance (comparable + speedup)
- Correctness failure handling (not_comparable)
- `tilelang_candidate.py --list` runs without import error

## Before/After

| Metric | Before | After |
|--------|--------|-------|
| Unit tests | 9 | 21 |
| compare_benchmarks lines | 47 | 188 |
| tl_quantize accum defined | No (undefined name) | Yes (`T.float32`) |
| Schema validation | None | Top-level + per-case |
| Timing validation | None | Positive median required |
| Missing case detection | Silent ignore | Explicit report |
| Contract mismatch detection | None | Operator/shape/dtype/warmup/iterations |

## Verification

```bash
make all  # 21 tests pass, validate, indices, agent-value-eval, doctor, repo-status all pass
git diff --check  # clean
```

## Decision

**Accepted.** Fixes a hard static defect (`accum` undefined) and prevents silent comparison failures. No regression on existing tests or functionality.
