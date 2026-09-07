---
{
  "id": "evaluation-compare-operator-backends",
  "title": "用 PyTorch、TileLang、MXMACA++ 比较算子实现",
  "type": "wiki-recipe",
  "status": "reviewed",
  "summary": "在同一输入、正确性和 C500 环境契约下，把 PyTorch 参考实现与 TileLang、MXMACA++ 候选实现进行可审计比较。",
  "languages": ["zh-CN", "en"],
  "tags": ["operator-evaluation", "correctness", "benchmark", "performance", "kernel"],
  "hardware": ["c500"],
  "mxmaca_versions": ["3.7.1.5"],
  "components": ["pytorch", "mctilelang", "mxmaca-cpp", "mxcc", "mxmaca-runtime"],
  "sources": ["doc-pytorch-operator-reference", "repo-mxmaca-performance-tuning-guide"],
  "related": ["pattern-establish-performance-baseline", "recipe-verify-mxmaca-environment"],
  "prerequisites": ["recipe-verify-mxmaca-environment", "pattern-establish-performance-baseline"],
  "verified_at": "2026-07-22",
  "confidence": "corroborated",
  "reproducibility": "procedure",
  "aliases": ["三后端算子对比", "PyTorch TileLang MXMACA++", "operator benchmark"]
}
---

# 目的

将 PyTorch 已实现的 `add`、`softmax`、`layer_norm` 和 `matmul` 作为语义参考，再比较 TileLang 与 MXMACA++ 的候选实现。仓库提供 `benchmarks/operator_cases.yaml`、PyTorch runner 和两个后端契约；当前没有 C500/MXMACA，因此后端状态必须保持 `not_run`。

# 统一输入与正确性

1. 从同一 case 文件读取 shape、dtype、参数、seed 和容差。
2. 生成一次输入并保存其描述；不要让不同后端各自随机生成不可复现输入。
3. 以 PyTorch 输出作为 reference，至少记录最大绝对误差、相对误差或 `allclose` 结果。
4. 对 softmax/layer norm 等归约算子单独检查 NaN、Inf、行和/均值方差等不变量。
5. 正确性门禁未通过时，结果为 `not_comparable`，不计算 speedup。

# 计时与环境

固定 warmup、iterations、同步策略、统计量和输入驻留位置。先运行 `scripts/capture_environment.py`，记录 C500 设备字符串、驱动、MXMACA、mxcc、PyTorch、TileLang、MXMACA++ 版本和源码 commit。同步 API 必须由目标栈确认；不要把 CUDA API 当成 MXMACA 事实。

`benchmarks/pytorch_baseline.py --device cpu` 只能验证工作流与 schema。只有三后端在同一 C500 环境中完成正确性，且环境 fingerprint、case_id 和计时契约一致时，`scripts/compare_benchmarks.py` 才允许输出 speedup。

# 最小演练

```bash
python3 benchmarks/pytorch_baseline.py --list
python3 benchmarks/pytorch_baseline.py --operator add --device cpu --correctness-only
python3 benchmarks/pytorch_baseline.py --operator all --profile smoke --device cpu --output results/pytorch.json
```

后续在 C500 上实现并运行 `benchmarks/backends/tilelang_contract.yaml` 和 `benchmarks/backends/mxmacacpp_contract.yaml`，然后使用同一结果 schema 比较。没有真实运行就填写 `not_run`，不要用占位值。

# 证据边界

PyTorch API 页面支持参考语义；公开性能指南支持“先冻结基线、再 profiling/建模”的方法。两者都不能证明某个 TileLang 或 MXMACA++ 实现的 C500 性能。性能结论需等待目标环境原始结果与人工审阅。

## 跨平台移植提示

性能调优指南首页提示：跨平台代码可能存在 warp size 与平台宏差异。这只能支持"把 CUDA/其他后端的算子移植到 MXMACA 时，必须显式核对硬件参数与平台宏，不能照搬"这一结论，不足以支撑独立的迁移指南页面。新增迁移页或迁移结论，需先在目标 C500 上完成一次真实的 kernel 移植验证并闭环证据。
