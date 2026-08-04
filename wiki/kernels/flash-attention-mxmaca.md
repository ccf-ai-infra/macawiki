---
{
  "id": "kernel-flash-attention-mxmaca",
  "title": "FlashAttention 在 MXMACA/C500 上的证据与验证指南",
  "type": "wiki-kernel",
  "status": "reviewed",
  "summary": "区分上游 FlashAttention 语义、MXMACA flash_attn 二进制证据和 mcTileLang 实验实现，并给出正确性与性能验证契约。",
  "languages": ["zh-CN", "en"],
  "tags": ["attention", "kernel", "correctness", "compatibility", "benchmark", "performance", "operator-evaluation"],
  "hardware": ["c500"],
  "mxmaca_versions": ["unspecified"],
  "components": ["flash-attn", "pytorch", "mcpytorch", "mctilelang"],
  "sources": ["repo-flash-attention-v2-6-3", "doc-mctilelang-flash-attention-pr-2", "doc-pytorch-operator-reference"],
  "related": ["evaluation-compare-operator-backends", "pattern-establish-performance-baseline", "recipe-verify-mxmaca-environment"],
  "verified_at": "2026-07-31",
  "confidence": "experimental",
  "reproducibility": "procedure",
  "prerequisites": ["recipe-verify-mxmaca-environment", "pattern-establish-performance-baseline"],
  "performance_claims": ["MXMACA flash_attn on C500: not_run; no speedup, support-matrix, or production-readiness claim is made."],
  "version_sensitive": "vc-006",
  "aliases": ["flash_attn", "flash-attn", "FlashAttention", "flash attention", "MXMACA FlashAttention"]
}
---

# 先给结论

Macawiki 可以直接使用上游 FlashAttention v2.6.3 来解释算法、Python API、shape 和 causal/varlen/KV cache 等**语义**，也可以借鉴其正确性测试设计。但上游资料没有声明 MetaX C500/MXMACA 支持，不能作为 C500 安装、ABI、功能覆盖或性能依据。

对于用户观察到的 `flash_attn 2.6.3+metax3.7.1.3torch2.8`，Macawiki 当前没有与 wheel 精确对应的源码、patch set 或构建清单。因此其来源、MetaX 修改、causal/varlen/KV cache/反向传播覆盖和生产支持均为 `unknown`，C500 性能状态为 `not_run`。版本字符串不能填补这条证据缺口。

# 三层对象不能混淆

| 对象 | 现在能证明什么 | 不能证明什么 | 当前状态 |
| --- | --- | --- | --- |
| 上游 FlashAttention v2.6.3 | 算法/API/测试语义，固定 ref 与许可证 | MXMACA 安装、兼容性、支持矩阵和 C500 性能 | `source-reported` |
| MXMACA `flash_attn` wheel | 尚无可审计制品；仅有用户报告的版本字符串 | 对应源码、补丁、ABI、功能完整性与普遍支持 | `unknown` / `not_run` |
| mcTileLang PR !2 示例 | PR 页面报告了 C500-64GB 示例路径和运行截图 | 已合并、已发布、等同于 wheel 源码或完整 FlashAttention 支持 | `experimental` / `not_run` |

mcTileLang 的公开 PR 只是另一个候选实现。它不能替代 MXMACA wheel 的来源证明，也不能因“在 C500 上运行过”就与上游或 wheel 宣称为等价实现。

# MXMACA 二进制需要什么证据

优先接受与二进制精确对应的公开 tag/commit。若没有公开仓库，应由提供方给出 patch set、构建清单或 SBOM、编译器与 ABI、构建参数和可复现说明。

如果源码暂时不可获得，就把 wheel 作为**不透明制品**。拿到制品后必须记录：

1. 完整文件名、版本、获取渠道、获取日期与 SHA256；
2. wheel 的 `METADATA`、`WHEEL`、`RECORD`、`direct_url.json`（如有）；
3. Python 包路径、原生扩展路径及各自哈希；
4. 可安全公开的动态依赖/符号清单；
5. C500、驱动、MACA/MXMACA、mxcc、PyTorch 和 Python 环境指纹；
6. 每个测试 case 的命令、日志、正确性和计时原始样本。

这些黑盒结果只能证明“该哈希制品在该环境和输入下的观察行为”。在制品尚未提供时，不填写假 SHA256，也不把 Issue 中的用户环境观察升级为兼容矩阵。

# 功能与正确性验证

固定任务集见 `benchmarks/flash_attention_cases.yaml`，后端证据要求见 `benchmarks/backends/flash_attn_mxmaca_contract.yaml`。至少逐项验证 fixed-length/varlen、causal/non-causal、fp16/bf16、forward/backward，以及对齐和非对齐 head dimension；只有制品声称支持时才执行 KV cache 高级接口。

正确性参考分两级：

- 用 PyTorch eager/SDPA 构造相同的 scaled dot-product attention 语义；
- 用固定上游 v2.6.3 的测试语义核对 causal mask 对齐、varlen、MQA/GQA、KV cache 和边界行为。

必须使用相同输入、seed、shape、dtype、scale、mask 和 dropout。记录 `allclose`、最大绝对误差、最大相对误差、NaN/Inf；backward 还要分别记录 Q/K/V 梯度误差。容差必须随 dtype 和计算路径在 case 中显式给出，不能先看结果再放宽。正确性门禁未通过时状态为 `not_comparable`，不得计算 speedup。

# 性能对比协议

对比对象为 PyTorch reference、MXMACA `flash_attn` wheel 和可运行的 TileLang/mcTileLang 候选。三者必须在同一 C500、软件栈、输入契约和同步策略下运行；先 warmup，再 device synchronize，保存所有样本并报告 median、P90、吞吐、显存峰值和失败率。

上游 A100/H100/ROCm 数字不属于 C500 基线。mcTileLang PR 的截图也不构成可比较性能数据。当前没有二进制制品与本专题 FlashAttention 的 C500 原始结果，所以三个后端的专题对比统一保持 `not_run`，没有加速比结论。

# Agent 回答契约

当被问到“可以直接在 C500 上安装上游 flash-attn 吗”，回答应为：上游命令只能说明其公开支持的平台，**不能作为 C500 安装依据**；需要官方 MXMACA 安装来源或与 wheel 匹配的构建证据。

当被问到“MXMACA 是否支持 causal、varlen、KV cache 或反向传播”，回答应列出上游 v2.6.3 的语义范围，同时明确 MXMACA 覆盖为 `unknown`，需要按固定矩阵逐项黑盒验证或审阅对应源码。

当被问到“wheel 对应哪份源码”，回答应说明当前没有证据确认，并请求 tag/commit、patch set 或构建清单；不得回答“就是未修改的上游 v2.6.3”。

# 何时可以提升结论状态

- 获得精确源码/构建证据后，可以把来源从 `unknown` 更新为可追溯，但仍不能跳过硬件测试。
- 同一哈希制品在捕获的 C500 环境通过全部正确性与计时门禁后，单个 case 才能从 `not_run` 提升为 `recorded`；是否标记 `verified` 仍需维护者批准。
- 任何环境、shape、dtype、实现或正确性状态不一致时保持 `not_comparable`。
