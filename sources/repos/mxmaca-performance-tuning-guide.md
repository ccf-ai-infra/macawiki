---
{
  "id": "repo-mxmaca-performance-tuning-guide",
  "title": "MXMACA Performance Optimization Guide 仓库",
  "type": "source-repo",
  "status": "draft",
  "summary": "记录公开仓库展示的 C500 Kernel 性能优化方法、示例和 microbenchmark 主题。",
  "languages": ["zh-CN", "en"],
  "tags": ["performance", "roofline", "kernel", "benchmark", "community"],
  "hardware": ["c500"],
  "mxmaca_versions": ["3.7.1.5"],
  "components": ["mxmaca-sdk", "mxcc", "mcprofiler"],
  "sources": [],
  "related": ["pattern-establish-performance-baseline"],
  "verified_at": "2026-07-22",
  "url": "https://gitee.com/metax-maca/mxmaca-performance-tuning-guide",
  "repo": "metax-maca/mxmaca-performance-tuning-guide",
  "ref": "main@65a3f76",
  "source_category": "official-repo",
  "retrieved_at": "2026-07-22",
  "license_status": "unknown",
  "aliases": ["MACA Performance Optimization Guide", "MXMACA 性能优化指南"]
}
---

# 来源摘要

公开仓库首页说明其内容包括性能优化文档、配套实例、microbenchmark 和 roofline 绘图，并以 MetaX C500 为主要目标。仓库展示的章节涉及基础异构编程、C500 架构、reduction、SGEMM 性能建模、优化技巧和性能分析工具。

仓库首页还提示跨平台代码可能存在 warp size 和平台宏差异。这只能支持“跨平台移植需要显式核对平台参数”，不能推出所有示例或技巧在任意 MXMACA 版本上均兼容。

## 许可限制

在 v0.1 采集时，仓库页面未显示明确仓库许可证。Macawiki 因此只保存原创摘要、公开链接和可见 ref，不复制仓库代码或文档正文。
