# Issue #2 迭代计划: Macawiki Claude 持续价值优化

> **状态**: 待审核
> **基于**: Issue #2 评审评论 + 当前 HEAD (`3b1e9a6`) 本地代码核实
> **创建日期**: 2026-07-22

---

## 当前状态核实

| 项目 | Issue #2 评审中的说法 | 本地核实结果 |
|------|----------------------|-------------|
| `3b1e9a6` 不在历史中 | ⚠️ 声称不存在 | ✅ 实际存在，是当前 HEAD |
| `tl_quantize` 未定义 `accum` | ⚠️ 已指出 | ✅ `tilelang_candidate.py:178-179` 确认存在 bug |
| `compare_benchmarks.py` 不校验 schema | ⚠️ 已指出 | ✅ 确认：仅 47 行，只检查环境指纹和正确性门禁 |
| `evals/claude/` 目录缺失 | ⚠️ 已指出 | ✅ 确认不存在 |
| `iteration-state.json` 缺失 | ⚠️ 已指出 | ✅ 确认不存在 |
| `macawiki-iterate` skill 缺失 | ⚠️ 已指出 | ✅ 确认不存在 |
| `run_claude_ab_eval.py` 缺失 | ⚠️ 已指出 | ✅ 确认不存在 |
| `score_claude_eval.py` 缺失 | ⚠️ 已指出 | ✅ 确认不存在 |
| version-claims/version-matrix 为空 | ⚠️ 已指出 | ✅ 确认均为空数组 |
| 仅 3 个 sources / 3 个 wiki pages | ⚠️ 已指出 | ✅ 确认：6 页总计，5 draft，1 reviewed |
| 无 mcPytorch/TileLang/vLLM-metax 生态接入 | ⚠️ 已指出 | ✅ 确认：仅 benchmarks/ 下有 scaffold |

**修正**: Issue #2 正文中 `3b1e9a6` 的引用实际是正确的，无需修改。

**9 个单元测试 + 3 个 agent value proxy + docter 全部通过**（`make all` 通过）。

---

## 两阶段策略

根据 Issue #2 评论的建议，将工作分为两个阶段：

### Phase 1 — 离线立即可做（无需 Claude API 付费授权）

**优先级 P0**：修复硬错、加强比较器、扩充非算子校验手段。
**优先级 P1**：建设迭代基础设施（state file、cycle 流程）、扩充语料覆盖面。

### Phase 2 — 需付费授权和 C500 环境（阻塞状态）

真实 Claude A/B 评测、C500 硬件验证、上下游实机接入。**暂不启动。**

---

## Phase 1 迭代计划

### Cycle 1: 修复硬错 + 加强 compare_benchmarks.py

**假设**: 修复 TileLang quantize 的 `accum` 未定义错误，并加强 `compare_benchmarks.py` 使其能校验 schema、检测缺失 case、验证 timing 字段，将消除已知的静态缺陷并防止未来的静默错误。

**影响文件**:
- `benchmarks/tilelang_candidate.py` (fix)
- `scripts/compare_benchmarks.py` (rewrite)
- `tests/test_repository.py` (new tests)

**具体改动**:

1. **修复 `tl_quantize` 的 `accum` 未定义**（`tilelang_candidate.py:178-179`）
   - `accum` 应为量化计算的累加器 dtype。根据上下文（`sf = T.float32(scale)`），累加器应为 `"float32"`。
   - 将 `T.Cast(accum, x[i])` 改为 `T.Cast("float32", x[i])`，或定义 `accum = "float32"` 变量。
   - 新增 `pytest` 风格的 import/CLI 静态测试：`python3 benchmarks/tilelang_candidate.py --list` 和代码语法检查。

2. **加强 `compare_benchmarks.py`**
   需要增加的校验维度：

   | 当前缺失 | 需增加 |
   |---------|--------|
   | 不校验 schema 字段 | 检查顶层必需字段：`status`, `environment`, `cases` |
   | 不校验 case 字段 | 检查每个 case 的 `case_id`, `operator`, `correctness`, `timing` |
   | 不校验 timing 契约 | 检查 `median_ms` 为正数、`warmup`/`iterations` 一致性 |
   | 缺失 case 静默忽略 | 报告仅在 baseline 或仅在 candidate 中的 case |
   | 不检查 case contract | 验证 `operator`, `shape`, `dtype` 在基线/候选间一致 |
   | 不检查 `not_run`/`not_comparable` | 正确性失败或 `not_run` 的 case 应显式报告 |

   输出格式保持 JSON，新增 `issues` 和 `missing_cases` 字段。

3. **新增针对性测试**
   - `test_compare_rejects_missing_fields`: 缺 `status`/`environment`/`cases` 等场景
   - `test_compare_flags_case_mismatch`: baseline 有、candidate 无的 case
   - `test_compare_requires_positive_median`: `median_ms` <= 0 时报 not_comparable
   - `test_tilelang_list_runs_without_import_error`: 无 TileLang 环境下 `--list` 可用

**验收标准**:
- `tl_quantize` 代码不再引用未定义变量
- `compare_benchmarks.py` 能检出已知的 schema 违规
- 所有新增测试通过
- `make all` 继续通过

---

### Cycle 2: 文档一致性同步

**假设**: 将 `README.md`、`SKILL.md`、`CLAUDE.md`、`docs/usage.md`、`docs/iteration-plan.md`、`docs/hardware-validation.md`、`benchmarks/README.md` 中关于 C500 状态、已实现能力、版本范围的描述进行一致性同步，能消除文档间的矛盾并降低 Agent 的混淆。

**影响文件**:
- `README.md`
- `SKILL.md`
- `docs/hardware-validation.md`
- `docs/usage.md`
- `docs/iteration-plan.md`
- `benchmarks/README.md`

**具体改动**:

1. 梳理当前文档中关于以下状态的不一致描述：
   - C500 环境状态（已就绪 vs 等待环境）
   - MXMACA++ 接入状态（backends/ 契约存在 vs 后端正运行）
   - 7 个算子（4 个原始 + 3 个新加）是否在所有文档中一致列出
   - Iterator 4（C500 bring-up）原文"等待环境"与实际已捕获结果的矛盾

2. 统一为:
   - C500: **已就绪，已有 PyTorch + TileLang 实测结果**（4 个基础算子 comparable，matmul not_comparable，3 个新算子结果在 results/ JSON 中）
   - MXMACA++: **契约已定义，后端未接入**（`not_run`）
   - 所有 7 个算子: add, softmax, layer_norm, matmul, quantize, transpose, moe_routing
   - 区分 "历史 C500 实测"、"当前环境运行"、"实现存在"、"`not_run`"、"`not_comparable`"

3. `docs/iteration-plan.md` 迭代 4 更新状态（从"等待环境"→"已完成初步 bring-up，后续扩展在硬件可用时继续"）

**验收标准**:
- 所有文档对 C500/MXMACA++ 状态的描述一致
- 无"当前无 C500"与"已保存 C500 结果"的矛盾
- `make all` 通过

---

### Cycle 3: 建设迭代基础设施

**假设**: 建设最小的迭代状态文件、cycle 报告模板和 `macawiki-iterate` skill，使后续的持续优化循环可追踪、可恢复、可审计。

**影响文件（新创建）**:
- `evals/claude/iteration-state.json` (schema v2)
- `evals/claude/reports/cycle-001.md` (本轮的 3 个 cycle 报告)
- `.agents/skills/macawiki-iterate/SKILL.md` (Codex)
- `.claude/skills/macawiki-iterate/SKILL.md` (Claude Code)

**注意**: `macawiki-iterate` skill 仅包含控制流程（读取 state → 选 backlog → 执行 cycle → 报告），不包含具体的运维约束（约束已在 AGENTS.md/CLAUDE.md 中）。

**具体改动**:

1. **`evals/claude/iteration-state.json`**
   - 按 Issue #2 正文中的 schema v2 创建
   - `champion.commit` 初始设为当前 HEAD `3b1e9a6`
   - backlog 从本文档的未完成项自动初始化
   - `external_blockers` 记录 Phase 2 的阻塞条件（付费授权、C500 环境变更）

2. **`evals/claude/reports/cycle-001.md`**
   - 记录 Cycle 1 的执行证据（before/after diff、测试结果、决策理由）

3. **`macawiki-iterate` skill**
   - 精简版：仅保留控制流程骨架
   - 支持参数：`status`, `next`, `run`（`run` 标注为受限）
   - 标注 `disable-model-invocation: true`（需要用户显式调用）

4. **Backlog 初始化**
   从 Issue #2 正文和本次审查中提取所有未完成项，写入 state 文件：
   - P0: accum 修复（Cycle 1 中完成）
   - P0: compare_benchmarks 加强（Cycle 1 中完成）
   - P1: 文档一致性同步（Cycle 2 中完成）
   - P1: 版本声明与矩阵数据扩充（从已有 sources 提取 version 信息）
   - P1: 语料扩充（增加更多公开来源和 wiki pages）
   - P2: 生态任务骨架（mcPytorch/vLLM-metax/cu-bridge 的 mock 任务）
   - P2: Claude A/B eval 基础设施（`run_claude_ab_eval.py`, `score_claude_eval.py`, tasks/rubric）
   - P3: 来源新鲜度检查脚本
   - P3: 链接失效检测

**验收标准**:
- `evals/claude/iteration-state.json` 可被 Python `json.load` 解析
- skill 文件语法正确，Agent 可发现
- `make all` 不报新错误（新增文件不违反正则约束）

---

### Cycle 4: 扩充非算子验证手段

**假设**: 当前 Agent 价值证据仅靠 3 个检索 proxy case（且主题重叠于环境和基线），增加版本/来源引用链路、negative-prompt 触发保护和文档一致性 lint 测试，能更全面地衡量 Macawiki 对 Agent 的价值。

**影响文件**:
- `evals/agent-value-cases.yaml` (扩展)
- `evals/gold-questions.yaml` (扩展)
- `tests/test_repository.py` (新增测试)
- `scripts/run_agent_value_eval.py` (增强)

**具体改动**:

1. **扩展 `agent-value-cases.yaml`** — 从 3 个 case 扩展到至少 8 个:
   - 新增 version-claim 验证 case: 查询版本相关信息时能否找到对应声明
   - 新增 negative-prompt case: 非 MXMACA 问题（如"如何用 CUDA 优化 GPU Kernel"）不应返回 MXMACA 页面
   - 新增 source-citation 链路 case: 查询结果能否追溯到具体 source ID
   - 新增 multi-page synthesis case: 需要跨多个 wiki pages 的综合查询
   - 新增 forbidden-claim case: 确保不包含虚构的 C500 性能数字或安装命令

2. **扩展 `gold-questions.yaml`** — 从 3 个到至少 6 个:
   - 覆盖更多 MXMACA 子领域（编译器、运行时、profiling）
   - 增加边界问题（证据不足时应拒答）

3. **新增测试**:
   - `test_version_claim_integrity`: version-claims 中的声明格式和引用完整性
   - `test_no_fabricated_c500_numbers`: 所有 corpus 不含未经来源支撑的 C500 性能数字
   - `test_source_links_valid`: 所有 source URL 格式且对应 source ID 存在
   - `test_negative_prompt_no_false_trigger`: 非 MXMACA prompt 不触发相关页面

4. **增强 `run_agent_value_eval.py`**:
   - 增加 negative-trigger 检查（prompt 不应触发 Macawiki 的场景）
   - 增加 source 引用链路完整性检查

**验收标准**:
- agent-value-cases 从 3 个增加到至少 8 个
- gold-questions 从 3 个增加到至少 6 个
- 所有新增测试通过
- `make all` 通过

---

### Cycle 5: 语料覆盖面扩充

**假设**: 当前仅 3 个来源和 3 个 wiki pages，覆盖不了 MXMACA 软件栈的关键领域（编译器 mxcc、运行时 mxmaca-runtime、profiler mcprofiler、编程模型 maca），增加公开来源和对应 wiki pages 能扩大 Agent 可回答问题的范围。

**影响文件**:
- `data/source-registry.yaml` (新增来源)
- `wiki/` (新增 pages)
- `data/version-claims.yaml` (从来源提取版本信息)
- `data/version-matrix.yaml` (从来源填充组合)
- `data/tags.yaml` / `data/aliases.yaml` (扩展词表)

**具体改动**:

1. **新增公开来源**（目标：从 3 → 至少 8 个）:
   - MetaX-MACA Gitee 组织的关键仓库（mxcc, mxmaca-runtime）的 README/文档
   - MXMACA 编程模型官方文档
   - TileLang 上游仓库（公开）
   - mcPytorch 仓库（公开，如可用）

   每个新来源：
   - 记录 URL、访问状态、许可证状态、捕获策略
   - 仅保留 metadata 和必要摘要，不复制许可证不明的完整文档

2. **新增 wiki pages**（目标：从 3 → 至少 6 个）:
   - `wiki/tutorials/mxmaca-first-program.md`: MXMACA 第一个程序
   - `wiki/reference/mxcc-compiler-flags.md`: mxcc 编译器关键选项
   - `wiki/diagnostics/profiling-with-mcprofiler.md`: mcProfiler 基本用法
   - 或基于可用来源确定最适合的 pages

3. **填充 version-claims 和 version-matrix**:
   - 从已有和新来源中提取版本相关声明
   - 记录 `unspecified` 的诚实标注
   - 维持 "不做推断" 的约束

**验收标准**:
- 来源数量增加到至少 8 个
- wiki pages 增加到至少 6 个
- `version-claims.claims` 从空数组变为至少有一些条目
- `version-matrix.combinations` 从空数组变为至少有记录
- `make all` 通过（包括 generate_indices 更新）

---

## Phase 2（阻塞项 — 暂不执行）

| 阻塞条件 | 依赖 |
|---------|------|
| Claude API 付费授权 | `MACAWIKI_RUN_PAID_EVAL=1` 或用户明确授权 |
| C500 环境变更 | 需要新环境 fingerprint 或重新捕获 |
| MXMACA++ 接入 | 需要 MXMACA++ SDK 和 C500 环境 |
| 上下游实机任务 | 需要对应框架在 C500 上可运行 |

Phase 2 中的工作项：
- `run_claude_ab_eval.py` 和 `score_claude_eval.py` 的完整实现
- 真实 Claude loaded vs unloaded A/B 评测
- C500 环境重新捕获和验证
- MXMACA++ 后端实现和评测
- 生态任务（mcPytorch, vLLM-metax, cu-bridge）的实机验证

---

## 执行时间线

```
Phase 1 (离线可做，无需授权)

Cycle 1: 修复硬错 + 加强 compare  ← 立即开始 (P0)
    ↓
Cycle 2: 文档一致性同步           ← Cycle 1 完成后 (P0)
    ↓
Cycle 3: 建设迭代基础设施        ← Cycle 2 完成后 (P1)
    ↓
Cycle 4: 扩充非算子验证手段      ← Cycle 3 完成后 (P1)
    ↓
Cycle 5: 语料覆盖面扩充          ← Cycle 4 完成后 (P1)
    ↓
[暂停，检查 Phase 2 阻塞条件]
    ↓
汇报当前状态 + 恢复命令
```

---

## 审核后自动执行

本文档审核通过后，将按 Cycle 1→5 顺序执行：

1. **每个 cycle 前**：读取当前 state、运行 `make all` 基线
2. **执行改动**：仅修改该 cycle 声明的文件
3. **运行验收**：`make all` + 新增测试
4. **记录报告**：写 `evals/claude/reports/cycle-NNN.md`
5. **更新 state**：标记 cycle 状态为 `accepted` 或 `rejected`
6. **继续下一个 cycle** 或 **暂停并汇报**

---

## 恢复命令

```bash
# 在任何时候查看状态
python3 scripts/doctor.py --json
python3 scripts/run_agent_value_eval.py --json
python3 scripts/repo_status.py
make all

# 如已建 skill:
# /macawiki-iterate status
# /macawiki-iterate next
```
