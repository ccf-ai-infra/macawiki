# 使用指南

## 最短工作流

```bash
python3 scripts/query.py "算子 性能基线" --compact
python3 scripts/get_page.py evaluation-compare-operator-backends --follow-sources
python3 scripts/grep_wiki.py "TileLang|MXMACA\+\+|torch.matmul"
```

回答时同时输出：页面 ID、来源 ID/URL、硬件与软件版本范围、置信度，以及仍缺少的验证。

## 给 Codex 的示例

```text
$macawiki 为 matmul 设计 PyTorch、TileLang、MXMACA++ 三后端对比。
先检索仓库，引用页面和公开来源；当前没有 C500，所以只生成运行计划和命令，不能生成性能数值。
```

## 给 Claude Code 的示例

```text
/macawiki 检查这个 MXMACA 算子优化方案是否具备可比较的基线。
列出缺失的环境、正确性、计时和溯源字段，不要把 CUDA 假设当成 MXMACA 事实。
```

## 典型任务

### 环境排障

先命中 `recipe-verify-mxmaca-environment`，再按它指向的官方快速上手来源核对当前版本，避免给出“所有版本通用”的安装命令。

### 性能评审

先命中 `pattern-establish-performance-baseline`，检查硬件、软件、形状、dtype、布局、预热、同步、重复次数和统计量是否一致，再讨论优化。

### 三后端算子评估

先读 `evaluation-compare-operator-backends` 和 `benchmarks/README.md`。本地无 C500 或仅作流程检查时可以：

1. 审阅算子、形状、容差和结果 schema；
2. 运行 PyTorch CPU 流程检查；
3. 填写 TileLang/MXMACA++ 后端契约；
4. 将结果保持为 `not_run`。

只有后续在同一 C500 环境完成三后端正确性与计时，才允许计算 speedup。

## 离线价值演练

```bash
python3 scripts/run_agent_value_eval.py
```

它验证“加载 Macawiki 后能否找到预期页面、证据、版本范围和禁止断言”。这不是大模型能力排行榜，也不声称未加载 Agent 一定答错；它证明的是仓库向 Agent 提供了可机器检查的证据包和安全边界。
