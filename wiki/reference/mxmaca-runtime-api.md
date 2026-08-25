---
{
  "id": "reference-mxmaca-runtime-api",
  "title": "MXMACA Runtime API 参考（能力边界与验证清单）",
  "type": "wiki-tool",
  "status": "draft",
  "summary": "MXMACA 运行时管理设备上下文、内存分配与 kernel 启动。本页给出能力边界和验证清单，不提供版本特定的 API 签名。",
  "languages": ["zh-CN"],
  "tags": ["runtime", "programming-model", "installation"],
  "hardware": ["unspecified"],
  "mxmaca_versions": ["unspecified"],
  "components": ["mxmaca-runtime", "mxmaca-sdk"],
  "sources": ["doc-mxmaca-programming-model", "repo-mxmaca-runtime"],
  "related": ["reference-mxcc-compiler-basics", "recipe-verify-mxmaca-environment", "tutorial-first-mxmaca-program"],
  "prerequisites": ["recipe-verify-mxmaca-environment"],
  "verified_at": "2026-08-25",
  "confidence": "source-reported",
  "reproducibility": "concept",
  "aliases": ["MXMACA Runtime API", "运行时 API", "runtime api", "设备内存管理", "kernel 启动"]
}
---

# 概述

MXMACA 运行时（Runtime）是 MXMACA 软件栈中负责设备管理、内存操作和 kernel 启动的组件。官方编程模型文档（`doc-mxmaca-programming-model`）将其职责概括为三块：**设备上下文管理、内存分配与释放、kernel 启动**；公开仓库 `repo-mxmaca-runtime` 的入口摘要与之一致。

本页是**能力边界与验证清单**，不是 API 签名手册。具体函数签名、参数和宏因 MXMACA 版本和目标硬件而异，使用前必须查阅对应版本的官方文档。

## 能力边界

依据官方文档与仓库摘要，运行时 API 提供以下类别的能力：

- **设备管理**：枚举与选择设备、查询设备属性、管理上下文。
- **内存操作**：设备内存分配/释放、主机与设备之间数据传输。
- **Kernel 启动**：加载并启动由 mxcc 编译的 kernel，传递参数。
- **同步与错误处理**：kernel 执行同步、错误码查询。

## 验证清单

在缺少明确版本安装命令时，按以下清单核对运行时是否可用：

1. 记录目标硬件型号与驱动版本。
2. 记录 MXMACA SDK 与运行时版本（`mx-smi`、`mxcc --version` 或等价命令）。
3. 确认运行时 API 头文件与库路径存在于安装目录。
4. 编译并运行一个最小 kernel（如向量加法），确认能完成设备内存分配、kernel 启动与结果回读。
5. 保存所用官方文档 URL/版本、编译命令、退出状态与运行输出。

## 使用约束

- 本页不列出具体 API 签名：签名与语义因版本而异。
- 不能从 CUDA Runtime API 行为推断 MXMACA 等价性——需 MXMACA 特定证据。
- 编译器（mxcc）与运行时版本必须匹配。
- 遇到版本不明确时停止，不从其他版本复制调用方式。
