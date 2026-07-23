# 评估方法

本文档定义 Macawiki 的评估框架，分为两个层次：
- **第 1 层**：确定性检索与证据代理测试（无 LLM 调用，每次提交自动运行）
- **第 2 层**：真实 Agent A/B 评估（需 Claude API 付费授权，按主要版本发布运行）

---

## 1. 两层评估体系

| 维度 | 第 1 层：确定性检索代理 | 第 2 层：Agent A/B 评估 |
|------|------------------------|------------------------|
| 测量什么 | 仓库是否提供正确的证据 | 加载 Macawiki 是否改善 Agent 回答 |
| 自动化程度 | 全自动（CI） | 半自动（需 API 调用） |
| 成本 | 免费 | API 费用 |
| 频率 | 每次提交 | 每个主要版本 |
| 评分方式 | 确定性匹配 | 人工审阅或 LLM-as-judge |

**核心原则：** 代理检索命中率只能证明索引可检索，不能替代真实 Agent A/B 结论。C500 性能对比必须先通过正确性检查，并确保设备、软件栈、shape、dtype、预热与计时方法一致。

---

## 2. 第 1 层：确定性检索与证据代理测试

### 2.1 Agent Value Cases

**位置**：`evals/agent-value-cases.yaml`（schema version 1）

**当前覆盖**：9 个 case（7 个正向检索 + 2 个负向触发）

| 类别 | 数量 | 行为 |
|------|------|------|
| 正向检索 (positive_retrieval) | 7 | 预期页面和来源必须被找到 |
| 负向触发 (negative_trigger) | 2 | 非 MXMACA 或隐私信息 Prompt 不得返回任何 Macawiki 页面 |

**运行方式**：

```bash
python3 scripts/run_agent_value_eval.py
# 预期: 9/9 passed
```

**指标**：
- `loaded_pass`：case 是否通过（布尔值）
- `expected_pages_found` vs `expected_pages_missing`：命中与缺失的预期页面
- `missing_sources`：预期来源中未在目标页面找到的部分
- `missing_content`：`must_contain` 项未在目标页面文本中找到的部分
- `forbidden_found`：`must_not_contain` 项在 corpus 中被找到（严重违规）

**通过标准**：所有 case 必须通过（`all_passed: true`），CI 才会标绿。

### 2.2 Gold Questions

**位置**：`evals/gold-questions.yaml`

**当前覆盖**：7 个问题，覆盖 5 个领域：

| 领域 | 示例问题 | 预期页面 |
|------|---------|---------|
| 环境验证 | MXMACA 环境就绪检查 | recipe-verify-mxmaca-environment |
| 性能基线 | C500 算子基线条件 | pattern-establish-performance-baseline |
| 算子评估 | 三后端对比方案 | evaluation-compare-operator-backends |
| 编译器 | mxcc 编译基础 | reference-mxcc-compiler-basics |
| 性能分析 | mcProfiler 使用 | diagnostics-mcprofiler-basics |
| 证据不足 | MXMACA++ BLAS 状态 | 多页面 + 边界声明 |

### 2.3 Contract Tests

**位置**：`tests/test_repository.py`

**当前覆盖**：38 个单元测试，覆盖：
- 页面验证、查询、别名过滤、来源跟踪
- compare_benchmarks 合约（18 个测试：schema、contract、timing、exit codes）
- transpose 工作负载合约（3 个测试）
- 证据完整性（8 个测试：版本声明、禁止伪造数字、来源 URL、agent-value 等）

### 2.4 添加新 Case

1. 在 `evals/agent-value-cases.yaml` 或 `evals/gold-questions.yaml` 中添加条目
2. 定义：prompt、terms、expected_pages、required_sources、must_contain、must_not_contain
3. 负向 case 设置 `expected_pages: []` 并在 `id` 中使用 `negative` 前缀
4. 运行 `python3 scripts/run_agent_value_eval.py` 确认通过
5. 如 case 数阈值变化，更新 `tests/test_repository.py` 中的断言

### 2.5 局限

- 使用确定性关键词搜索（AND 语义），不模拟 LLM 的语义理解
- 仅验证"索引可检索"，不测量答案质量
- 不能替代真实 Agent A/B 评测

---

## 3. 第 2 层：Agent A/B 评估

> ⚠️ **状态**：已弃用（wontfix）。Macawiki 定位于本地 Agent CLI 工作流（Claude Code、Codex、OpenCode），付费 API A/B 评估不在此架构范围内。第 1 层确定性检索代理已提供充分的证据质量测量。

### 3.1 评估协议

**A 组（控制组）**：Agent 不加载 Macawiki Skill
**B 组（实验组）**：同一 Agent 加载 Macawiki Skill

| 参数 | 约束 |
|------|------|
| 模型 | 固定（同一模型用于所有运行） |
| 客户端版本 | 锁定（`pip freeze` 随结果记录） |
| 工具权限 | A/B 组相同 |
| 上下文窗口 | 固定值 |
| 最大输出 Token | 固定值 |
| 最长时间 | 记录每次运行的实际用时 |
| API Key | 同等级别 |

### 3.2 任务集

| 任务领域 | 说明 | 示例问题 |
|---------|------|---------|
| 安装与配置 | 环境验证、SDK 设置 | "怎样验证 MXMACA 开发环境？" |
| MXMACA 术语/架构 | 编译器、运行时、性能分析概念 | "mxcc 的主要作用和编译流程是什么？" |
| 算子实现/适配 | PyTorch/TileLang/MXMACA++ 实现计划 | "如何用 PyTorch 做算子 baseline？" |
| 上下游生态项目 | mcPytorch、vLLM-MetaX 集成 | "vllm-metax 的版本要求是什么？" |
| 评测设计 | 基准测试方法和门禁 | "三后端对比需要满足什么条件？" |

任务问题从 `evals/gold-questions.yaml`（当前 7 个问题）中抽取。每个 gold question 定义了 expected_pages、required_sources、must_state 和 must_not_state。

### 3.3 主要指标

| 指标 | 定义 | 测量方式 |
|------|------|---------|
| `success@1` | 首次尝试成功完成任务的比例 | 人工或 LLM-judge |
| 任务完成率 | 所有尝试中完成的比例 | 自动化 |
| 结论正确率 | 事实准确的任务比例 | 专家审阅 |
| 引用准确率 | 引用正确追溯到源位置的比例 | 自动化匹配 |
| 不可验证断言数 | 输出中无证据支持的说法数 | 专家审阅 |
| 技能触发精确率 | MXMACA 相关 Prompt 正确触发的比例 | 日志分析 |
| 技能触发召回率 | 非 MXMACA Prompt 正确不触发的比例 | 日志分析 |
| `tokens_per_solved_task` | 每个成功任务的输入+输出 Token | API Token 计数 |
| 单任务成本 | API 费用 / 任务数 | API 账单 |
| 完成时间 | Prompt 到完整回复的耗时 | 客户端计时 |

### 3.4 运行协议

1. 每个任务至少执行 N 次独立运行（N ≥ 3，推荐 ≥ 5 以获得统计显著性）
2. 随机化加载/不加载 session 的顺序
3. 记录所有输出：成功、失败、错误、超时
4. 原始日志保存在 `evals/claude/runs/YYYY-MM-DD-task-id-{a,b}-run-N.json`
5. 评分：两名独立审阅者或 LLM-as-judge（配明确评分标准）
6. 聚合：每个任务每个指标的平均值和标准差
7. 报告同时包含成功和失败样本，不只报告均值

### 3.5 运行器与评分脚本（待实现）

```bash
# A/B 评估运行器（Phase 2）
MACAWIKI_RUN_PAID_EVAL=1 python3 scripts/run_claude_ab_eval.py

# 评分
python3 scripts/score_claude_eval.py --results <results-dir>
```

### 3.6 数据公开要求

- 任务定义文件（JSON/YAML schema）
- 评分标准（rubric）
- 原始运行日志
- 聚合脚本和可视化代码

---

## 4. C500 硬件评测规范

C500 性能对比必须满足以下前置条件（详细门禁定义见 [硬件验证计划](hardware-validation.md)）：

1. **环境门禁**：硬件型号、驱动版本、MACA 版本、mxcc 版本、PyTorch 版本、源码 commit 已记录
2. **构建门禁**：完整编译命令、选项、返回码和日志已保存
3. **正确性门禁**：使用相同 seed/shape/dtype/输入分布，以 PyTorch 输出为 reference，报告最大绝对误差和 allclose
4. **计时门禁**：完成预热；每次计时前后使用确认过的同步方式；保存所有样本
5. **可比性门禁**：三后端必须来自同一机器、同一软件栈、同一输入契约
6. **结论门禁**：正确性失败、环境缺失或样本不足时，结论保持 `not_comparable`

**当前 C500 状态**：

| 算子 | PyTorch | TileLang | MXMACA++ | 状态 |
|------|---------|----------|-----------|------|
| add | ✅ C500 | ✅ C500 | — | comparable (speedup=0.73) |
| softmax | ✅ C500 | ✅ C500 | — | comparable (speedup=0.75) |
| layer_norm | ✅ C500 | ✅ C500 | — | comparable (speedup=0.83) |
| matmul | ✅ C500 | ✅ C500 | — | not_comparable (codegen gap) |
| quantize | ✅ C500 | ✅ C500 | — | comparable (speedup=1.59) |
| transpose | ✅ C500 | ✅ C500 | — | comparable (speedup=1.00) |
| moe_routing | ✅ C500 | ✅ C500 | — | not_comparable (top-k) |

MXMACA++ 后端：`not_run`（契约已定义，等待 SDK 环境重捕获）。

---

## 5. 当前评估状态

| 组件 | 状态 | 说明 |
|------|------|------|
| agent-value proxy | ✅ 已实现 | 9 cases, 7 positive + 2 negative |
| gold-questions | ✅ 已实现 | 7 个问题，5 个领域 |
| compare_benchmarks | ✅ 已实现 | 38 contract tests |
| Claude A/B runner | ❌ 已弃用 | wontfix：本地 Agent 优先架构 |
| Claude A/B scorer | ❌ 已弃用 | wontfix |
| CI/CD 自动评估 | ⚠️ 部分 | `make all` 包含 validate + test + agent-value |

**下一步**：获得 Claude API 付费授权 → 实现 `run_claude_ab_eval.py` → 实现 `score_claude_eval.py` → 首次 A/B 评估运行 → 结果写入 `evals/claude/reports/`。
