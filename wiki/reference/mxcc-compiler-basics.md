---
{
  "id": "reference-mxcc-compiler-basics",
  "title": "mxcc 编译器基础参考",
  "type": "wiki-tool",
  "status": "reviewed",
  "summary": "mxcc 是 MXMACA C/C++ 编译器，将 MACA kernel 代码编译为可在 MetaX 硬件上执行的二进制。",
  "languages": ["zh-CN"],
  "tags": ["compiler", "programming-model"],
  "hardware": ["c500"],
  "mxmaca_versions": ["3.7.1.5"],
  "components": ["mxcc", "mxmaca-sdk", "mxmaca-runtime"],
  "sources": ["doc-mxmaca-compiler-mxcc", "doc-mxmaca-quick-start"],
  "related": ["recipe-verify-mxmaca-environment", "tutorial-first-mxmaca-program"],
  "prerequisites": ["recipe-verify-mxmaca-environment"],
  "verified_at": "2026-07-22",
  "confidence": "source-reported",
  "reproducibility": "concept",
  "aliases": ["mxcc", "MACA 编译器", "编译器选项"]
}
---

# 概述

mxcc 是 MXMACA 软件栈中的 C/C++ 编译器，负责将 MACA kernel 源代码编译为 MetaX 硬件可执行的目标代码。它与 MXMACA 运行时协同工作，管理 kernel 的加载与启动。

## 关键角色

- 编译 MACA C/C++ kernel 为设备端二进制。
- 支持与 MXMACA 运行时 API 的集成。
- 编译选项决定优化级别、目标架构和调试信息。

## 使用注意事项

- mxcc 不是 nvcc 的直接替代品，编译选项和宏定义不可直接照搬 CUDA 项目。
- 具体编译参数（目标架构、优化级别等）因 MXMACA 版本和目标硬件而异。
- 使用前必须查阅对应版本的官方文档。
- 本页不列出具体的命令行参数，以避免因版本差异导致误导。

## 与运行时协作

编译后的 kernel 通过 MXMACA 运行时 API 加载并启动。运行时负责：
- 设备内存管理。
- Kernel 启动参数传递。
- 执行同步与错误处理。

编译器与运行时的版本必须匹配。
