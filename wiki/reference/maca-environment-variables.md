---
{
  "id": "reference-maca-environment-variables",
  "title": "vLLM-MetaX cu-bridge 环境变量配置",
  "type": "wiki-tool",
  "status": "draft",
  "summary": "vLLM-MetaX 构建所需的 cu-bridge 环境变量配置（来源：vllm-metax/env.sh），覆盖 MACA_PATH、CUCC_PATH、CUDA_PATH 和库路径。",
  "languages": ["zh-CN"],
  "tags": ["installation", "compiler", "framework"],
  "hardware": ["c500"],
  "mxmaca_versions": ["unspecified"],
  "components": ["vllm-metax", "mxmaca-sdk", "mxcc"],
  "sources": ["repo-vllm-metax-env-sh"],
  "related": ["recipe-verify-mxmaca-environment", "reference-mxcc-compiler-basics", "repo-vllm-metax"],
  "prerequisites": ["recipe-verify-mxmaca-environment"],
  "verified_at": "2026-07-24",
  "confidence": "source-reported",
  "reproducibility": "snippet",
  "aliases": ["vLLM 环境变量", "cu-bridge 环境配置", "vLLM-MetaX env setup"]
}
---

# 概述

本页记录 **vLLM-MetaX** 构建时所需的环境变量配置，直接来源为 vLLM-MetaX 仓库根目录的 `env.sh`（commit `0bf07c51`，文件 blob `88b76bf4`，master，2026-07-24）。env.sh 自身未内嵌 MXMACA 版本号，随 vLLM 0.15.0 相关提交引入。

> ⚠️ **适用范围**：此配置面向 vLLM-MetaX 的 cu-bridge 构建场景，**不是通用 MACA 标准配置**。其他 MetaX 项目（如 mcPyTorch）可能使用不同的 `CUDA_PATH` 约定（例如 `CUDA_PATH=/opt/maca/tools/cu-bridge/`），使用时请核对具体项目的环境要求。

## 来源

`repo-vllm-metax-env-sh` — vLLM-MetaX `env.sh`（commit `0bf07c51`，blob `88b76bf4`），通过 Gitee API 获取并验证。

## 配置内容

vLLM-MetaX `env.sh` 定义以下变量（已去除脚本参数逻辑，使用默认值）：

```bash
# === MACA 根路径（默认 /opt/maca，可通过脚本参数覆盖）===
export MACA_PATH="/opt/maca"

# === cu-bridge（CUDA → MACA 编译转换层）===
export CUCC_PATH="${MACA_PATH}/tools/cu-bridge"
export CUDA_PATH="${HOME}/cu-bridge/CUDA_DIR"
export CUCC_CMAKE_ENTRY=2

# === 可执行文件搜索路径 ===
export PATH=${MACA_PATH}/mxgpu_llvm/bin:${MACA_PATH}/bin:${CUCC_PATH}/tools:${CUCC_PATH}/bin:${PATH}

# === 动态库加载路径 ===
export LD_LIBRARY_PATH=${MACA_PATH}/lib:${MACA_PATH}/ompi/lib:${MACA_PATH}/mxgpu_llvm/lib:${LD_LIBRARY_PATH}

# === vLLM Punica kernel 编译开关 ===
export VLLM_INSTALL_PUNICA_KERNELS=1
```

## 变量说明

| 变量 | 值 | 说明 |
|------|-----|------|
| `MACA_PATH` | `/opt/maca`（默认） | MACA 软件栈根目录，可通过 env.sh 的第一个参数覆盖 |
| `CUCC_PATH` | `${MACA_PATH}/tools/cu-bridge` | cu-bridge 工具链路径 |
| `CUDA_PATH` | `${HOME}/cu-bridge/CUDA_DIR` | cu-bridge 所需 CUDA 头文件/库（vLLM-MetaX 特定约定，不同于 mcPyTorch 的 `/opt/maca/tools/cu-bridge/`） |
| `CUCC_CMAKE_ENTRY` | `2` | cmake cu-bridge 入口模式 |
| `VLLM_INSTALL_PUNICA_KERNELS` | `1` | 启用 vLLM Punica kernel 编译 |
| `PATH` | 追加 4 个目录 | mxgpu_llvm/bin、MACA/bin、cu-bridge/tools、cu-bridge/bin |
| `LD_LIBRARY_PATH` | 追加 3 个目录 | MACA/lib、ompi/lib、mxgpu_llvm/lib |

## 验证方法

配置生效后，执行以下检查：

```bash
# 1. 变量生效
echo ${MACA_PATH}
echo ${CUCC_PATH}

# 2. 编译器可用
which mxcc && mxcc --version

# 3. LD_LIBRARY_PATH 覆盖的目录存在（env.sh 定义的加载路径）
test -d ${MACA_PATH}/lib      && echo "MACA/lib OK"
test -d ${MACA_PATH}/ompi/lib && echo "ompi/lib OK"
test -d ${MACA_PATH}/mxgpu_llvm/lib && echo "mxgpu_llvm/lib OK"

# 4. 运行时加载验证（需要 MACA 设备，不可用时退出码非零）
python3 -c "import sys, torch; sys.exit(0 if torch.cuda.is_available() else 1)"
```

> 注意：`ldconfig -p` 查询的是系统 `/etc/ld.so.cache`，**不能**证明当前 shell 的 `LD_LIBRARY_PATH` 已正确加载 MACA 库。步骤 3 检查 env.sh 定义的目录存在性（目录名来自来源），步骤 4 通过 PyTorch 验证运行时加载并在不可用时以非零退出码失败。

完整的 MXMACA 环境验证流程参见 `recipe-verify-mxmaca-environment`。

## 与其他项目的差异

| 场景 | CUDA_PATH | CUCC_PATH | 额外变量 | 来源 |
|------|-----------|-----------|----------|------|
| **vLLM-MetaX 构建** | `${HOME}/cu-bridge/CUDA_DIR` | `${MACA_PATH}/tools/cu-bridge` | `VLLM_INSTALL_PUNICA_KERNELS=1` | `repo-vllm-metax-env-sh` |
| **mcPyTorch Extension** | `/opt/maca/tools/cu-bridge/` | `/opt/maca/tools/cu-bridge/` | `MACA_CLANG_PATH` | mcPyTorch 官方指南 |

此页面仅覆盖 vLLM-MetaX 行。其他项目的环境配置请查阅对应来源。

## 注意事项

- `MACA_PATH` 默认 `/opt/maca`，按实际安装位置调整。
- `CUDA_PATH` 指向 cu-bridge 的 CUDA 目录，**不是**系统 CUDA（如 `/usr/local/cuda`）。
- 环境变量需在编译和运行前生效，建议通过项目级 env 脚本 source 而非写入 `~/.bashrc`。
- 编译器与运行时版本必须匹配，参见 `reference-mxcc-compiler-basics`。

## 限制

- 此配置来源为 vLLM-MetaX `env.sh`（commit `0bf07c51`，blob `88b76bf4`），未内嵌 MXMACA 版本号，随 vLLM 0.15.0 相关提交引入。版本标记为 `unspecified`。
- cu-bridge 路径约定可能在后续 MXMACA 或 vLLM-MetaX 版本中变更。
- **不适用于** mcPyTorch Extension 或其他 MetaX 项目的构建环境——这些项目有不同的 `CUDA_PATH` 约定。
