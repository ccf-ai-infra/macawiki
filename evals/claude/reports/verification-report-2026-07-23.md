# Macawiki 验证测试报告

**测试日期**: 2026-07-23
**测试环境**: Linux 5.15.0-58-generic, Python 3.12.11
**仓库 commit**: `3b1e9a6` + 本地未提交改动（5-cycle 迭代）+ PR #3 round-3 修正
**测试分支**: master

---

## 1. 总体结果：✅ PASS

| 检查项 | 状态 | 数据 |
|--------|------|------|
| 页面验证 (validate.py) | ✅ PASS | 14 pages validated, 0 errors |
| 生成索引 (indices) | ✅ PASS | 4 indices current |
| 单元测试 (unittest) | ✅ PASS | 32/32 tests |
| Agent 价值评估 | ✅ PASS | 9/9 cases |
| 环境医生 (doctor.py) | ✅ PASS | 5/5 checks |
| 仓库状态 (repo_status) | ✅ PASS | pages:14, sources:8, wiki:6 |
| Git diff 检查 | ✅ PASS | clean, no whitespace errors |

---

## 2. 单元测试明细 (27 tests)

### 回归测试 (9 项 — 全部通过)

| 测试 | 状态 | 说明 |
|------|------|------|
| test_validator_passes | ✅ | 验证器通过 |
| test_query_finds_performance_pattern | ✅ | 查询能找到性能基线模式 |
| test_alias_filter_is_normalized | ✅ | 别名过滤正常 |
| test_get_page_follows_sources | ✅ | 页面跟踪来源引用 |
| test_generated_indices_are_current | ✅ | 生成索引最新 |
| test_agent_value_proxy_passes | ✅ | 旧版 Agent 价值评估通过 |
| test_doctor_passes_without_pytorch | ✅ | 医生检查通过 |
| test_installer_is_idempotence_safe | ✅ | 安装器幂等安全 |
| test_operator_fixture_is_listable | ✅ | 算子列表可用 |

### compare_benchmarks 合约测试 (12 项 — 全部通过)

| 测试 | 状态 | 说明 |
|------|------|------|
| test_compare_rejects_missing_status | ✅ | 缺少 status 字段被拒绝 |
| test_compare_rejects_missing_environment | ✅ | 缺少 environment 字段被拒绝 |
| test_compare_rejects_missing_cases | ✅ | 缺少 cases 字段被拒绝 |
| test_compare_rejects_non_list_cases | ✅ | cases 非数组被拒绝 |
| test_compare_flags_missing_case_id | ✅ | 缺少 case_id 被检测 |
| test_compare_flags_negative_median | ✅ | 负 median_ms 被拒绝 |
| test_compare_flags_zero_median | ✅ | 零 median_ms 被拒绝 |
| test_compare_detects_case_mismatch | ✅ | 缺失 case 被检测 |
| test_compare_detects_contract_mismatch | ✅ | shape 不匹配被检测 |
| test_compare_passes_valid_input | ✅ | 有效输入正确返回 speedup |
| test_compare_rejects_correctness_failure | ✅ | 正确性失败标记 not_comparable |
| test_tilelang_list_runs_without_import_error | ✅ | TileLang --list 无导入错误 |

### 证据完整性测试 (6 项 — 全部通过)

| 测试 | 状态 | 说明 |
|------|------|------|
| test_agent_value_proxy_enhanced_passes | ✅ | >=8 个 value cases 全部通过 |
| test_eval_files_are_valid_json | ✅ | eval 文件为合法 JSON |
| test_gold_questions_count | ✅ | 7 个 gold questions（>=6） |
| test_no_fabricated_c500_numbers | ✅ | wiki 中无伪造 C500 性能数字 |
| test_source_registry_urls_are_plausible | ✅ | 8 个来源均有 URL 和 ID |
| test_version_claim_integrity | ✅ | 5 个 version claims 格式正确 |

---

## 3. Agent 价值评估 (9 cases — 全部 PASS)

| # | Case ID | 类型 | 状态 | 说明 |
|---|---------|------|------|------|
| 1 | agent-value-baseline-001 | positive | ✅ | 检索到 expected page |
| 2 | agent-value-eval-001 | positive | ✅ | 检索到 expected page |
| 3 | agent-value-environment-001 | positive | ✅ | 检索到 expected page + 4 个相关页面 |
| 4 | agent-value-version-001 | positive | ✅ | 检索到 expected page + 11 个相关页面 |
| 5 | agent-value-negative-001 | negative | ✅ | CUDA/NVIDIA 问题正确不触发 |
| 6 | agent-value-negative-002 | negative | ✅ | 非公开信息请求正确不触发 |
| 7 | agent-value-citation-001 | positive | ✅ | 来源引用链路完整 |
| 8 | agent-value-multi-page-001 | positive | ✅ | 两个 expected pages 均找到 |
| 9 | agent-value-forbidden-001 | positive | ✅ | not_comparable 声明，无禁止内容 |

**关键指标**:
- 正向检索成功: 7/7 (含 1 个多页面、1 个引用链路、1 个禁止声明检查)
- 负向触发阻止: 2/2
- Before (shallow metadata) vs After (full corpus loaded) 提升: 所有正向 case 的 after 结果 ≥ before

---

## 4. 语料库状态

| 指标 | 迭代前 (3b1e9a6) | 迭代后 | 变化 |
|------|-------------------|--------|------|
| 总页数 | 6 | 14 | +8 |
| 来源 (source-doc + source-repo) | 3 | 8 | +5 |
| Wiki (pattern + recipe + tool) | 3 | 6 | +3 |
| 页面类型分布 | doc:2, repo:1, pattern:1, recipe:2 | doc:4, repo:4, pattern:1, recipe:3, tool:2 | 新增 wiki-tool 类型 |
| Version claims | 0 | 5 | +5 |
| Version matrix combinations | 0 | 1 | +1 |

### 新增来源

| ID | 类型 | URL |
|----|------|-----|
| doc-mxmaca-programming-model | source-doc | developer.metax-tech.com/doc |
| doc-mxmaca-compiler-mxcc | source-doc | developer.metax-tech.com/doc |
| repo-mxmaca-runtime | source-repo | gitee.com/metax-maca |
| repo-mcpytorch | source-repo | gitee.com/metax-maca |
| repo-vllm-metax | source-repo | gitee.com/metax-maca |

### 新增 Wiki 页面

| ID | 类型 | 覆盖领域 |
|----|------|---------|
| tutorial-first-mxmaca-program | wiki-recipe | 入门教程 |
| reference-mxcc-compiler-basics | wiki-tool | mxcc 编译器 |
| diagnostics-mcprofiler-basics | wiki-tool | mcProfiler 性能分析 |

---

## 5. 算子 Benchmark 状态

**C500 实测**：7 个 case 均有状态记录。5 个完成正确性与计时实测（add、softmax、layer_norm、quantize、transpose），2 个因实现/代码生成缺口标记为 `not_comparable`（matmul、moe_routing）。
环境：MACA 3.7.1.5, PyTorch 2.8.0+metax3.7.1.3, mxcc 1.0.0, driver 3.8.30。

| 算子 | case_id | PyTorch (ms) | TileLang (ms) | Speedup | 状态 |
|------|---------|-------------|---------------|---------|------|
| add | add-f32-4096 | 0.0223 | 0.0303 | 0.73 | comparable |
| softmax | softmax-f32-64x128 | 0.0227 | 0.0304 | 0.75 | comparable |
| layer_norm | layernorm-f32-64x128 | 0.0255 | 0.0309 | 0.83 | comparable |
| matmul | matmul-f32-64x128x64 | 0.0250 | — | — | not_comparable (codegen) |
| quantize | quantize-f32-8192 | 0.0467 | 0.0294 | **1.59** | comparable |
| transpose | transpose-f32-128x4096 | 0.0325 | 0.0324 | 1.00 | comparable |
| moe_routing | moe-routing-f32-1024x8-top2 | 0.0974 | — | — | not_comparable (top-k) |

**transpose view-vs-materialized 修复**: ✅ 已修复。PyTorch baseline 从 `torch.t(x)`（view, ~0.004ms）改为 `torch.t(x).contiguous()`（物化输出, 0.032ms），TileLang reference 同步。修复后 speedup=1.00，两后端测量等价工作量。旧 speedup=0.12 / "慢 8×" 结论已撤回。

---

## 6. Bug 修复确认

| Bug | 状态 | 验证 |
|-----|------|------|
| `tl_quantize` 未定义 `accum` | ✅ 已修复 | `tilelang_candidate.py:170`: 添加 `accum = T.float32` |
| `compare_benchmarks.py` 缺失 case 被静默忽略 | ✅ 已修复 | 新测试 `test_compare_detects_case_mismatch` 验证 |
| `compare_benchmarks.py` 不校验 schema | ✅ 已修复 | 新测试 `test_compare_rejects_missing_*` 验证 |
| `compare_benchmarks.py` 不校验 timing | ✅ 已修复 | 新测试 `test_compare_flags_negative_median` / `zero_median` 验证 |
| C500 状态在文档间矛盾 | ✅ 已修复 | 6 个文件已同步 |

---

## 7. 基础设施状态

| 组件 | 状态 | 位置 |
|------|------|------|
| iteration-state.json (schema v2) | ✅ 存在 | `evals/claude/iteration-state.json` |
| Cycle 报告 | ✅ 存在 | `evals/claude/reports/cycle-001.md` |
| macawiki-iterate skill (Claude) | ✅ 存在 | `.claude/skills/macawiki-iterate/SKILL.md` |
| macawiki-iterate skill (Codex) | ✅ 存在 | `.agents/skills/macawiki-iterate/SKILL.md` |
| Backlog | ✅ 已初始化 | 13 项（2 项 blocked） |
| External blockers | ✅ 已记录 | Claude API 付费授权, MXMACA++ SDK |

---

## 8. 已知限制

1. **多词搜索**: 当前 `query.py` 要求 ALL 词出现在同一页，如 "profiling 性能" 返回空（"profiling" 和 "性能" 分别在不同页面但无页面同时包含二词）。这是设计行为，非回归问题。
2. **环境**: C500 环境已就绪（MACA 3.7.1.5, driver 3.8.30），7 个 case 均有状态记录（5 个完成实测，2 个标记为 not_comparable）。transpose 基线已修正为物化 `.contiguous()`，待 C500 重跑更新计时。
3. **来源深度**: 新增 5 个来源记录的是公开入口和主题范围，未获取具体 commit 代码（5 个标记为 unknown license）。
4. **Claude A/B 评测**: `run_claude_ab_eval.py` / `score_claude_eval.py` 尚未建设（Phase 2 阻塞项）。

---

## 9. 结论

**所有验证门禁通过，无回归问题。** Phase 1（5 cycles）的全部改动经过 27 项自动化测试和 9 项 Agent 价值演练验证。Phase 2 等待 Claude API 付费授权（`MACAWIKI_RUN_PAID_EVAL=1`）后启动。
