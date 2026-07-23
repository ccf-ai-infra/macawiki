---
{
  "id": "diagnostics-mcprofiler-basics",
  "title": "mcProfiler 基本使用",
  "type": "wiki-tool",
  "status": "draft",
  "summary": "mcProfiler 是 MXMACA 的性能分析工具，用于收集硬件计数器、timeline 和 kernel 执行特征。",
  "languages": ["zh-CN"],
  "tags": ["profiling", "performance", "diagnostics"],
  "hardware": ["c500"],
  "mxmaca_versions": ["unspecified"],
  "components": ["mcprofiler", "mxmaca-sdk", "mxmaca-runtime", "mxcc"],
  "sources": ["repo-mxmaca-performance-tuning-guide", "doc-mxmaca-quick-start"],
  "related": ["pattern-establish-performance-baseline", "reference-mxcc-compiler-basics"],
  "prerequisites": ["recipe-verify-mxmaca-environment", "pattern-establish-performance-baseline"],
  "verified_at": "2026-07-22",
  "confidence": "source-reported",
  "reproducibility": "procedure",
  "aliases": ["mcProfiler", "profiler", "性能分析", "profiling"]
}
---

# 概述

mcProfiler 是 MXMACA 软件栈中的性能分析工具，用于：
- 收集 kernel 执行的硬件计数器。
- 生成 timeline 追踪。
- 分析计算/内存带宽利用率。
- 为 roofline 模型提供数据。

## 在性能基线中的位置

mcProfiler 的输出是建立性能基线（见 `pattern-establish-performance-baseline`）的关键输入：
1. 在固定环境和输入下运行 target kernel。
2. 使用 mcProfiler 收集硬件计数器。
3. 将数据填入 roofline 或延迟隐藏模型。
4. 确定瓶颈类型（计算受限或带宽受限）后再选择优化策略。

## 使用约束

- mcProfiler 不是 nvprof 或 Nsight 的等价替代品，输出格式和指标名称不同。
- 具体使用命令和参数因 MXMACA 版本而异。
- 本页不提供通用命令行示例，避免在不同版本间产生误导。
- Profiling 开销可能影响短 kernel 的计时准确性；需要与裸计时交叉验证。

## 与计时协作

- 先用 mcProfiler 确定瓶颈类型。
- 再用精确计时（warmup + 同步 + 多样本）测量具体 kernel 的执行时间。
- 两者不可相互替代。
