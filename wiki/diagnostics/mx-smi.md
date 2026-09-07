---
{
  "id": "diagnostics-mx-smi",
  "title": "mx-smi 硬件与版本查询工具（能力边界与验证清单）",
  "type": "wiki-tool",
  "status": "draft",
  "summary": "mx-smi 是 MXMACA 环境探针依赖的硬件/版本查询工具。本页给出能力边界和验证清单，不承诺具体输出字段布局。",
  "languages": ["zh-CN", "en"],
  "tags": ["diagnostics", "installation", "benchmark"],
  "hardware": ["c500"],
  "mxmaca_versions": ["unspecified"],
  "components": ["mx-smi", "diagnostics", "mxmaca-sdk", "mxmaca-runtime", "mxcc"],
  "sources": ["repo-mxmaca-performance-tuning-guide"],
  "related": ["recipe-verify-mxmaca-environment", "pattern-establish-performance-baseline", "reference-mxmaca-runtime-api"],
  "prerequisites": ["recipe-verify-mxmaca-environment"],
  "verified_at": "2026-08-25",
  "confidence": "source-reported",
  "reproducibility": "procedure",
  "aliases": ["mx-smi", "mxsmi", "MX-SMI", "硬件查询", "设备信息", "显存查询"]
}
---

# 概述

`mx-smi` 是当前环境探针（`scripts/env_detector.py`、`benchmarks/env_capture.py`）用于查询 MetaX 硬件与 MXMACA 软件栈版本的工具。它在本仓库中承担的角色是：在缺少精确 C500 环境的前提下，进程内调用 `mx-smi` 并解析其文本输出，以获得设备型号、MACA 版本、驱动版本以及运行指标（GPU 利用率、显存用量、功耗、温度）。

> ⚠️ **证据边界**：本仓库当前没有一份真实捕获的 `mx-smi` 输出样本。工具链的正则表达式描述了期望的文本布局，但没有捕获证据支撑"输出恰好长这样"。因此本页只声明 `mx-smi` 提供的信息**类别**，不断言具体字段或布局。

## 能力边界（信息类别）

根据环境探针对其输出的解析目标，`mx-smi` 预期提供：

- **设备标识**：设备序号与型号名称。
- **软件栈版本**：MACA 版本、内核模式驱动版本。
- **运行指标**：GPU 利用率、显存用量与总量、功耗（当前/上限）、温度。

这些信息用于环境指纹与性能基线（见 `pattern-establish-performance-baseline`），以及校验硬件与驱动是否匹配（见 `recipe-verify-mxmaca-environment`）。

## 验证清单

在运行或报告 `mx-smi` 结果前，按以下清单核对：

1. 确认 `mx-smi` 是否在 `PATH` 中（`which mx-smi`）。
2. 记录输出中的设备型号、MACA 版本与驱动版本；缺失（即未解析到）时不臆测。
3. 若用于性能基线，将设备/版本字段写入结果 JSON 的环境块，供两后端可比性校验。
4. 若某字段未解析到，`not_comparable` 优先于猜测，不虚构硬件事实。

## 使用约束

- 不要用 CUDA 的 `nvidia-smi` 输出格式去推断 `mx-smi` 的任何字段——需 MXMACA 特定证据。
- `<path>` 不存在或输出布局超出预期时，工具返回空值（null）而非报错，这是有意设计；文档与响应也不应据此虚构。
- 具体命令参数与输出布局因 MXMACA 版本而异；本页在获得真实样本前不固定样板用法。