---
{
  "id": "reference-mccl-basics",
  "title": "mcCL 集合通信库基础参考（C500 实测安装证据）",
  "type": "wiki-tool",
  "status": "reviewed",
  "summary": "mcCL 是 MXMACA 的集合通信库。本页给出 C500/MACA 3.7.1.5 上的实测安装证据，含一次头文件宏与工具自报版本的一致性交叉验证。",
  "languages": ["zh-CN"],
  "tags": ["runtime", "installation", "operator-evaluation"],
  "hardware": ["c500"],
  "mxmaca_versions": ["3.7.1.5"],
  "components": ["mccl", "mxmaca-sdk", "mxmaca-runtime"],
  "sources": ["local-c500-maca-sdk-install"],
  "related": ["reference-mcblas-basics", "reference-mcdnn-basics", "recipe-verify-mxmaca-environment", "diagnostics-mx-smi"],
  "prerequisites": ["recipe-verify-mxmaca-environment"],
  "verified_at": "2026-09-14",
  "confidence": "corroborated",
  "reproducibility": "procedure",
  "aliases": ["mcCL", "libmccl", "mccl", "MXMACA 集合通信", "RAS", "mcclras"]
}
---

# 概述

mcCL 是 MXMACA 软件栈中的集合通信库（collective communication），提供多设备/多进程间的通信原语。本页记录它在 C500 上的安装证据与一次版本交叉验证。

> ✅ **证据状态**：本页的安装与版本证据来自 2026-09-14 在 MetaX C500（MACA 3.7.1.5）上的实测捕获，可复现产物见 `benchmarks/results/environment-c500-components.json`（hostname 已脱敏）。

## 实测安装布局（MACA 3.7.1.5 / C500）

| 项 | 值 |
|----|----|
| 库文件 | `/opt/maca/lib/libmccl.so` → 实际 `/opt/maca-3.7.1/lib/libmccl.so` |
| 头文件 | `/opt/maca/include/mccl.h` |
| 版本宏 | `MCCL_MAJOR 2`、`MCCL_MINOR 16`、`MCCL_PATCH 5`（另有 `MCCL_VERSION_CODE 21605`） |
| 伴随工具 | `/opt/maca/bin/mcclras`（RAS 客户端，`--version` 自报 `MCCL RAS client version 2.16.5`） |

`/opt/maca` 是指向 `/opt/maca-3.7.1` 的符号链接农场，引用库路径时建议用真实路径。

## 一次交叉验证（本库独有）

mcCL 在本机有**两个独立版本信号**，且一致：

1. 编译期证据：`mccl.h` 的宏 `MCCL_MAJOR/MINOR/PATCH = 2/16/5`。
2. 运行期证据：`mcclras --version` 自报 `MCCL RAS client version 2.16.5`。

两者给出同一版本号，因此 mcCL 的版本证据记为 `corroborated`——这是本 cluster 三个数学库中唯一有交叉验证的一个。mcBLAS 与 mcDNN 只有头文件宏这一个信号，记为 `source-reported`。

需要注意：`mcclras` 自报的是 **RAS client** 的版本，严格说它是 mcCL 包内的一个组件版本，而不是 `libmccl.so` 运行时版本的直接读数。把它当作库版本的第二条证据，依赖「同一包内组件与库主版本一致」这一通常成立但未被官方文档明示的假设。本页如实标注这一点，不将其升级为 `verified`。

## 使用注意事项

- 集合通信的行为（语义、拓扑、环境变量）与上游 NCCL 的对应关系需 MXMACA 特定证据，不可从 CUDA 行为推断。
- mcCL 的版本号体系（`2.16.5`）与 MXMACA 主版本（`3.7.1.5`）是**两条独立版本线**：一个 MXMACA 版本可搭载某个特定 mcCL 版本，但两者不互相推导。本页记录的是「MACA 3.7.1.5 搭载 mcCL 2.16.5」这一共存事实。
- 多卡场景下 mcCL 的性能与拓扑强相关；本页没有任何性能主张。
- 上述路径与版本针对 MACA 3.7.1.5 安装，其他版本需重新捕获。

## 复现方式

```bash
python3 scripts/capture_environment.py --output /tmp/env.json
# 检查 maca_libraries.libmccl.so.real_path 与 tools.mcclras.version
grep -n "MCCL_MAJOR\|MCCL_MINOR\|MCCL_PATCH\|MCCL_VERSION_CODE" /opt/maca/include/mccl.h
/opt/maca/bin/mcclras --version
```
