---
{
  "id": "reference-ecosystem-port-status",
  "title": "C500 开源生态移植状态（实测）",
  "type": "wiki-framework",
  "status": "draft",
  "summary": "MXMACA C500 上开源推理栈的实际版本与缺口：哪些库有 metax 移植版、版本代差有多大、第三方框架如何误判硬件。用于推理框架适配与优化前的可行性判断。",
  "languages": ["zh-CN"],
  "tags": ["compatibility", "installation", "framework", "migration", "diagnostics"],
  "hardware": ["c500"],
  "mxmaca_versions": ["3.7.1.5"],
  "components": ["mcpytorch", "mctriton", "mctilelang", "flash-attn", "sglang", "mxmaca-sdk", "mxmaca-runtime"],
  "sources": ["local-c500-maca-sdk-install", "repo-mcpytorch"],
  "related": ["repo-mcpytorch", "reference-mctriton-basics", "local-c500-maca-sdk-install"],
  "confidence": "source-reported",
  "reproducibility": "runnable",
  "verified_at": "2026-09-16",
  "prerequisites": ["local-c500-maca-sdk-install", "repo-mcpytorch"]
}
---

# C500 开源生态移植状态

本页记录 **2026-09-16** 在一台 MetaX C500（MACA 3.7.1.5 / 驱动 3.8.30 / mx-smi 2.3.1）上实测的
开源推理栈状态。所有版本号来自本机 `importlib.metadata` 或库自报，不从文档推断。

## 为什么需要这一页

MXMACA 原生组件（mcBLAS/mcCL/mcDNN 等）在 `local-c500-maca-sdk-install` 里已有记录，
但**在 C500 上跑开源推理框架时，实际打交道的是移植到 MXMACA 的开源库**：flashinfer、
flash-attn、triton、以及上层的 sglang/vllm。这些库的移植深度参差，版本代差是适配工作中
最高频的失败来源，此前语料中没有任何一条记录。

## 核心事实：硬件如何被上层看到

这是理解所有后续行为的关键。

| 探测项 | 实测值 |
|--------|--------|
| `torch.cuda.is_available()` | `True` |
| `torch.cuda.get_device_name(0)` | `MetaX C500` |
| `torch.cuda.get_device_capability(0)` | `(8, 0)` → sm_80 |
| `torch.cuda.get_arch_list()` | `['sm_80']` |
| `torch.version.cuda` | `11.6`（兼容层，非 NVIDIA 驱动） |
| `torch.__version__` | `2.8.0+metax3.7.1.3` |

**含义**：mcPyTorch 通过 `torch.cuda` 命名空间暴露设备。任何用 `torch.cuda` API 检测硬件
的第三方框架，会把 C500 判定为**一张 sm_80 / CUDA 11.6 的 NVIDIA GPU**。这不是缺陷，是
MXMACA 的兼容层设计；但它有两个具体后果，见下节。

## 生态库移植状态

| 库 | 本机版本 | 上游对应版本 | 移植状态 |
|----|----------|------------|----------|
| `flashinfer` | `0.2.6+metax3.7.1.3torch2.8` | 上游已到 0.6.x | **有 metax 移植，但停在旧 API 线** |
| `flash_attn` | `2.6.3` (无 `.cute` 子包) | 上游 cu 路径含 `flash_attn.cute` | 部分移植，缺 cute 子包 |
| `triton` | `3.0.0` | — | 可用，metax 构建 |
| `sgl_kernel`（`sglang-kernel`） | 无 metax 版 | 上游 0.4.6 | **未移植**，PyPI wheel 仅供 sm90/sm100 |
| `sglang` | 无 metax 版 | 上游 0.5.19 | 上游 wheel 可 import（见下） |
| `sglang-omni` | 无 metax 版 | 上游 0.1.5 | 上游 wheel 可 import |

### flashinfer 的版本代差（最常见的坑）

本机 `flashinfer` 是 metax 移植版 `0.2.6`，而依赖它的框架（如 sglang 0.5.19）按上游
`0.6.18` 的 API 编写。实测缺失的符号包括：

- `flashinfer.fp4_quantization`（整个子模块不存在）
- `flashinfer.bmm_fp8`、`flashinfer.bmm_fp8_batched`（顶层函数）
- `flashinfer.fused_moe.convert_to_block_layout`、`trtllm_mxint4_block_scale_moe`

metax 0.2.6 实际存在的子模块：`activation`、`aot`、`cascade`、`decode`、`fused_moe`、
`gemm`、`jit`、`mla`、`norm`、`page`、`prefill`、`quantization`、`rope`、`sampling`、
`sparse`、`triton`、`utils`。

**含义**：任何按上游新 API 编写的 fp4/fp8 量化路径，在本机会因 `ImportError` 在 import 时
失败；而 bf16 路径通常不受影响。**这不是「不支持」，而是移植版本滞后**，可以通过补齐 metax
构建解决。

### sgl_kernel 未移植的硬约束

`sglang-kernel` 的 PyPI wheel 只编译了 `sm90`/`sm100` 二进制，且链接 `libnvrtc.so.13`
（CUDA 13）。本机是 sm_80 / CUDA 11.6，因此该 wheel **无法加载**，import 时报
`Could not load any common_ops library`。

注意：**PyPI 上无 metax 构建的 sgl_kernel**。要让 sglang 的量化/算子路径在本机真正可用，
需要一个 sm80 + CUDA 11.6 的 metax 构建，这是编译工作，不是配置工作。

## 第三方框架的实际行为

实测 `sglang==0.5.19` 与 `sglang-omni==0.1.5`（PyPI 上游 wheel，非 metax 版）在本机：

| 检查点 | 结果 |
|--------|------|
| `import sglang` | 成功（兼容 torch 2.8） |
| `sglang.srt.platforms.current_platform` | 解析为 `CudaSRTPlatform` |
| `current_platform.is_cuda()` | `True`（因 MXMACA 暴露 `torch.cuda`） |
| `sgl-omni --help` / `check-gpu` | 可运行，正确识别 `MetaX C500` |
| `sgl-omni config export`（本地 Qwen3-TTS 权重） | 可解析出 3 阶段流水线 |
| `sgl-omni serve` 流水线启动 | Coordinator 与 stage worker 可启动 |

**结论**：`sglang`/`sglang-omni` 的上游 wheel 在 MXMACA 上**可 import、可启动**。
README 中未提及 MXMACA，不代表不能跑——平台抽象层通过 `torch.cuda` 把 C500 当作 CUDA 卡。

**这也说明一个检索陷阱**：判断「某框架是否支持 MXMACA」不能只看上游 README 的硬件支持表。
MXMACA 是 CUDA-compatible stack，上游可能根本不知道自己被支持。判断依据应是本机实测。

## 兼容层的两个具体后果

1. **`if is_cuda():` 守卫无法区分真 NVIDIA 与 MXMACA**。框架中形如
   `if is_cuda(): from flashinfer import bmm_fp8` 的导入是**无条件的**——因为 `is_cuda()`
   在本机恒为 `True`。设置 `SGLANG_IS_FLASHINFER_AVAILABLE=false` **不会**跳过这类导入，
   守卫是平台判断，不是可用性判断。
2. **`check-gpu` 类自检会把慢 import 误报为不可用**。metax `flashinfer` 首次 import 约
   **23 秒**（torch JIT 扫描所有 arch），超过 sglang-omni `check-gpu` 内部 30 秒超时，
   于是该工具把 flashinfer 报为 "module unavailable"——实际可用，只是慢。
   设 `TORCH_CUDA_ARCH_LIST="8.0"` **不能**加快（实测无效），需用更长的超时。

## 证据边界（本页不主张）

- 本页只记录**装了什么、什么版本、缺什么符号**。不主张任何 API 兼容性、性能或正确性结论。
- 上层框架（sglang-omni 等）的**端到端模型推理未验证**：卡在 `qwen-tts` 包与
  `transformers` 的版本 pin 冲突（qwen-tts 锁 4.57.3，sglang 锁 5.12.1，本机是 5.8）。
  这是依赖解析问题，不是 MXMACA 兼容问题。
- `sgl_kernel` 的"未移植"结论仅针对 PyPI 公开 wheel；不排除存在内部 metax 构建。
- 所有版本针对 MACA 3.7.1.5 安装；其他版本需重新捕获。

## 如何复现

```bash
python3 -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.get_device_capability(0))"
python3 -c "import flashinfer; print(flashinfer.__version__)"
python3 -c "import triton, flash_attn; print(triton.__version__, flash_attn.__version__)"
# 平台判断（需已 pip install --no-deps sglang==0.5.19）
python3 -c "from sglang.srt.platforms import current_platform; print(type(current_platform).__name__, current_platform.is_cuda())"
```

## 相关页面

- `local-c500-maca-sdk-install` — MXMACA 原生组件实测（mcBLAS/mcCL/mcDNN/mxcc/mcTracer）
- `repo-mcpytorch` — mcPyTorch，本页 torch 版本事实的来源
- `reference-mxmaca-triton-tilelang` — TileLang/triton 在 C500 上的状态
