# Macawiki iteration trend

14 cycles recorded: 14 accepted, 0 rejected, 0 abandoned, 0 in progress. 4 carry measurable metrics.

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
| 14 | ✅ accepted | 29 | 19/20 | 4/6 | 51.7% | 27.6% | 66.7% | 1.000 | 85 |

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

- `pages`: 28 → 29 (up 1.0)
- `component_coverage`: 18 → 19 (up 1.0)
- `version_claims_specified`: flat at 4
- `draft_ratio`: 50.0% → 51.7% (up 1.7pp)
- `unspecified_ratio`: 28.6% → 27.6% (down 1.0pp)
- `license_known_ratio`: 58.3% → 66.7% (up 8.4pp)
- `recall`: flat at 1.000
- `tests`: 72 → 85 (up 13.0)

Note: `up` is not always improvement. Draft ratio and unspecified
ratio are *better when lower*; the symbol only records direction.

## Most recent decision

**Cycle 14 (accepted)**

> ACCEPTED. All three falsifiable parts of the hypothesis reproduced on this machine.

Coverage: component_coverage 18/20 -> 19/20. The page declares mcpytorch, mctriton, mctilelang, flash-attn, sglang, mxmaca-sdk and mxmaca-runtime; sglang was the only one of those with zero pages before, so coverage moved by exactly one bucket and not by padding. Recall stays 1.000 and tests went 84 -> 85.

Retrieval: three query terms that returned zero results before this cycle now each resolve to exactly one page -- 'sglang' 1, 'flashinfer' 1, 'omni' 1 -- plus the Chinese alias '生态移植' 1. This is the part that matters: the failure this cycle was built to fix was not a missing metric, it was an agent asking about sglang-omni and getting nothing. The zero-result query is the failure mode that a coverage ratio cannot see.

Version fidelity: every version the page states was re-measured live before finishing, not carried from notes -- torch 2.8.0+metax3.7.1.3, torch.version.cuda 11.6, capability (8,0), arch list ['sm_80'], flashinfer 0.2.6+metax3.7.1.3torch2.8, triton 3.0.0, flash_attn 2.6.3, platform CudaSRTPlatform with is_cuda() True. All matched the page as written.

Two things are recorded against the change rather than for it.

1. draft_ratio moved 50.0% -> 51.7%, a real regression. The new page is status: draft because the end-to-end claim is not verified -- sglang-omni's pipeline launches but model serving is blocked by the qwen-tts/transformers pin conflict (qwen-tts pins transformers 4.57.3, sglang pins 5.12.1, the box has 5.8.0). That conflict is dependency resolution, not MXMACA compatibility, and it was deliberately NOT shimmed: patching @check_model_inputs() would falsify real model input validation and make any inference result untrustworthy. So the page ships as draft with the gap stated in its evidence-boundaries section, and the ratio is the honest price of saying 'this is what we measured, not what we achieved'. Promoting it to reviewed requires a separate venv or an upstream qwen-tts release for transformers 5.x, plus an actual serve run.

2. The before-snapshot is stale. The page, the aliases and the index were already written when --begin ran, so metrics_before reports pages 29 and component_coverage 19 -- the post-change state. The true before-state was measured at the start of this session, before any file was touched: 28 pages, component_coverage 18/20, and zero results for sglang/flashinfer/omni. The 18 -> 19 and 28 -> 29 deltas above are from that session-start measurement, not from the state file. The trend tool will read the recorded numbers, so this delta must not be consumed as a validated before/after pair.

The non-obvious finding, and the reason this page exists at all: an agent reading sglang-omni's README would conclude it has no MXMACA backend and stop. That conclusion was wrong here -- it was my own conclusion earlier in this session and empirical testing overturned it. MXMACA exposes the C500 through the torch.cuda namespace, so sglang's platform layer resolves it as CudaSRTPlatform and is_cuda() is True. The page records two concrete consequences that an adapter will hit: `if is_cuda():` guards run unconditionally so SGLANG_IS_FLASHINFER_AVAILABLE=false does not skip the flashinfer fp8/fp4 imports, and metax flashinfer's ~23s first import exceeds check-gpu's 30s timeout and gets reported as unavailable when it is merely slow. Those two are configuration-shaped problems and are the actionable part of the page; the sgl_kernel gap is not -- it needs an sm80/CUDA-11.6 metax build, which is compilation work.

Evidence boundaries kept: the page claims only what is installed, what version, and which symbols are missing. It claims no API compatibility, no performance and no correctness. sgl_kernel's 'not ported' is scoped to public PyPI wheels. verified was not assigned; the page stays draft.

