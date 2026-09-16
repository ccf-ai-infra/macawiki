# Cycle 014: accepted change cluster

| Field | Value |
|-------|-------|
| Cycle ID | 14 |
| Status | accepted |
| Workstream | corpus |
| Date | 2026-09-16 |
| Hypothesis | Adding a measured ecosystem-port-status page recording that flashinfer is a metax build of 0.2.6 (not the upstream 0.6.x API line), that sgl_kernel has no metax build and its PyPI wheel is sm90/sm100 plus CUDA 13 only, and that mcPyTorch exposes the C500 through the torch.cuda namespace as sm_80, raises component coverage from 18 to 19 of 20 and makes three previously zero-result queries (sglang, flashinfer, omni) resolve to a page. Rejected if any recorded version fails to reproduce on this machine, or if any of those queries still returns zero after index regeneration, since a page that cannot be found provides no value to an agent. |

## Decision

**accepted**. ACCEPTED. All three falsifiable parts of the hypothesis reproduced on this machine.

Coverage: component_coverage 18/20 -> 19/20. The page declares mcpytorch, mctriton, mctilelang, flash-attn, sglang, mxmaca-sdk and mxmaca-runtime; sglang was the only one of those with zero pages before, so coverage moved by exactly one bucket and not by padding. Recall stays 1.000 and tests went 84 -> 85.

Retrieval: three query terms that returned zero results before this cycle now each resolve to exactly one page -- 'sglang' 1, 'flashinfer' 1, 'omni' 1 -- plus the Chinese alias '生态移植' 1. This is the part that matters: the failure this cycle was built to fix was not a missing metric, it was an agent asking about sglang-omni and getting nothing. The zero-result query is the failure mode that a coverage ratio cannot see.

Version fidelity: every version the page states was re-measured live before finishing, not carried from notes -- torch 2.8.0+metax3.7.1.3, torch.version.cuda 11.6, capability (8,0), arch list ['sm_80'], flashinfer 0.2.6+metax3.7.1.3torch2.8, triton 3.0.0, flash_attn 2.6.3, platform CudaSRTPlatform with is_cuda() True. All matched the page as written.

Two things are recorded against the change rather than for it.

1. draft_ratio moved 50.0% -> 51.7%, a real regression. The new page is status: draft because the end-to-end claim is not verified -- sglang-omni's pipeline launches but model serving is blocked by the qwen-tts/transformers pin conflict (qwen-tts pins transformers 4.57.3, sglang pins 5.12.1, the box has 5.8.0). That conflict is dependency resolution, not MXMACA compatibility, and it was deliberately NOT shimmed: patching @check_model_inputs() would falsify real model input validation and make any inference result untrustworthy. So the page ships as draft with the gap stated in its evidence-boundaries section, and the ratio is the honest price of saying 'this is what we measured, not what we achieved'. Promoting it to reviewed requires a separate venv or an upstream qwen-tts release for transformers 5.x, plus an actual serve run.

2. The before-snapshot is stale. The page, the aliases and the index were already written when --begin ran, so metrics_before reports pages 29 and component_coverage 19 -- the post-change state. The true before-state was measured at the start of this session, before any file was touched: 28 pages, component_coverage 18/20, and zero results for sglang/flashinfer/omni. The 18 -> 19 and 28 -> 29 deltas above are from that session-start measurement, not from the state file. The trend tool will read the recorded numbers, so this delta must not be consumed as a validated before/after pair.

The non-obvious finding, and the reason this page exists at all: an agent reading sglang-omni's README would conclude it has no MXMACA backend and stop. That conclusion was wrong here -- it was my own conclusion earlier in this session and empirical testing overturned it. MXMACA exposes the C500 through the torch.cuda namespace, so sglang's platform layer resolves it as CudaSRTPlatform and is_cuda() is True. The page records two concrete consequences that an adapter will hit: `if is_cuda():` guards run unconditionally so SGLANG_IS_FLASHINFER_AVAILABLE=false does not skip the flashinfer fp8/fp4 imports, and metax flashinfer's ~23s first import exceeds check-gpu's 30s timeout and gets reported as unavailable when it is merely slow. Those two are configuration-shaped problems and are the actionable part of the page; the sgl_kernel gap is not -- it needs an sm80/CUDA-11.6 metax build, which is compilation work.

Evidence boundaries kept: the page claims only what is installed, what version, and which symbols are missing. It claims no API compatibility, no performance and no correctness. sgl_kernel's 'not ported' is scoped to public PyPI wheels. verified was not assigned; the page stays draft.

## Metrics (before → after)

| Metric | Before | After | Δ |
|--------|--------|-------|---|
| pages | 29 | 29 | — |
| component_coverage | 19 | 19 | — |
| component_total | 20 | 20 | — |
| version_claims_specified | 4 | 4 | — |
| version_claims_total | 6 | 6 | — |
| draft_ratio | 51.7% | 51.7% | — |
| unspecified_ratio | 27.6% | 27.6% | — |
| license_known_ratio | 66.7% | 66.7% | — |
| recall | 1.000 | 1.000 | — |
| tests | 85 | 85 | — |

*No tracked metric changed between baseline and finish.*

## Candidate changes

- `data/aliases.yaml`
- `evals/claude/iteration-state.json`
- `evals/claude/trend.md`
- `queries/by-component.md`
- `queries/by-hardware.md`
- `queries/by-type.md`
- `queries/by-version.md`
- `queries/index.pickle`
- `tests/test_repository.py`
- `wiki/reference/ecosystem-port-status.md`

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
    "pages": 29,
    "draft_ratio": 0.517,
    "unspecified_ratio": 0.276,
    "license_known_ratio": 0.667,
    "_coverage_error": null,
    "component_coverage": 19,
    "component_total": 20,
    "version_claims_specified": 4,
    "version_claims_total": 6,
    "_recall_error": null,
    "recall": 1.0,
    "tests": 85
  },
  "metrics_after": {
    "_quality_gates_error": null,
    "pages": 29,
    "draft_ratio": 0.517,
    "unspecified_ratio": 0.276,
    "license_known_ratio": 0.667,
    "_coverage_error": null,
    "component_coverage": 19,
    "component_total": 20,
    "version_claims_specified": 4,
    "version_claims_total": 6,
    "_recall_error": null,
    "recall": 1.0,
    "tests": 85
  },
  "deltas": {},
  "status": "accepted"
}
```
-->
