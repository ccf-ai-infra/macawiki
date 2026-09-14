---
{
  "id": "reference-mcblas-basics",
  "title": "mcBLAS 数学库基础参考（C500 实测安装证据）",
  "type": "wiki-tool",
  "status": "reviewed",
  "summary": "mcBLAS 是 MXMACA 的 BLAS 数学库。本页给出 C500/MACA 3.7.1.5 上的实测安装证据（库路径与头文件版本宏），以及 API 使用边界。",
  "languages": ["zh-CN"],
  "tags": ["runtime", "installation", "operator-evaluation"],
  "hardware": ["c500"],
  "mxmaca_versions": ["3.7.1.5"],
  "components": ["mcblas", "mxmaca-sdk", "mxmaca-runtime"],
  "sources": ["local-c500-maca-sdk-install"],
  "related": ["reference-mxcc-compiler-basics", "recipe-verify-mxmaca-environment", "diagnostics-mx-smi", "reference-mcdnn-basics", "reference-mccl-basics"],
  "prerequisites": ["recipe-verify-mxmaca-environment"],
  "verified_at": "2026-09-14",
  "confidence": "source-reported",
  "reproducibility": "procedure",
  "aliases": ["mcBLAS", "libmcblas", "mcblasLt", "mcblas", "MXMACA BLAS", "数学库"]
}
---

# 概述

mcBLAS 是 MXMACA 软件栈中的 BLAS 层数学库，提供矩阵/向量运算的设备实现。它常与 mcDNN（卷积/推理算子）与 mcCL（集合通信）并列出现，构成 MXMACA 的三层算子栈。

> ✅ **证据状态**：本页的安装与版本证据来自 2026-09-14 在 MetaX C500（MACA 3.7.1.5）上的实测捕获，可复现产物见 `benchmarks/results/environment-c500-components.json`（hostname 已脱敏）。版本号来自**头文件版本宏**，不是文档转录。

## 实测安装布局（MACA 3.7.1.5 / C500）

| 项 | 值 |
|----|----|
| 库文件 | `/opt/maca/lib/libmcblas.so` → 实际 `/opt/maca-3.7.1/lib/libmcblas.so` |
| 伴随库 | `libmcblasLt.so`（与 `libmcblas.so` 同目录） |
| 头文件 | `/opt/maca/include/mcblas/mcblas.h`、`mcblasLt.h`、`mcblasXt.h` |
| 版本宏 | `MCBLAS_VER_MAJOR 1`、`MCBLAS_VER_MINOR 0`（头文件未定义 `MCBLAS_VER_PATCH`） |
| 版本查询 API | `mcblasGetVersion(handle, int*)`、`mcblasGetProperty(...)` |
| 预编译内核 | `/opt/maca/lib/mcblas_xcore1000.mcfb`（另有 `mcblas_xcore1500.mcfb` 等按架构分文件） |

两点解释：

- `/opt/maca` 是**符号链接农场**，指向当前版本目录 `/opt/maca-3.7.1`。引用库路径时建议用 `real_path`（跟随链接后的真实路径），这样版本升级后旧引用仍可追溯。
- `.mcfb` 是预编译内核镜像，按设备 ISA 命名。本机 `macainfo` 报告 GPU 的 ISA 名为 `METAX-MXC-MXMACA--XCORE1000`、市场名 `MetaX C500`，因此 `xcore1000` 后缀对应 C500。**这是从设备名到内核文件名的推断，不是官方文档陈述**。

## 版本证据的强度与边界

- 证据是**单信号**（头文件宏），因此本页 `confidence` 记为 `source-reported`，不是 `verified`。
- `mcblasGetVersion` 需要**已初始化的 handle**。尝试在未初始化 handle 的情况下以 ctypes 直接调用会发生段错误——这是实测结论，本页如实记录，并建议读者不要重复这条路线。
- 因此本页**不给出**运行时 `mcblasGetVersion()` 的返回值；版本仅以头文件宏为准。
- 安装证据 ≠ API 兼容性或性能结论。本页只主张「装了什么、什么版本」。

## 使用注意事项

- mcBLAS 的 API 与上游 BLAS/CUBLAS 的对应关系需 MXMACA 特定证据，不可从 CUDA 行为推断。
- 链接时用 `-lmcblas`；`mcblasLt` 提供轻量级运行时调度入口，与 `mcblas` 分库。
- 具体算子覆盖与精度支持因 MXMACA 版本而异；上述路径与版本针对 MACA 3.7.1.5，其他版本需重新捕获。

## 复现方式

```bash
python3 scripts/capture_environment.py --output /tmp/env.json
# 检查 maca_libraries.libmcblas.so.real_path 与 tools 块
```

头文件版本宏的核对方式（只读，不加载库）：

```bash
grep -n "MCBLAS_VER_" /opt/maca/include/mcblas/mcblas.h
```
