---
{
  "id": "local-c500-maca-sdk-install",
  "title": "本地 C500 MXMACA SDK 安装实测记录（MACA 3.7.1.5）",
  "type": "source-repo",
  "status": "draft",
  "summary": "在 MetaX C500 上实测的 MXMACA SDK 安装布局：数学库、追踪/诊断工具与版本证据。事实来自本机文件系统，不来自任何公开文档副本。",
  "languages": ["zh-CN"],
  "tags": ["installation", "runtime", "diagnostics", "benchmark"],
  "hardware": ["c500"],
  "mxmaca_versions": ["3.7.1.5"],
  "components": ["mxmaca-sdk", "mxmaca-runtime", "mxcc", "mcblas", "mccl", "mcdnn", "mctracer", "mcprofiler"],
  "sources": [],
  "related": ["repo-mcpytorch", "diagnostics-mx-smi", "recipe-verify-mxmaca-environment"],
  "verified_at": "2026-09-14",
  "url": "local:///opt/maca-3.7.1",
  "repo": "metax-maca (local install)",
  "ref": "local-install@/opt/maca-3.7.1 (mx-smi 报告 MACA 3.7.1.5)",
  "source_category": "official-repo",
  "retrieved_at": "2026-09-14",
  "license_status": "restricted",
  "note": "本地捕获类证据，非公开文档副本。URL 使用 local:// 前缀明确表示来源是本机安装而非可下载文档；版本号均为本机实测，不从文档推断。",
  "aliases": ["MXMACA SDK 安装", "C500 SDK", "/opt/maca", "MACA 3.7.1.5 安装"]
}
---

# 来源摘要

本页记录 2026-09-14 在一台 MetaX C500（mx-smi 2.3.1 / MACA 3.7.1.5 / 驱动 3.8.30）上实测的
MXMACA SDK 安装布局。所有事实来自本机文件系统与工具输出，已写入可复现的捕获产物：

```
benchmarks/results/environment-c500-components.json
```

该产物由 `scripts/capture_environment.py --output <path>` 生成，hostname 与硬件 UUID 默认脱敏。

# 许可

安装根目录提供专有最终用户许可协议（不是宽松许可）：

| 文件 | 标题 | 版本与日期 | 语言 |
|------|------|-----------|------|
| `/opt/maca-3.7.1/EULA-en.txt` | End User License Agreement | Version 1.0, September 13, 2025 | 英文 |
| `/opt/maca-3.7.1/EULA-zh.txt` | 沐曦软件开发套件（SDK）最终用户许可协议 | 同上 | 中文 |

据此外推的结论：该安装是**受专有 EULA 约束的商业 SDK**，不是 permissive 或开源许可软件。
本页只记录许可**存在、标题、版本与性质**，不复制协议正文（本仓库的捕获策略为
metadata-and-original-summary-only）。该许可为 `restricted` 类别：可用于验证「许可状态可确定」
这一事实，但**不**构成许可条款的摘要，也**不**授予任何权利。

许可状态此前记为 `unknown`；2026-09-15 探得上述文件后改为 `restricted`，使本源的许可状态可确定。

# 本页与公开来源的关系

`url` 字段使用 `local://` 前缀：本页的**来源是本机安装本身**，不是任何公开文档的副本。这样做的原因是
本仓库的网络环境无法访问 `developer.metax-tech.com`，因此版本号一律以本机实测为准，不从文档推断——
这与 `AGENTS.md`「版本未知时标记 `unspecified`，不臆测」一致。

本地捕获在本仓库是已被接受的证据类别（先例：`repo-mcpytorch` 记录 `mxmaca_versions: ["3.7.1.5"]`，
`benchmarks/results/environment-c500.json` 作为环境证据提交）。本页把同一做法扩展到此前完全没有记录的
数学库与追踪工具。

# 实测到的安装布局

工具与库（路径来自捕获产物，`real_path` 已跟随 `/opt/maca` 符号链接）：

| 组件 | 路径 | 实测版本 |
|------|------|----------|
| mxcc | `/opt/maca/mxgpu_llvm/bin/mxcc` | `1.0.0 (d9102a1572)`，InstalledDir `/opt/maca-3.7.1/mxgpu_llvm/bin` |
| mcTracer | `/opt/maca/bin/mcTracer` | `3.7.1.5-ef9e10e` |
| mcclras | `/opt/maca/bin/mcclras` | `MCCL RAS client version 2.16.5` |
| macainfo | `/opt/maca/bin/macainfo` | 输出设备拓扑（Agent 3 = `XCORE1000` / `MetaX C500`，vendor `METAX`） |
| mxvs | `/opt/maca/bin/mxvs` | 本机加载失败（缺 `libfuse.so.2`），记录为失败而非忽略 |
| mcProfiler | `/usr/local/bin/mcProfiler` | 本机缺 `.version` 文件，`version` 子命令报错；版本标记为未知 |

数学库（`/opt/maca/lib` → 实际 `/opt/maca-3.7.1/lib`）：

| 库 | 头文件 | 头文件版本宏 |
|----|--------|-------------|
| `libmcblas.so`, `libmcblasLt.so` | `/opt/maca/include/mcblas/{mcblas.h,mcblasLt.h,mcblasXt.h}` | `MCBLAS_VER_MAJOR 1`、`MCBLAS_VER_MINOR 0` |
| `libmccl.so` | `/opt/maca/include/mccl.h` | `MCCL_MAJOR 2`、`MCCL_MINOR 16`、`MCCL_PATCH 5`（`MCCL_VERSION_CODE 21605`） |
| `libmcdnn.so` | `/opt/maca/include/mcdnn/{mcdnn.h,mcdnn_cnn_infer.h,...}` | `MCDNN_MAJOR 1`、`MCDNN_MINOR 1`、`MCDNN_PATCHLEVEL 1` |

预编译内核镜像 `*.mcfb`（按设备架构分文件）：`mcblas_xcore1000.mcfb`、`mcblas_xcore1500.mcfb`、
`mcdnn_xcore1000_*.mcfb` 等。`macainfo` 显示本机 GPU 的 ISA 名为 `METAX-MXC-MXMACA--XCORE1000`，
市场名 `MetaX C500`——即 `xcore1000` 后缀对应 C500。

Python 侧：`torch 2.8.0+metax3.7.1.3`、`triton 3.0.0+metax3.7.1.3`；`tilelang` 无 pip 包，
但 `/opt/tilelang-metax-v0.1.10` 存在（见 `reference-mxmaca-triton-tilelang`）。

# 一次交叉验证

`mccl.h` 的宏给出 `2.16.5`，`mcclras` 工具自报 `MCCL RAS client version 2.16.5`。两个独立信号一致，
因此 mcCL 的版本证据记为 `corroborated`；其余组件为单信号，记为 `source-reported`。

# 证据边界（本页不主张）

- 库的存在与版本宏**不等于** API 兼容性或性能结论；本页只记录「装了什么、什么版本」。
- 未实际调用任何库的算子（尝试以 ctypes 调用 `mcblasGetVersion` 因需要有效 handle 而段错误，
  已放弃该路线），因此不产生任何功能正确性或性能主张。
- `mxvs` 与 `mcProfiler` 的失败被如实记录为失败，不解释为「未安装」。
- 上述路径与版本针对 MACA 3.7.1.5 安装；其他版本需重新捕获。
