---
{
  "id": "reference-mctilelang-basics",
  "title": "TileLang（MetaX 构建）安装证据与边界",
  "type": "wiki-tool",
  "status": "reviewed",
  "summary": "TileLang 的 MetaX 构建在 C500 上以 /opt/tilelang-metax-v0.1.10 目录安装，但不在 Python 环境中。本页记录实测布局与证据强度的特殊之处。",
  "languages": ["zh-CN"],
  "tags": ["installation", "kernel", "operator-evaluation", "compatibility"],
  "hardware": ["c500"],
  "mxmaca_versions": ["3.7.1.5"],
  "components": ["mctilelang", "tilelang", "mxmaca-sdk"],
  "sources": ["local-c500-maca-sdk-install"],
  "related": ["evaluation-compare-operator-backends", "kernel-flash-attention-mxmaca", "recipe-verify-mxmaca-environment", "reference-mxcc-compiler-basics"],
  "prerequisites": ["recipe-verify-mxmaca-environment"],
  "verified_at": "2026-09-14",
  "confidence": "source-reported",
  "reproducibility": "procedure",
  "aliases": ["TileLang", "tilelang", "mcTileLang", "TileLang MetaX 构建", "/opt/tilelang-metax"]
}
---

# 概述

TileLang 是一个用于编写高性能算子的领域特定语言（DSL），可面向包括 MXMACA 在内的多种后端生成代码。在 C500 上它以 MetaX 构建的形式安装，但安装形态比较特殊，值得单独记录。

> ✅ **证据状态**：本页的安装证据来自 2026-09-14 在 MetaX C500（MACA 3.7.1.5）上的实测，可复现产物见 `benchmarks/results/environment-c500-components.json`（hostname 已脱敏）。

## 实测安装布局（MACA 3.7.1.5 / C500）

| 项 | 值 |
|----|----|
| 安装目录 | `/opt/tilelang-metax-v0.1.10`（**版本化目录名**） |
| pip 包 | **不存在**（`importlib.metadata` 查不到 `tilelang`） |
| 可导入性 | `import tilelang` 失败（`ModuleNotFoundError`） |
| 版本来源 | 目录名中的 `v0.1.10`；`pyproject.toml` 声明 `dynamic = ["version"]`，未静态写死版本 |

## 证据强度的特殊性（本页最重要的一节）

TileLang 的版本号 `0.1.10` **只能从安装目录名读到**，无法从包元数据读到（因为根本没有安装成 pip 包）。这与本 cluster 其他组件形成对比：

| 组件 | 版本证据来源 | 强度 |
|------|-------------|------|
| mcCL | 头文件宏 + 工具自报，两者一致 | corroborated |
| mcBLAS / mcDNN | 头文件宏（单一来源） | source-reported |
| TileLang | **安装目录名**（无包元数据、不可导入） | source-reported |

因此：

- `confidence` 记为 `source-reported`，不升级。
- 「目录存在」**不等于**「可用」。没有 import 成功，就不能主张任何功能正确性或代码生成能力。
- 若要真正使用它，需要先解决「如何把这个目录形式的安装接入 Python 环境」（例如设置 `PYTHONPATH` 或按其文档安装），这一步本页**未做**，也不假装已做。

## 与 MXMACA++ / mcTileLang 的关系

本页不把上游 TileLang 的文档能力清单当作 MetaX 构建的事实。`kernel-flash-attention-mxmaca` 记录了一个具体例证：mcTileLang 的 FlashAttention 示例 PR 在检索时处于冲突状态，且并非 MXMACA flash_attn wheel 的来源。即：**上游仓库的示例存在，不等于它在 MetaX 构建上可用**。

## 使用注意事项

- 不要从 CUDA 版 TileLang 的行为推断 MXMACA 行为，需 MXMACA 特定证据。
- 若使用 TileLang 生成 MXMACA 代码，产物仍需在目标硬件与版本上验证（见 `evaluation-compare-operator-backends` 的正确性/性能契约）。
- 版本随安装目录走，升级或切换版本会改变目录名；引用时建议写明完整目录名而非 `/opt/tilelang-metax`（该非版本化路径在本机**不存在**）。

## 复现方式

```bash
ls -d /opt/tilelang-metax*                 # 版本化目录
python3 -c "import importlib.metadata as m; print(m.version('tilelang'))"  # 预期：PackageNotFoundError
python3 -c "import tilelang"               # 预期：ModuleNotFoundError
```
