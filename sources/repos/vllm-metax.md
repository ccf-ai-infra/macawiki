---
{
  "id": "repo-vllm-metax",
  "title": "vLLM-MetaX",
  "type": "source-repo",
  "status": "draft",
  "summary": "MetaX-maintained vLLM fork providing LLM inference serving on MXMACA hardware, enabling large language model deployment on C500.",
  "languages": ["en"],
  "tags": ["framework", "installation", "performance"],
  "hardware": ["c500"],
  "mxmaca_versions": ["3.7.1.5"],
  "components": ["vllm-metax", "mxmaca-sdk", "mcpytorch"],
  "sources": [],
  "related": ["repo-mcpytorch"],
  "verified_at": "2026-07-22",
  "url": "https://gitee.com/metax-maca",
  "repo": "metax-maca/vllm-metax",
  "ref": "unspecified",
  "source_category": "official-repo",
  "retrieved_at": "2026-07-22",
  "license_status": "permissive",
  "aliases": ["MetaX vLLM", "vLLM MACA"]
}
---

# 来源摘要

vLLM-MetaX 是 MetaX 维护的 vLLM 分支，提供在 MXMACA C500 硬件上的大语言模型推理服务。本页仅记录公开仓库入口和主题范围。仓库许可证为 Apache-2.0。

## 可支持的结论

- vLLM-MetaX 支持在 MXMACA C500 上部署 LLM 推理。
- 依赖 mcPyTorch 和 MXMACA SDK。

## 限制

- 未获取特定 commit/release 的代码内容。
- 版本范围和性能数据标记为 `unspecified`。
- 不能由此推断与上游 vLLM 的 API 兼容性。
