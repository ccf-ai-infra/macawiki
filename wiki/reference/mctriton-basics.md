---
{
  "id": "reference-mctriton-basics",
  "title": "Triton（MetaX 构建）安装证据与边界",
  "type": "wiki-tool",
  "status": "reviewed",
  "summary": "Triton 的 MetaX 构建以 pip 包形式装在 C500 的 Python 环境中，版本 3.0.0+metax3.7.1.3。本页区分「装得上」与「功能已验证」。",
  "languages": ["zh-CN"],
  "tags": ["installation", "kernel", "operator-evaluation", "compatibility"],
  "hardware": ["c500"],
  "mxmaca_versions": ["3.7.1.5"],
  "components": ["mctriton", "mxmaca-sdk", "mxmaca-runtime"],
  "sources": ["local-c500-maca-sdk-install"],
  "related": ["reference-mctilelang-basics", "evaluation-compare-operator-backends", "recipe-verify-mxmaca-environment", "reference-mxcc-compiler-basics"],
  "prerequisites": ["recipe-verify-mxmaca-environment"],
  "verified_at": "2026-09-14",
  "confidence": "source-reported",
  "reproducibility": "procedure",
  "aliases": ["Triton", "triton", "mcTriton", "Triton MetaX 构建", "MXMACA Triton"]
}
---

# 概述

Triton 是一个用于编写 GPU 算子的语言与编译器，可通过 `tt` DSL 生成设备代码。MXMACA 侧存在一个 MetaX 构建的 Triton 发行版，供 PyTorch 生态在 MXMACA 硬件上生成算子。

> ✅ **证据状态**：本页的安装证据来自 2026-09-14 在 MetaX C500（MACA 3.7.1.5）上的实测，可复现产物见 `benchmarks/results/environment-c500-components.json`（hostname 已脱敏）。版本号来自包元数据，不是文档转录。

## 实测安装布局（MACA 3.7.1.5 / C500）

| 项 | 值 |
|----|----|
| pip 包 | `triton` 已安装 |
| 版本 | `3.0.0+metax3.7.1.3`（来自 `importlib.metadata`） |
| 伴随包 | `torch 2.8.0+metax3.7.1.3`（同套构建） |

版本串中的 `+metax3.7.1.3` 是本地版本标签，说明这是与 MXMACA 3.7.1.x 配套的构建，不是上游 `triton 3.0.0`。这一点很关键：**它的版本号与上游同名，但构建不同**。

## 与 TileLang 的证据强度对比

同为「DSL/算子生成」生态，两者在本机的证据强度差别很大：

| 组件 | 是否 pip 包 | 可导入 | 版本来源 |
|------|------------|--------|---------|
| Triton | 是 | 是 | 包元数据（可信） |
| TileLang | 否（目录安装） | 否 | 安装目录名（弱） |

因此 Triton 的安装证据比 TileLang 更可靠。但**两者都不能据此主张功能正确性**：导入成功只证明包完整，不证明任意算子在 C500 上生成正确代码。

## 「装得上」≠「功能已验证」

本页明确区分两个层级：

- **已验证**：包已安装、版本可读、可导入。本页主张到此为止。
- **未验证**：任何具体的代码生成、算子正确性、性能表现。本页**不主张**，也未运行任何 Triton kernel。

若要用 Triton 写 MXMACA 算子，产物仍需按 `evaluation-compare-operator-backends` 的契约验证（同输入、同语义、正确性门先行，性能结果带完整环境元数据）。

## 使用注意事项

- 不要从 CUDA 版 Triton 的行为（语言语义、后端支持、已知 bug）推断 MXMACA 行为，需 MXMACA 特定证据。
- 上游 Triton 文档可作为语法参考，但**后端能力与代码生成结果**必须以 MXMACA 构建上的实测为准。
- 版本串中的 `+metax` 后缀会随 MXMACA 版本变化；引用时应写完整串（`3.0.0+metax3.7.1.3`）而非只写 `3.0.0`，否则会与上游构建混淆。

## 复现方式

```bash
python3 -c "import importlib.metadata as m; print(m.version('triton'))"
# 预期：3.0.0+metax3.7.1.3
python3 -c "import triton; print(triton.__version__ if hasattr(triton,'__version__') else 'imported, no __version__')"
```
