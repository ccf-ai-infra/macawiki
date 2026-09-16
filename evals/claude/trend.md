# Macawiki iteration trend

14 cycles recorded: 13 accepted, 0 rejected, 0 abandoned, 1 in progress. 3 carry measurable metrics.

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
| 13 | ✅ accepted | 28 | 18/20 | 4/6 | 50.0% | 28.6% | 66.7% | 1.000 | 85 |
| 14 | ⏳ in_progress | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

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
- **cycle 14**: no report path in state (cycles 7-10); decision is not traceable

## Direction of travel

- `pages`: flat at 28
- `component_coverage`: flat at 18
- `version_claims_specified`: flat at 4
- `draft_ratio`: flat at 50.0%
- `unspecified_ratio`: flat at 28.6%
- `license_known_ratio`: 58.3% → 66.7% (up 8.4pp)
- `recall`: flat at 1.000
- `tests`: 72 → 85 (up 13.0)

Note: `up` is not always improvement. Draft ratio and unspecified
ratio are *better when lower*; the symbol only records direction.

## Most recent decision

**Cycle 13 (accepted)**

> Both targets met, and the denominator change is an honesty correction, not a cosmetic one. license_known_ratio 58.3% -> 66.7%: the install at /opt/maca-3.7.1 ships a proprietary End User License Agreement (EULA-en.txt, Version 1.0, September 13, 2025, plus EULA-zh.txt), so the local-capture source's license status is now determinable and recorded as 'restricted'. Only the presence, title, version and nature were recorded; the EULA text is neither copied nor summarized, and no rights are granted. The remaining 4 unknown-license sources are all gitee URLs unreachable in this environment, so 66.7% is this cycle's real ceiling. component coverage 18/21 -> 18/20: 'unspecified' was a placeholder bucket for pages naming no specific component, and it is declared by zero pages in the whole corpus, so the true ceiling was always 20. Deleting it raises real coverage from 85.7% to 90.0%; the raw 'component_total' count moves DOWN (21 -> 20) and must not be read as a regression -- the trend's direction-of-travel note already warns that a symbol only records direction, not improvement. Verified against the rejection path: the EULA exists and is classifiable (not absent), and no page declares the deleted tag, so the removal fixes a bad denominator instead of hiding real coverage. A third defect surfaced while opening this cycle and was fixed rather than worked around: the target parser latched 'coverage to 18' onto the bare phrase 'unspecified' (which names a tag, not the ratio), fabricating an unspecified_ratio target the hypothesis never stated and the cycle could not reach; the number must now follow its own metric. A test-isolation flaw of the same family was also fixed -- scratch state copied any in-progress real cycle, so 'make test' failed spuriously whenever a cycle was genuinely mid-flight. The page-level unspecified_ratio 28.6% still misses the <25% sub-target and is left there on purpose: those pages cite upstream non-MXMACA sources that carry no MXMACA version and AGENTS.md forbids inferring one.

