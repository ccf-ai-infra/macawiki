# 使用指南

## 最短工作流

```bash
python3 scripts/query.py "算子 性能基线" --compact
python3 scripts/get_page.py evaluation-compare-operator-backends --follow-sources
python3 scripts/grep_wiki.py "TileLang|MXMACA\+\+|torch.matmul"
```

回答时同时输出：页面 ID、来源 ID/URL、硬件与软件版本范围、置信度，以及仍缺少的验证。

## 回答契约

Macawiki Agent 在回答 MXMACA 相关问题时必须遵守以下契约（完整规则见 [SKILL.md](../SKILL.md)）：

- 引用页面 ID 和仓库路径，引用来源 ID 或公开 URL
- 声明硬件和 MXMACA/框架版本范围
- 区分 `verified`、`source-reported`、`corroborated`、`inferred`、`experimental` 置信度
- 将无完整基准元数据的性能数据视为不可比较
- 将仅 CPU 的 PyTorch 运行标注为流程检查，不作为 C500 性能证据
- 将未通过正确性+计时门禁的 TileLang 结果保持为 `not_comparable`
- 将 MXMACA++ 结果保持为 `not_run`，直到后端接入 C500 环境
- 使用统一状态术语（定义见 `docs/hardware-validation.md`）

## 给 Agent 的示例

### Claude Code

```text
/macawiki 检查这个 MXMACA 算子优化方案是否具备可比较的基线。
列出缺失的环境、正确性、计时和溯源字段，不要把 CUDA 假设当成 MXMACA 事实。
```

### Codex

```text
$macawiki 为 matmul 设计 PyTorch、TileLang、MXMACA++ 三后端对比。
先检索仓库，引用页面和公开来源；当前没有 C500，所以只生成运行计划和命令，不能生成性能数值。
```

## 端到端使用示例

以下 5 个示例展示 Macawiki 在真实 MXMACA 任务中的价值。每个示例包含完整的任务背景、Prompt、预期来源、预期产物、通过标准和限制条件。

---

### 示例 1：环境与兼容性诊断

**背景**：用户新搭建了一个 MXMACA 开发环境，需要确认环境是否可用，以及各组件版本是否兼容。

**完整 Prompt**：

```text
/macawiki 我刚搭建了一个 MXMACA 开发环境，请帮我确认环境是否可用。
需要检查哪些组件（MACA、mxcc、PyTorch、TileLang）？给出可运行的验证命令和版本获取方法。
如果某些信息不够，请告诉我还需要收集什么。
```

**预期来源**：
- `recipe-verify-mxmaca-environment`（wiki）：环境诊断方法
- `doc-mxmaca-quick-start`（source）：官方快速上手文档

**预期产物**：
- 逐项可运行的验证命令（maca 版本查询、mxcc --version、Python import）
- 版本信息获取方法
- 命令执行顺序
- 各命令的预期成功输出示例

**通过标准**：
- 给出版本化命令，而非"所有版本通用"的安装指令
- 引用 `doc-mxmaca-quick-start` 来源和 URL
- 标注不确定版本范围为 `unspecified`
- 不编造硬件型号，不假设 CUDA 行为等价于 MXMACA
- 明确说明 C500 需要物理硬件，不能通过软件检查推断

**限制**：当前 corpus 不含所有 MACA 版本的兼容性矩阵。具体硬件环境影响命令输出格式。

---

### 示例 2：算子基线评审

**背景**：开发者为 C500 上的 `add` 算子编写了性能基线，需要评审基线设置是否满足可比性门禁。

**完整 Prompt**：

```text
/macawiki 审查 add 算子 f32[4096] 在 C500 上的基准测试设置是否满足可比性门禁。
列出所有需要检查的门禁（环境、构建、正确性、计时、可比性、结论），逐项说明通过条件。
```

**预期来源**：
- `pattern-establish-performance-baseline`（wiki）：基线建立模式
- `evaluation-compare-operator-backends`（wiki）：算子对比方法
- `docs/hardware-validation.md`：C500 验证计划与门禁定义

**预期产物**：
- 逐项检查清单：硬件型号、驱动/MACA/mxcc 版本、shape、dtype、seed、warmup、iterations、同步策略
- 每项门禁的通过条件
- 建议的 benchmark 运行命令

**通过标准**：
- 列出全部 6 个门禁（环境、构建、正确性、计时、可比性、结论）
- 引用 `pattern-establish-performance-baseline` 和硬件验证文档
- 不包含虚构的性能数字
- 说明必须在同一 C500 环境运行两后端才可比较

**限制**：无独立参考实现时，正确性比较只能以 PyTorch 自身为参考（self-check），非独立验证。

---

### 示例 3：三后端评测计划生成

**背景**：团队需要为 `softmax` 算子设计 PyTorch/TileLang/MXMACA++ 三后端对比方案。

**完整 Prompt**：

```text
/macawiki 为 softmax f32[64,128] 生成 PyTorch、TileLang、MXMACA++ 三后端评测计划。
包括输入契约、运行命令、门禁检查清单和预期输出格式。
当前 MXMACA++ 后端未接入，标记为 not_run。
```

**预期来源**：
- `evaluation-compare-operator-backends`（wiki）：三后端评估方法
- `benchmarks/operator_cases.yaml`：softmax case 定义
- `docs/hardware-validation.md`：门禁顺序

**预期产物**：
- Softmax case 的完整参数（shape=[64,128], dtype=float32, dim=-1, tolerance=1e-5）
- PyTorch baseline 运行命令
- TileLang candidate 运行命令（含 PYTHONPATH）
- MXMACA++ 标注为 `not_run`
- 门禁检查清单
- 预期输出 JSON schema

**通过标准**：
- 不生成假的性能数字
- MXMACA++ 正确标注为 `not_run`
- 包含环境指纹、正确性门禁、计时门禁的逐项要求
- 生成的是运行计划，不是性能结论

**限制**：MXMACA++ 后端未接入，仅可定义契约；C500 环境不在本地时只生成计划。

---

### 示例 4：上下游生态项目查询

**背景**：开发者计划在 mcPytorch 或 vLLM-MetaX 项目中进行 MXMACA 适配，需要了解这些生态项目的版本和许可证状态。

**完整 Prompt**：

```text
/macawiki 我需要了解 mcpytorch 和 vllm-metax 的当前状态：
它们的来源 URL、版本范围、许可证状态和支持的 MXMACA 版本。
如果信息不完整，请明确标注缺失部分。
```

**预期来源**：
- `repo-mcpytorch`（source）：mcPytorch 仓库来源记录
- `repo-vllm-metax`（source）：vLLM-MetaX 仓库来源记录
- `repo-mxmaca-runtime`（source）：MXMACA 运行时仓库来源记录

**预期产物**：
- 每个来源的 URL、许可证状态、检索日期
- 版本范围（明确版本或 `unspecified`）
- 已知约束和注意事项
- 缺失信息的明确列表

**通过标准**：
- 引用具体来源 ID 和 Gitee URL
- 标注未知许可证为 `unknown`
- 版本不确定时声明 `unspecified`，不推断
- 不声称已审查过仓库代码（仅记录公开入口信息）

**限制**：来源记录为公开入口+主题范围摘要，非完整代码审查；许可证状态可能过时。

---

### 示例 5：已知问题诊断

**背景**：用户报告 `tl_quantize` kernel 存在编译错误，需要定位并修复。

**完整 Prompt**：

```text
/macawiki tl_quantize kernel 中 accum 变量未定义的问题是怎么发现和修复的？
给出修复前后的代码对比，以及验证方法。
```

**预期来源**：
- `benchmarks/tilelang_candidate.py`：TileLang kernel 实现
- `evaluation-compare-operator-backends`（wiki）：算子评估文档
- `evals/claude/reports/cycle-001.md`：修复记录

**预期产物**：
- Bug 根因分析（`tl_quantize` 缺少 `accum = T.float32` 声明）
- 修复前/修复后代码对比
- 验证命令（`make all`、quantize case 正确性门禁）
- 同类问题检查清单（其他 kernel 的 accum 声明）

**通过标准**：
- 引用具体代码行号（`tilelang_candidate.py:170`）
- 说明修复已在 PR #3 cycle 1 中完成
- 提供可运行的验证命令
- 不生成未经证实的其他 bug 报告

**限制**：此 bug 已修复，仅用于展示 Macawiki 的问题诊断能力。

---

## 离线价值演练

```bash
python3 scripts/run_agent_value_eval.py
```

它验证"加载 Macawiki 后能否找到预期页面、证据、版本范围和禁止断言"——这不是大模型能力排行榜，也不声称未加载 Agent 一定答错；它证明的是仓库向 Agent 提供了可机器检查的证据包和安全边界。

9 个演练 case 覆盖：正向检索（7 个）、负向触发（2 个）、多页面合成、来源引用链和禁止声明检查。详见 [评估文档](evaluation.md)。

## 更多查询模式

```bash
# 按类型过滤
python3 scripts/query.py --type wiki-pattern --compact

# 按硬件过滤
python3 scripts/query.py --hardware c500 --compact

# 按组件过滤
python3 scripts/query.py --component mxcc --compact

# 按版本过滤
python3 scripts/query.py --version unspecified --compact

# 全文搜索符号或错误文本
python3 scripts/grep_wiki.py "roofline|kWarpSize|accum"
```

完整查询参考见 [references/examples.md](../references/examples.md)。
