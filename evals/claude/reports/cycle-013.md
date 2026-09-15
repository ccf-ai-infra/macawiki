# Cycle 013: accepted change cluster

| Field | Value |
|-------|-------|
| Cycle ID | 13 |
| Status | accepted |
| Workstream | corpus |
| Date | 2026-09-15 |
| Hypothesis | Recording the proprietary EULA found at /opt/maca-3.7.1 raises source license_known_ratio to >=66.7%, and deleting the 'unspecified' bucket from data/tags.yaml corrects component coverage to 18 covered of 20 known (90.0%) from the currently reported 18 of 21: that tag is a placeholder for pages naming no specific component, and it is declared by zero pages in the corpus, so the true ceiling was always 20. Rejected if the EULA is absent, unreadable, or cannot be classified as proprietary, or if any page already declares component 'unspecified', which would make the deletion hide real coverage rather than fix a bad denominator. |

## Decision

**accepted**. Both targets met, and the denominator change is an honesty correction, not a cosmetic one. license_known_ratio 58.3% -> 66.7%: the install at /opt/maca-3.7.1 ships a proprietary End User License Agreement (EULA-en.txt, Version 1.0, September 13, 2025, plus EULA-zh.txt), so the local-capture source's license status is now determinable and recorded as 'restricted'. Only the presence, title, version and nature were recorded; the EULA text is neither copied nor summarized, and no rights are granted. The remaining 4 unknown-license sources are all gitee URLs unreachable in this environment, so 66.7% is this cycle's real ceiling. component coverage 18/21 -> 18/20: 'unspecified' was a placeholder bucket for pages naming no specific component, and it is declared by zero pages in the whole corpus, so the true ceiling was always 20. Deleting it raises real coverage from 85.7% to 90.0%; the raw 'component_total' count moves DOWN (21 -> 20) and must not be read as a regression -- the trend's direction-of-travel note already warns that a symbol only records direction, not improvement. Verified against the rejection path: the EULA exists and is classifiable (not absent), and no page declares the deleted tag, so the removal fixes a bad denominator instead of hiding real coverage. A third defect surfaced while opening this cycle and was fixed rather than worked around: the target parser latched 'coverage to 18' onto the bare phrase 'unspecified' (which names a tag, not the ratio), fabricating an unspecified_ratio target the hypothesis never stated and the cycle could not reach; the number must now follow its own metric. A test-isolation flaw of the same family was also fixed -- scratch state copied any in-progress real cycle, so 'make test' failed spuriously whenever a cycle was genuinely mid-flight. The page-level unspecified_ratio 28.6% still misses the <25% sub-target and is left there on purpose: those pages cite upstream non-MXMACA sources that carry no MXMACA version and AGENTS.md forbids inferring one.

## Metrics (before → after)

| Metric | Before | After | Δ |
|--------|--------|-------|---|
| pages | 28 | 28 | — |
| component_coverage | 18 | 18 | — |
| component_total | 21 | 20 | -1.0 |
| version_claims_specified | 4 | 4 | — |
| version_claims_total | 6 | 6 | — |
| draft_ratio | 50.0% | 50.0% | — |
| unspecified_ratio | 28.6% | 28.6% | — |
| license_known_ratio | 58.3% | 66.7% | +8.4pp |
| recall | 1.000 | 1.000 | — |
| tests | 85 | 85 | — |

## Candidate changes

- `data/source-registry.yaml`
- `data/tags.yaml`
- `evals/claude/iteration-state.json`
- `evals/claude/trend.md`
- `queries/index.pickle`
- `scripts/iterate_cycle.py`
- `sources/repos/local-c500-maca-sdk.md`
- `tests/test_repository.py`

## Reproduction

```bash
python3 scripts/iterate_metrics.py --json    # re-measure
make all
make check-advisory
```

<!-- iterate_metrics
```json
{
  "metrics_before": {
    "_quality_gates_error": null,
    "pages": 28,
    "draft_ratio": 0.5,
    "unspecified_ratio": 0.286,
    "license_known_ratio": 0.583,
    "_coverage_error": null,
    "component_coverage": 18,
    "component_total": 21,
    "version_claims_specified": 4,
    "version_claims_total": 6,
    "_recall_error": null,
    "recall": 1.0,
    "tests": 85
  },
  "metrics_after": {
    "_quality_gates_error": null,
    "pages": 28,
    "draft_ratio": 0.5,
    "unspecified_ratio": 0.286,
    "license_known_ratio": 0.667,
    "_coverage_error": null,
    "component_coverage": 18,
    "component_total": 20,
    "version_claims_specified": 4,
    "version_claims_total": 6,
    "_recall_error": null,
    "recall": 1.0,
    "tests": 85
  },
  "deltas": {
    "component_total": -1.0,
    "license_known_ratio": 8.4
  },
  "status": "accepted"
}
```
-->
