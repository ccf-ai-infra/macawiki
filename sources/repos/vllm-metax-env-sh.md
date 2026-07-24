---
{
  "id": "repo-vllm-metax-env-sh",
  "title": "vLLM-MetaX env.sh — cu-bridge 环境配置",
  "type": "source-repo",
  "status": "draft",
  "summary": "vLLM-MetaX 仓库根目录 env.sh，提供 MACA_PATH、CUCC_PATH (cu-bridge)、编译标志和库路径的默认配置。",
  "languages": ["en"],
  "tags": ["installation", "compiler"],
  "hardware": ["c500"],
  "mxmaca_versions": ["unspecified"],
  "components": ["vllm-metax", "mxmaca-sdk", "mxcc"],
  "sources": [],
  "related": ["repo-vllm-metax"],
  "verified_at": "2026-07-24",
  "url": "https://gitee.com/metax-maca/vLLM-metax",
  "repo": "metax-maca/vLLM-metax",
  "ref": "commit 0bf07c51d32f24eb3a2adecf50476260f589db9c (env.sh blob 88b76bf4, master, 2026-07-24)",
  "source_category": "official-repo",
  "retrieved_at": "2026-07-24",
  "license_status": "permissive",
  "aliases": ["vLLM-MetaX env.sh", "vLLM 环境脚本", "cu-bridge env"]
}
---

# 来源摘要

`env.sh` 位于 vLLM-MetaX 仓库根目录，提供构建和运行 vLLM-MetaX 所需的环境变量默认值。文件内容通过 Gitee API 获取，对应 commit `0bf07c51`（文件 blob SHA `88b76bf4`），随 vLLM 0.15.0 相关提交引入。env.sh 自身未内嵌 MXMACA 版本号。

## 文件内容（master, 2026-07-24）

```bash
# setup MACA path
DEFAULT_DIR="/opt/maca"
export MACA_PATH=${1:-$DEFAULT_DIR}

# cu-bridge
export CUCC_PATH="${MACA_PATH}/tools/cu-bridge"
export CUDA_PATH="${HOME}/cu-bridge/CUDA_DIR"
export CUCC_CMAKE_ENTRY=2

# update PATH
export PATH=${MACA_PATH}/mxgpu_llvm/bin:${MACA_PATH}/bin:${CUCC_PATH}/tools:${CUCC_PATH}/bin:${PATH}
export LD_LIBRARY_PATH=${MACA_PATH}/lib:${MACA_PATH}/ompi/lib:${MACA_PATH}/mxgpu_llvm/lib:${LD_LIBRARY_PATH}

export VLLM_INSTALL_PUNICA_KERNELS=1
```

## 可支持的结论

- vLLM-MetaX 构建依赖 cu-bridge（`CUCC_PATH`、`CUDA_PATH`、`CUCC_CMAKE_ENTRY`）。
- 默认 MACA 安装路径为 `/opt/maca`，可通过脚本参数或直接设置 `MACA_PATH` 覆盖。
- vLLM-MetaX 需要 `VLLM_INSTALL_PUNICA_KERNELS=1` 编译 Punica kernel。

## 不能支持的结论

- 此 env.sh 不是通用 MXMACA 标准配置，仅适用于 vLLM-MetaX 的 cu-bridge 构建场景。
- 其他 MetaX 项目（如 mcPyTorch）可能有不同的 `CUDA_PATH` 约定（例如 `CUDA_PATH=/opt/maca/tools/cu-bridge/`）。
- 不能由此推断所有 MXMACA 项目的环境变量设置方式。
