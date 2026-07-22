---
{
  "id": "pattern-establish-performance-baseline",
  "title": "优化前先建立可比较的性能基线",
  "type": "wiki-pattern",
  "status": "draft",
  "summary": "用固定环境、正确计时和性能模型约束 MXMACA Kernel 优化迭代。",
  "languages": ["zh-CN"],
  "tags": ["performance", "roofline", "kernel", "benchmark"],
  "hardware": ["c500"],
  "mxmaca_versions": ["unspecified"],
  "components": ["mxmaca-sdk", "mxcc", "mcprofiler"],
  "sources": ["repo-mxmaca-performance-tuning-guide"],
  "related": [],
  "prerequisites": [],
  "verified_at": "2026-07-22",
  "confidence": "source-reported",
  "reproducibility": "procedure",
  "symptoms": ["performance-regression", "unstable-benchmark"],
  "aliases": ["性能基线", "benchmark baseline"]
}
---

# 模式

在修改 Kernel 之前，先冻结硬件、软件栈、输入形状、计时方法和基线实现。公开性能指南把计时、硬件参数 microbenchmark、roofline/延迟隐藏模型和实例优化放在同一学习路径中，这支持“先测量和建模，再选择优化手段”的方法。

## 最小步骤

1. 记录硬件型号、驱动、MXMACA、编译器和相关库版本。
2. 固定输入数据类型、形状、布局、并发和正确性容差。
3. 明确预热、同步点、重复次数和统计量。
4. 保存未优化实现的原始结果与运行命令。
5. 用 profiling 或硬件参数证据判断瓶颈，再提出单一变量的优化假设。
6. 同时比较正确性与性能，保留失败实验。

## 限制

本页没有给出性能数字，也没有断言某个具体优化对任意 MXMACA 版本有效。跨平台示例中的 warp size、宏和硬件参数必须在目标平台重新核对。

## 证据

- `repo-mxmaca-performance-tuning-guide`
