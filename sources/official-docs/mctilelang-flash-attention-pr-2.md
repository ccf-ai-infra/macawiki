---
{
  "id": "doc-mctilelang-flash-attention-pr-2",
  "title": "mcTileLang FlashAttention 示例 PR !2",
  "type": "source-doc",
  "status": "draft",
  "summary": "记录 mcTileLang PR !2 公开展示的 C500 FlashAttention 示例线索及其开放、冲突和未完成审核状态。",
  "languages": ["zh-CN", "en"],
  "tags": ["attention", "kernel", "correctness", "community", "documentation"],
  "hardware": ["c500"],
  "mxmaca_versions": ["unspecified"],
  "components": ["mctilelang"],
  "sources": [],
  "related": ["kernel-flash-attention-mxmaca"],
  "verified_at": "2026-07-31",
  "url": "https://gitee.com/metax-maca/mcTileLang/pulls/2",
  "source_category": "community-note",
  "retrieved_at": "2026-07-31",
  "license_status": "unknown",
  "aliases": ["mcTileLang PR 2", "mcTileLang flash_attention 示例", "example_mha_fwd_bshd_extended.py"]
}
---

# 来源摘要

公开 PR !2 的标题为“Level 3 文档开发-flash_attention算子文档编写”。PR 描述称示例曾在 `mcTileLang` 镜像与“曦云 C500-64GB”加速卡上执行，完整代码位于提交分支的 `examples/flash_attention/example_mha_fwd_bshd_extended.py`，并展示了默认参数及 `scale`、`causal` 等可选参数的运行截图。

# 状态与证据边界

在 2026-07-31 回看时，该 PR 状态为 Open、conflicted，reviewer/tester 审核仍在进行，页面明确显示不能自动合并。因此它只能作为 `experimental` 的 mcTileLang 示例和后续测试候选，不能视为已发布能力、性能结论或生产支持。

该 PR 也不是 `flash_attn 2.6.3+metax...` wheel 的对应源码。示例存在、在某次环境中运行过和二进制包的来源/功能完整性是三个不同命题，必须分别取证。

# 许可限制

本次采集没有从 PR 页面确认示例文件的适用许可证和可再分发边界。Macawiki 因此仅保存页面链接、状态和原创摘要，不复制代码、patch 或截图。
