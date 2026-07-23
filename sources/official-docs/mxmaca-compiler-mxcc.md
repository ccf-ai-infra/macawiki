---
{
  "id": "doc-mxmaca-compiler-mxcc",
  "title": "MXMACA C/C++ Compiler (mxcc) Documentation",
  "type": "source-doc",
  "status": "draft",
  "summary": "mxcc compiler documentation covering compilation options, target architectures, and optimization levels as listed in the official documentation center.",
  "languages": ["zh-CN", "en"],
  "tags": ["compiler", "documentation"],
  "hardware": ["c500"],
  "mxmaca_versions": ["3.7.1.5"],
  "components": ["mxcc", "mxmaca-sdk"],
  "sources": [],
  "related": ["doc-mxmaca-quick-start", "reference-mxcc-compiler-basics"],
  "verified_at": "2026-07-22",
  "url": "https://developer.metax-tech.com/doc",
  "source_category": "official-doc",
  "retrieved_at": "2026-07-22",
  "license_status": "source-terms",
  "aliases": ["mxcc docs", "mxcc 文档"]
}
---

# 来源摘要

MXMACA C/C++ 编译器 (mxcc) 文档涵盖编译选项、目标架构支持、优化级别以及与运行时 API 的集成。本页仅记录公开入口和主题范围，不复制文档正文。

## 可支持的结论

- mxcc 编译 MACA C/C++ kernel 代码为设备端二进制。
- 编译选项因目标硬件和 MXMACA 版本而异。
- mxcc 不是 nvcc 的直接替代品。

## 限制

- 不提供具体命令行参数（因版本而异）。
- 版本范围标记为 `unspecified`。
