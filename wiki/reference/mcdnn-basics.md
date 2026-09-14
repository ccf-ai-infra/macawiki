---
{
  "id": "reference-mcdnn-basics",
  "title": "mcDNN 数学库基础参考（C500 实测安装证据）",
  "type": "wiki-tool",
  "status": "reviewed",
  "summary": "mcDNN 是 MXMACA 的深度学习算子库。本页给出 C500/MACA 3.7.1.5 上的实测安装证据（库路径与头文件版本宏），以及能力边界。",
  "languages": ["zh-CN"],
  "tags": ["runtime", "installation", "operator-evaluation"],
  "hardware": ["c500"],
  "mxmaca_versions": ["3.7.1.5"],
  "components": ["mcdnn", "mxmaca-sdk", "mxmaca-runtime"],
  "sources": ["local-c500-maca-sdk-install"],
  "related": ["reference-mcblas-basics", "reference-mccl-basics", "recipe-verify-mxmaca-environment", "diagnostics-mx-smi"],
  "prerequisites": ["recipe-verify-mxmaca-environment"],
  "verified_at": "2026-09-14",
  "confidence": "source-reported",
  "reproducibility": "procedure",
  "aliases": ["mcDNN", "libmcdnn", "mcdnn", "MXMACA DNN 库", "深度学习算子库"]
}
---

# 概述

mcDNN 是 MXMACA 软件栈中的深度学习算子库，提供卷积、归一化、激活等推理与训练相关算子的设备实现。它与 mcBLAS 共享安装布局，但头文件与预编译内核镜像独立。

> ✅ **证据状态**：本页的安装与版本证据来自 2026-09-14 在 MetaX C500（MACA 3.7.1.5）上的实测捕获，可复现产物见 `benchmarks/results/environment-c500-components.json`（hostname 已脱敏）。版本号来自**头文件版本宏**，不是文档转录。

## 实测安装布局（MACA 3.7.1.5 / C500）

| 项 | 值 |
|----|----|
| 库文件 | `/opt/maca/lib/libmcdnn.so` → 实际 `/opt/maca-3.7.1/lib/libmcdnn.so` |
| 头文件 | `/opt/maca/include/mcdnn/` 目录（含 `mcdnn.h`、`mcdnn_cnn_infer.h` 等） |
| 版本宏 | `MCDNN_MAJOR 1`、`MCDNN_MINOR 1`、`MCDNN_PATCHLEVEL 1`，即 `1.1.1` |
| 预编译内核 | `/opt/maca/lib/mcdnn_xcore1000_*.mcfb`（另有 `xcore1500` 等按架构分文件） |

与 mcBLAS 相同的两点：`/opt/maca` 是指向 `/opt/maca-3.7.1` 的符号链接，引用时建议用真实路径；`.mcfb` 按设备 ISA 命名，本机 `macainfo` 报告 ISA 为 `METAX-MXC-MXMACA--XCORE1000`（市场名 `MetaX C500`），因此 `xcore1000` 后缀对应 C500——**这是从设备名到内核文件名的推断，不是官方文档陈述**。

## 版本证据的强度与边界

- 证据是**单信号**（头文件宏），因此本页 `confidence` 记为 `source-reported`。
- 与 mcBLAS 不同，本页**没有**记录到可用的运行时版本查询入口（头文件中未见 `mcdnnGetVersion` 之类的稳定符号）。因此 mcDNN 的版本只能以头文件宏为准，无第二条证据路径。
- 安装证据 ≠ 算子覆盖或性能结论。本页只主张「装了什么、什么版本」。

## 使用注意事项

- mcDNN 的算子语义与上游 cuDNN 的对应关系需 MXMACA 特定证据，不可从 CUDA 行为推断。
- 具体算子覆盖（尤其是低精度/混合精度路径）因 MXMACA 版本而异；上述路径与版本针对 MACA 3.7.1.5，其他版本需重新捕获。
- 若某个算子在 mcDNN 中缺失，常见替代路线是 mcBLAS 组合或 TileLang 手写算子（见 `reference-mctilelang-basics`）；无论选哪条，都需在目标版本上重新验证。

## 复现方式

```bash
python3 scripts/capture_environment.py --output /tmp/env.json
# 检查 maca_libraries.libmcdnn.so.real_path
grep -n "MCDNN_MAJOR\|MCDNN_MINOR\|MCDNN_PATCHLEVEL" /opt/maca/include/mcdnn/mcdnn.h
```
