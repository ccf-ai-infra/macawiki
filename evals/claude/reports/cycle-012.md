# Cycle 012: accepted change cluster

| Field | Value |
|-------|-------|
| Cycle ID | 12 |
| Status | accepted |
| Workstream | foundation |
| Date | 2026-09-14 |
| Hypothesis | Wrapping the 13-step loop in iterate_cycle.py makes cycle decisions traceable: every cycle would record a falsifiable hypothesis, measured before/after metrics, and a report even when rejected. Falsification path: if the tooling adds no real enforcement beyond what the agent already does by hand, it is not worth the maintenance surface and the cycle should be rejected. |

## Decision

**accepted**. Tooling cycle, not a corpus cycle: no tracked corpus metric moved (all 10 unchanged), which is expected because this adds instruments rather than evidence. Accepted on the traceability claim, verified concretely: (1) the falsifiability gate rejected its own operator's first draft of this hypothesis for naming no measurable metric, proving it enforces rather than advises; (2) a begin->reject run in the test suite leaves a report with metrics, closing the cycles-7-10 failure mode; (3) next_cycle_id advances at --begin, pre-empting the exact drift Phase 2 had to fix by hand. Genuinely no corpus gain, so this main line returns to corpus work next cycle; the <25% unspecified sub-target remains deliberately out of reach per AGENTS.md.

## Metrics (before → after)

| Metric | Before | After | Δ |
|--------|--------|-------|---|
| pages | 28 | 28 | — |
| component_coverage | 18 | 18 | — |
| component_total | 21 | 21 | — |
| version_claims_specified | 4 | 4 | — |
| version_claims_total | 6 | 6 | — |
| draft_ratio | 50.0% | 50.0% | — |
| unspecified_ratio | 28.6% | 28.6% | — |
| license_known_ratio | 58.3% | 58.3% | — |
| recall | 1.000 | 1.000 | — |
| tests | 82 | 82 | — |

*No tracked metric changed between baseline and finish.*

## Candidate changes

- `evals/claude/iteration-state.json`

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
    "tests": 82
  },
  "metrics_after": {
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
    "tests": 82
  },
  "deltas": {},
  "status": "accepted"
}
```
-->
