# Macawiki iteration trend

11 cycles recorded: 11 accepted, 0 rejected, 0 abandoned, 0 in progress. 0 carry measurable metrics.

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
| 11 | ✅ accepted | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

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
- **cycle 11**: report predates metric recording and has no embedded metrics block

## Most recent decision

**Cycle 11 (accepted)**

> Hypothesis confirmed, not falsified: versions were read from header macros without loading any library or running a kernel. Component coverage 12/21 -> 18/21 (target >=15/21). version-claims specified 0/6 -> 4/6 (target >=3/6). Pages 21 -> 28. Recall 100% held. 72 tests pass (count unchanged; one existing URL-plausibility assertion was strengthened rather than added). mcCL is the only corroborated component (header macro + mcclras self-report agree on 2.16.5); all others single-signal. Page-level unspecified ratio 28.6% missed the <25% sub-target deliberately: the remaining unspecified pages cite upstream non-MXMACA sources that carry no MXMACA version and AGENTS.md forbids inferring one. License-known ratio fell 63.6% -> 58.3% because the new local-capture source has license_status unknown, surfacing rather than hiding that gap. Negative evidence recorded: ctypes mcblasGetVersion segfaulted (needs an initialized handle); mcTracer --version silently reports no version at all (the version is in --help; capture script fixed and re-run); mxvs and mcProfiler version probes both failed. Two real defects surfaced via make all and were fixed with tests: the URL-plausibility test now audits local:// sources (access must be local-capture and fixed_ref must name a committed artifact) instead of blanket-rejecting them; iterate_precheck champion-stale was demoted from error to warn because HEAD legitimately outruns the recorded champion between cycles, while foreign SHA and cycle-id collision stay critical.

