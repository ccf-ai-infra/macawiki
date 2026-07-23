# 基础版本迭代计划

## Iteration 1 — v0.1 corpus foundation（已完成）

- 建立 `sources/wiki/queries/data` 分层。
- 提供 JSON-compatible YAML schema、词表、验证器和生成索引。
- 加入最小公开来源、查询脚本和回归测试。

退出条件：页面、引用、词表和生成索引可离线验证。

## Iteration 2 — v0.2 dual-agent packaging（已纳入 v0.3）

- 加入 Codex 与 Claude Code 仓库级适配器。
- 加入用户级/项目级 copy 与 symlink 安装器。
- 加入 doctor、安装、升级、回退与使用文档。

退出条件：临时目录内可完成两类 Agent 的安装测试，已有目标默认不覆盖。

## Iteration 3 — v0.3 evaluation-ready foundation（已完成）

- 选择 PyTorch 已实现的 add、softmax、layer_norm、matmul 作为基线案例。
- 定义统一输入、正确性、计时、环境和结果 schema。
- 提供 PyTorch runner、TileLang/MXMACA++ 后端契约与比较器。
- 提供 Agent 价值离线演练，明确“检索可验证”与“模型质量评估”的边界。

退出条件：无 C500 环境也能完整审阅和测试流程；所有硬件结果为 `not_run`。
（注：Iteration 4 已满足此条件 — C500 环境已就绪，7 个 case 均有状态记录。）

## Iteration 4 — C500 bring-up（已完成）

- 捕获驱动、MXMACA、编译器、框架、TileLang 和硬件信息。
- 已确认设备字符串、同步 API、编译命令和 MXMACA++ 头文件/API。
- 已完成 7 个 case 的正确性与计时实测：5 个 comparable（add, softmax, layer_norm, quantize, transpose），2 个 not_comparable（matmul codegen gap，moe_routing top-k 未支持）。
- 原始 JSON、日志、源码 commit 和运行命令已作为证据保存在 `benchmarks/results/`。

**C500 结果证据：**
- PyTorch 基线: `benchmarks/results/pytorch_c500.json`
- TileLang 候选: `benchmarks/results/tilelang_c500.json`
- 对比结果: `benchmarks/results/compare_pytorch_vs_tilelang_c500.json`

退出条件：PyTorch + TileLang 两后端在同机同栈下通过正确性门禁，生成可复现原始结果。 ✅
MXMACA++ 后端尚未接入（`not_run`）。

## Iteration 5 — community hardening（待开始）

- 用真实失败案例扩展 gold questions 和回归测试。
- 审核更多官方文档/仓库的许可证与版本范围。
- 根据稳定 API 将后端模板升级为可运行实现。
- 经人工审阅后才把实验结论提升为 `verified`。

**前置条件**：MXMACA++ SDK 环境就绪，Claude API 付费授权（用于 A/B 评测）。
