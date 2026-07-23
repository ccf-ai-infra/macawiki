---
{
  "id": "repo-mcpytorch",
  "title": "mcPyTorch",
  "type": "source-repo",
  "status": "draft",
  "summary": "MetaX-maintained PyTorch distribution for MXMACA hardware, providing MXMACA backend support through the torch.cuda device namespace.",
  "languages": ["en"],
  "tags": ["framework", "installation"],
  "hardware": ["c500"],
  "mxmaca_versions": ["unspecified"],
  "components": ["mcpytorch", "mxmaca-sdk"],
  "sources": [],
  "related": ["doc-pytorch-operator-reference"],
  "verified_at": "2026-07-22",
  "url": "https://gitee.com/metax-maca",
  "repo": "metax-maca/mcpytorch",
  "ref": "unspecified",
  "source_category": "official-repo",
  "retrieved_at": "2026-07-22",
  "license_status": "unknown",
  "aliases": ["MetaX PyTorch", "mcPyTorch repo"]
}
---

# 来源摘要

mcPyTorch 是 MetaX 维护的 PyTorch 发布版本，提供 MXMACA 后端支持，通过 `torch.cuda` 设备命名空间暴露 MXMACA 硬件功能。本页仅记录公开仓库入口和主题范围。

## 可支持的结论

- mcPyTorch 映射到 torch.cuda 设备命名空间。
- 与上游 PyTorch 的版本兼容性需 MXMACA 特定验证。

## 限制

- 未获取特定 commit/release 的代码内容（license 未知）。
- 版本范围标记为 `unspecified`。
- 不能由此推断与所有上游 PyTorch 版本的兼容性。
