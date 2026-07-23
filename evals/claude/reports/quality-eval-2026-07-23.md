# Macawiki 质量与效果评估报告

**日期**: 2026-07-23
**基准版本**: `master` @ `3b1e9a6` (35a2496 之前的迭代前基线)
**环境**: Linux 5.15, Python 3.12.11, PyTorch 2.8.0+metax3.7.1.3, MACA 3.7.1.5
**评测维度**: 正确性、检索效果、证据可追溯性、测试覆盖、benchmark 完整性

---

## 1. 总体得分

| 维度 | 评分 | 状态 |
|------|------|------|
| 确定性测试 (35 tests) | 35/35 | ✅ PASS |
| Agent 价值演练 (3 cases) | 3/3 | ✅ PASS |
| 页面验证 (6 pages) | 0 errors | ✅ PASS |
| 查询召回率 (6 queries) | 4/6 | ⚠️ 67% |
| 源代码缺陷 | 1 bug | ❌ accum 未定义 |
| Benchmark 完整性 | 4/7 cases | ⚠️ 57% |
| 来源可追溯性 | 3/3 linked | ✅ PASS |
| 版本数据 | 0 条 | ❌ 空 |
| 页面质量 | 5/6 draft | ⚠️ 83% draft |

---

## 2. 测试结果

### 2.1 单元测试: ✅ 35/35 PASS（回归 9 + compare 15 + transpose 3 + 证据 8）

### 2.2 Agent 价值演练: ✅ 3/3 PASS

| Case | 目标页面 | 来源引用 | 禁止内容 | 结果 |
|------|---------|---------|---------|------|
| baseline-001 | pattern-establish-performance-baseline | repo-mxmaca-performance-tuning-guide | 无伪造 | ✅ |
| eval-001 | evaluation-compare-operator-backends | doc-pytorch + repo-tuning-guide | 无伪造 speedup | ✅ |
| environment-001 | recipe-verify-mxmaca-environment | doc-mxmaca-quick-start | 无通用安装命令 | ✅ |

**但存在严重覆盖缺口**: 仅 3 个 case，全部为正向检索，无 negative-trigger（非 MXMACA 问题应不触发）、无 citation-chain 验证、无 forbidden-claim 检查、无多页面综合查询。

---

## 3. 检索效果评估

| # | 查询 | 召回页数 | 状态 | 分析 |
|---|------|---------|------|------|
| Q1 | `性能 基线` | 0 | ❌ | "性能"和"基线"均在某页出现，但无单页同时含二词 |
| Q2 | `MXMACA 环境` | 1 | ✅ | 找到 recipe-verify-mxmaca-environment |
| Q3 | `算子 对比` | 0 | ❌ | 同上 AND 语义问题 |
| Q4 | `profiler` | 2 | ✅ | 找到 tuning-guide + baseline pattern |
| Q5 | `TileLang matmul` | 0 | ❌ | 无单页同时含 TileLang 和 matmul |
| Q6 | `mxcc` | 4 | ✅ | 找到 4 个相关页面 |

**根因**: `query.py` 使用 AND 语义（`all(term in haystack for term in terms)`），多词中文查询要求所有词出现在同一页中。当 corpus 较小时（6 pages），交叉覆盖不足。

---

## 4. 代码质量

### ❌ 缺陷: tl_quantize 使用未定义变量 `accum`

```python
# benchmarks/tilelang_candidate.py:164-182
@tilelang.jit(target="maca")
def tl_quantize(X, scale: float, BLOCK_N, dtype, out_dtype, threads):
    # ... 参数定义 ...
    # ❌ 缺少: accum = T.float32
    with T.Kernel(...) as (bx,):
        # ...
        for i in T.Parallel(BLOCK_N):
            qf = T.Cast(accum, x[i]) / sf      # ← accum 未定义!
            qf = T.max(lo, T.min(hi, T.Cast(accum, T.round(qf))))  # ← 同上
```

`tl_softmax` (line 80) 和 `tl_layernorm` (line 108) 各自定义了 `accum = T.float32`，但 `tl_quantize` 遗漏了。该 bug 已在 PR #3 迭代中修复 (`accum = T.float32` 已添加)，C500 环境已就绪且 quantize 正确性通过。

---

## 5. Benchmark 完整性

| operator_cases.yaml | PyTorch C500 | TileLang C500 | 对比状态 |
|---------------------|-------------|--------------|---------|
| add-f32-4096 | ✅ | ✅ | comparable (speedup=0.73) |
| softmax-f32-64x128 | ✅ | ✅ | comparable (speedup=0.75) |
| layernorm-f32-64x128 | ✅ | ✅ | comparable (speedup=0.83) |
| matmul-f32-64x128x64 | ✅ | ✅ | not_comparable (codegen) |
| quantize-f32-8192 | ✅ | ✅ | comparable (**speedup=1.59**) |
| transpose-f32-128x4096 | ✅ | ✅ | comparable (speedup=1.00) |
| moe-routing-f32-1024x8-top2 | ✅ | ✅ | not_comparable (top-k) |

**全部 7 个 case 均有 C500 状态记录**：5 个完成正确性与计时实测（add、softmax、layer_norm、quantize、transpose），2 个因实现/代码生成缺口标记为 `not_comparable`（matmul、moe_routing）。quantize 是 TileLang 首个超过 PyTorch 基线的算子（speedup=1.59）。transpose 基线已修正为 `.contiguous()`（物化输出），C500 重跑后 speedup=1.00，两个后端测量等价工作量。

---

## 6. 语料库质量

| 指标 | 值 | 评价 |
|------|-----|------|
| 总页数 | 6 | 面窄 |
| 来源数 | 3 | 仅覆盖 quick-start、pytorch-ref、tuning-guide |
| Wiki 页数 | 3 | 模式×1 + 方法×2 |
| Draft 比例 | 5/6 (83%) | 仅 pytorch-operator-reference 为 reviewed |
| 未知许可证来源 | 1/3 | tuning-guide 仓库无明确许可证 |
| version-claims | 0 条 | **空** — 无版本声明 |
| version-matrix | 0 组合 | **空** — 无可追溯版本组合 |
| 页面类型 | doc×2, repo×1, pattern×1, recipe×2 | 缺 tool/migration/kernel 类型 |

**关键缺口**:
- mxmaca 编译器 (mxcc)、运行时、profiler 无独立页面
- 版本信息完全缺失，所有页面标记 `mxmaca_versions: ["unspecified"]`
- 无入门教程、排障指南、API 参考等覆盖

---

## 7. 来源可追溯性: ✅

每个 wiki 页面可追溯至来源：

```
pattern-establish-performance-baseline → repo-mxmaca-performance-tuning-guide (main@65a3f76)
evaluation-compare-operator-backends   → doc-pytorch-operator-reference + repo-mxmaca-performance-tuning-guide
recipe-verify-mxmaca-environment       → doc-mxmaca-quick-start
```

来源均记录 URL、许可证状态、检索日期和提取策略。`unknown` 许可证的来源仅保存元数据和摘要。

---

## 8. 评测方法总结

### 已有评测手段

| 方法 | 类型 | 覆盖 |
|------|------|------|
| `validate.py` | 静态 schema + 词表校验 | 14 个字段，8 种页面类型 |
| `test_repository.py` | 9 个单元测试 | 查询、别名、安装、算子列表 |
| `run_agent_value_eval.py` | 确定性检索 + 证据代理 | 3 个 case，仅正向检索 |
| `compare_benchmarks.py` | 基线/候选对比 | 环境指纹 + 正确性 + timing（无 schema 校验） |
| `doctor.py` | 环境就绪检查 | Python、文件、corpus、索引、PyTorch 可选 |
| `repo_status.py` | 语料统计 | 页面数、类型、状态、置信度分布 |

### 缺失评测手段

| 方法 | 重要性 | 阻塞条件 |
|------|--------|---------|
| Claude A/B (loaded vs unloaded) | 🔴 核心 | 需付费授权 + `run_claude_ab_eval.py` 未建 |
| Negative-trigger 防护 | 🟡 高 | `run_agent_value_eval.py` 不支持 |
| 版本/引用一致性 lint | 🟡 高 | 未实现 |
| C500 硬件正确性回归 | 🟡 高 | 需 C500 环境 |
| 上下游生态任务 (mcPytorch/vLLM) | 🟢 中 | 环境 + 授权 |
| 来源新鲜度检查 | 🟢 低 | 未实现 |

---

## 9. 结论与建议

### 当前质量总结

Macawiki v0.3 基线版本（`3b1e9a6`）通过所有确定性测试，来源可追溯链完整。但评估面过窄：

- **Agent 价值证据**: 仅靠 3 个正向检索 case 证明价值，缺少负向防护、禁止声明和多页面综合验证
- **代码缺陷**: `tl_quantize` 存在未被硬件测试发现的静态缺陷
- **语料覆盖**: 6 页仅覆盖 3 个来源，版本数据完全空白
- **评测缺口**: 缺少真实 Claude A/B 评测、negative-trigger 防护和 benchmark schema 校验

### 优先级建议

1. **P0**: 修复 `tl_quantize` accum 缺陷 + 加强 `compare_benchmarks.py` schema 校验
2. **P0**: 增加 negative-trigger 和 forbidden-claim 测试到 agent-value-eval
3. **P1**: 扩充 sources/wiki 覆盖 mxcc、runtime、profiler
4. **P1**: 填充 version-claims 和 version-matrix
5. **P2**: 建设 Claude A/B eval runner（需付费授权）

> ⚠️ 以上建议已在 PR #3 (`issue2-iteration` 分支) 中实现了 Phase 1 的 5 个 cycle，等待合入 master。
