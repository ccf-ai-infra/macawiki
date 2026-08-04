---
{
  "id": "repo-flash-attention-v2-6-3",
  "title": "上游 FlashAttention v2.6.3",
  "type": "source-repo",
  "status": "reviewed",
  "summary": "固定上游 FlashAttention v2.6.3 的算法、API、测试语义和许可证范围，不把 CUDA/ROCm 事实外推为 MXMACA 支持。",
  "languages": ["zh-CN", "en"],
  "tags": ["attention", "kernel", "correctness", "compatibility", "benchmark"],
  "hardware": ["unspecified"],
  "mxmaca_versions": ["unspecified"],
  "components": ["flash-attn", "pytorch"],
  "sources": [],
  "related": ["kernel-flash-attention-mxmaca"],
  "verified_at": "2026-07-31",
  "url": "https://github.com/Dao-AILab/flash-attention/commit/418d677192b483dfc1decfdf9aadca40b402485d",
  "repo": "Dao-AILab/flash-attention",
  "ref": "v2.6.3@418d677192b483dfc1decfdf9aadca40b402485d",
  "source_category": "upstream-code",
  "retrieved_at": "2026-07-31",
  "license_status": "permissive",
  "aliases": ["FlashAttention 2.6.3", "flash-attn v2.6.3", "flash_attn 2.6.3"]
}
---

# 来源摘要

上游 release `v2.6.3` 指向 commit `418d677192b483dfc1decfdf9aadca40b402485d`。固定版本 README 将项目描述为 FlashAttention 和 FlashAttention-2 的官方实现，并给出 `flash_attn_func`、packed/varlen 接口和 `flash_attn_with_kvcache` 等 API 的输入、输出与行为说明。

该版本公开说明涵盖 causal mask、变长序列、滑动窗口、ALiBi、MQA/GQA、paged KV cache 和 forward/backward 等测试维度。它适合作为语义定义、测试用例设计和 PyTorch reference 对照的上游基线；具体函数的限制仍应以固定 ref 下的接口和测试为准。

# 平台范围

v2.6.3 README 的安装与硬件说明面向 CUDA/NVIDIA 路径，并另列 ROCm 路径；它没有声明 MetaX C500 或 MXMACA 支持。因此，上游安装命令、支持的 dtype/head dimension、性能图表和 GPU 结论都不能直接作为 C500/MXMACA 事实。

上游版本号与用户环境中的 `2.6.3+metax...` 只能说明存在相同的基础版本字符串，不能证明二进制没有供应方补丁、采用相同 ABI、覆盖相同功能或可由该 commit 复现。

# 许可证与采集边界

固定 ref 下的根许可证为 BSD-3-Clause。Macawiki 只保存来源元数据和原创摘要，不复制上游代码或大段文档；仓库内嵌第三方目录仍需分别核对许可证。
