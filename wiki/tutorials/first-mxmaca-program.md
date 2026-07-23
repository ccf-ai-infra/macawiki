---
{
  "id": "tutorial-first-mxmaca-program",
  "title": "编写并验证第一个 MXMACA 程序",
  "type": "wiki-recipe",
  "status": "draft",
  "summary": "从零开始构建、编译并运行一个最简 MXMACA 程序，验证开发环境可用性。",
  "languages": ["zh-CN"],
  "tags": ["quick-start", "programming-model", "installation"],
  "hardware": ["unspecified"],
  "mxmaca_versions": ["3.7.1.5"],
  "components": ["mxmaca-sdk", "mxmaca-runtime", "mxcc"],
  "sources": ["doc-mxmaca-quick-start", "doc-mxmaca-programming-model"],
  "related": ["recipe-verify-mxmaca-environment"],
  "prerequisites": ["recipe-verify-mxmaca-environment"],
  "verified_at": "2026-07-22",
  "confidence": "source-reported",
  "reproducibility": "procedure",
  "aliases": ["第一个程序", "MXMACA hello world"]
}
---

# 流程

1. 确认 MXMACA SDK、运行时和 mxcc 编译器已安装。
2. 编写一个简单的向量加法 kernel（MACA C 或通过 PyTorch 调用）。
3. 使用 mxcc 或 PyTorch 构建并运行。
4. 验证输出结果的正确性。

## 最小验证示例

可通过 PyTorch 快速验证 MXMACA 环境：

```python
import torch
# 确认 MACA 设备可见
print(torch.cuda.is_available())  # MXMACA PyTorch maps to cuda device
```

具体的 MACA C kernel 示例和 mxcc 编译参数因版本而异，必须查阅当前安装版本的官方文档。

## 限制

- 本页不提供可直接运行的完整 kernel 代码（API 因版本而异）。
- 不承诺 `torch.cuda.is_available()` 的返回值在当前或未来 MXMACA 版本中保持一致。
- 使用前必须根据官方文档核对该版本的真实 API。
