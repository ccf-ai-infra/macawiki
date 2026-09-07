---
{
  "id": "diagnostics-mx-smi",
  "title": "mx-smi 硬件与版本查询工具（能力边界与验证清单）",
  "type": "wiki-tool",
  "status": "reviewed",
  "summary": "mx-smi 是 MXMACA 环境探针依赖的硬件/版本查询工具。本页给出能力边界和验证清单，附一份真实 C500 捕获样本（mx-smi 2.3.1 / MACA 3.7.1.5 / 驱动 3.8.30）。",
  "languages": ["zh-CN", "en"],
  "tags": ["diagnostics", "installation", "benchmark"],
  "hardware": ["c500"],
  "mxmaca_versions": ["3.7.1.5"],
  "components": ["mx-smi", "diagnostics", "mxmaca-sdk", "mxmaca-runtime", "mxcc"],
  "sources": ["repo-mxmaca-performance-tuning-guide"],
  "related": ["recipe-verify-mxmaca-environment", "pattern-establish-performance-baseline", "reference-mxmaca-runtime-api"],
  "prerequisites": ["recipe-verify-mxmaca-environment"],
  "verified_at": "2026-09-07",
  "confidence": "corroborated",
  "reproducibility": "procedure",
  "aliases": ["mx-smi", "mxsmi", "MX-SMI", "硬件查询", "设备信息", "显存查询"]
}
---

# 概述

`mx-smi` 是当前环境探针（`scripts/env_detector.py`、`benchmarks/env_capture.py`）用于查询 MetaX 硬件与 MXMACA 软件栈版本的工具。它在本仓库中承担的角色是：进程内调用 `mx-smi` 并解析其文本输出，以获得设备型号、MACA 版本、驱动版本以及运行指标（GPU 利用率、显存用量、功耗、温度）。

> ✅ **证据状态**：本页已附带一份在 MetaX C500 上捕获的真实 `mx-smi` 输出样本（`mx-smi` 2.3.1、MACA 3.7.1.5、内核模式驱动 3.8.30，捕获于 2026-09-07）。配套的可复现环境捕获见 `benchmarks/results/environment-c500.json`（hostname 已脱敏）。

## 能力边界（信息类别）

根据环境探针对其输出的解析目标，`mx-smi` 提供：

- **设备标识**：设备序号与型号名称。
- **软件栈版本**：MACA 版本、内核模式驱动版本。
- **运行指标**：GPU 利用率、显存用量与总量、功耗（当前/上限）、温度。

这些信息用于环境指纹与性能基线（见 `pattern-establish-performance-baseline`），以及校验硬件与驱动是否匹配（见 `recipe-verify-mxmaca-environment`）。

## 真实捕获样本（MetaX C500）

以下为 2026-09-07 在 C500 上执行 `mx-smi`（无参数）的完整输出（MX-SMI 2.3.1）：

```
mx-smi  version: 2.3.1

=================== MetaX System Management Interface Log ===================
Timestamp                                         : Mon Sep  7 07:00:31 2026

Attached GPUs                                     : 1
+---------------------------------------------------------------------------------+
| MX-SMI 2.3.1                       Kernel Mode Driver Version: 3.8.30           |
| MACA Version: 3.7.1.5              BIOS Version: 1.33.5.0                       |
|------------------+-----------------+---------------------+----------------------|
| Board       Name | GPU   Persist-M | Bus-id              | GPU-Util      sGPU-M |
| Pwr:Usage/Cap    | Temp   Perf     | Memory-Usage        | GPU-State            |
|==================+=================+=====================+======================|
| 0     MetaX C500 | 0           Off | 0000:12:00.0        | 0%          Disabled |
| 37W / 350W       | 32C          P0 | 826/65536 MiB       | Available            |
+------------------+-----------------+---------------------+----------------------+

+---------------------------------------------------------------------------------+
| Process:                                                                        |
|  GPU                    PID         Process Name                 GPU Memory     |
|                                                                  Usage(MiB)     |
|=================================================================================|
|  no process found                                                               |
+---------------------------------------------------------------------------------+

End of Log
```

> ⚠️ 样本说明：上述指标（826/65536 MiB、37W/350W、32°C P0）是**空闲状态**下单次捕获，不代表负载画像。`mx-smi` 还支持按需采样（`-l <ms>`）与 CSV 输出（`-o <file>`），用于持续观测时使用。

`mx-smi --help` 展示的能力范围（该版本）包括：温度、PMBus/板卡功耗、芯片序列号、显存、EEPROM、版本（MACA/BIOS/驱动/固件）、PCIe、风扇转速、HBM 带宽、系统信息、进程列表（`--show-process` / `--show-all-process`）、持久模式（`--show-persistence-mode` / `--set-persistence-mode`）、电源模式（`--set-power-mode`）、采样间隔（`-l <ms>`）、CSV 输出（`-o <file>`）等。`--show-version` 单独输出 MACA/BIOS/驱动/固件版本。

## 与仓库工具链的对应关系

`scripts/env_detector.py` 与 `benchmarks/env_capture.py` 对 `mx-smi` 文本布局的解析（设备名、`MACA Version:`、`Kernel Mode Driver Version:`、`MiB` 显存、`W` 功耗、`C` 温度）已用上述真实样本核对通过，无需正则校准。

## 验证清单

在运行或报告 `mx-smi` 结果前，按以下清单核对：

1. 确认 `mx-smi` 是否在 `PATH` 中（`which mx-smi`）。
2. 记录输出中的设备型号、MACA 版本与驱动版本；缺失（即未解析到）时不臆测。
3. 若用于性能基线，将设备/版本字段写入结果 JSON 的环境块，供两后端可比性校验。
4. 若某字段未解析到，`not_comparable` 优先于猜测，不虚构硬件事实。

## 使用约束

- 不要用 CUDA 的 `nvidia-smi` 输出格式去推断 `mx-smi` 的任何字段——需 MXMACA 特定证据。
- `<path>` 不存在或输出布局超出预期时，工具返回空值（null）而非报错，这是有意设计；文档与响应也不应据此虚构。
- 具体命令参数与输出布局因 MXMACA 版本而异；上述样本与字段对应关系针对 mx-smi 2.3.1 + MACA 3.7.1.5 + 驱动 3.8.30 记录，其他版本需以实际输出为准。