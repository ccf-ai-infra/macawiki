# Macawiki iteration trend

12 cycles recorded: 12 accepted, 0 rejected, 0 abandoned, 0 in progress. 2 carry measurable metrics.

| Cycle | Status | pages | component_coverage | version_claims_specified | draft_ratio | unspecified_ratio | license_known_ratio | recall | tests |
|-------|--------|---|---|---|---|---|---|---|---|
| 1 | ✅ accepted | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| 2 | ✅ accepted | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| 3 | ✅ accepted | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| 4 | ✅ accepted | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| 5 | ✅ accepted | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| 6 | ✅ accepted | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| 7 | ✅ accepted | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| 8 | ✅ accepted | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| 9 | ✅ accepted | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| 10 | ✅ accepted | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| 11 | ✅ accepted | 28 | 18/21 | 4/6 | 50.0% | 28.6% | 58.3% | 1.000 | 72 |
| 12 | ✅ accepted | 28 | 18/21 | 4/6 | 50.0% | 28.6% | 58.3% | 1.000 | 82 |

Legend:
- `pages` — total corpus pages
- `component_coverage` — covered / known components in data/tags.yaml
- `version_claims_specified` — version-claims.yaml entries with a real version
- `draft_ratio` — share of wiki pages still in draft status
- `unspecified_ratio` — share of wiki pages with no MXMACA version
- `license_known_ratio` — share of sources with a determinable license
- `recall` — gold-question recall (recall_check.py)
- `tests` — unittest methods in tests/

## Cycles without metrics

These contribute no trend point. Each gap is a record-keeping
gap, not necessarily a bad outcome — but a loop that cannot
audit its own past will repeat it.

- **cycle 1**: report predates metric recording and has no embedded metrics block
- **cycle 2**: report predates metric recording and has no embedded metrics block
- **cycle 3**: report predates metric recording and has no embedded metrics block
- **cycle 4**: report predates metric recording and has no embedded metrics block
- **cycle 5**: report predates metric recording and has no embedded metrics block
- **cycle 6**: report predates metric recording and has no embedded metrics block
- **cycle 7**: no report path in state (cycles 7-10); decision is not traceable
- **cycle 8**: no report path in state (cycles 7-10); decision is not traceable
- **cycle 9**: no report path in state (cycles 7-10); decision is not traceable
- **cycle 10**: no report path in state (cycles 7-10); decision is not traceable

## Direction of travel

- `pages`: flat at 28
- `component_coverage`: flat at 18
- `version_claims_specified`: flat at 4
- `draft_ratio`: flat at 50.0%
- `unspecified_ratio`: flat at 28.6%
- `license_known_ratio`: flat at 58.3%
- `recall`: flat at 1.000
- `tests`: 72 → 82 (up 10.0)

Note: `up` is not always improvement. Draft ratio and unspecified
ratio are *better when lower*; the symbol only records direction.

## Most recent decision

**Cycle 12 (accepted)**

> Tooling cycle, not a corpus cycle: no tracked corpus metric moved (all 10 unchanged), which is expected because this adds instruments rather than evidence. Accepted on the traceability claim, verified concretely: (1) the falsifiability gate rejected its own operator's first draft of this hypothesis for naming no measurable metric, proving it enforces rather than advises; (2) a begin->reject run in the test suite leaves a report with metrics, closing the cycles-7-10 failure mode; (3) next_cycle_id advances at --begin, pre-empting the exact drift Phase 2 had to fix by hand. Genuinely no corpus gain, so this main line returns to corpus work next cycle; the <25% unspecified sub-target remains deliberately out of reach per AGENTS.md.

