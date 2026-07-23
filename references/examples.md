# 查询示例

## 按类型检索

```bash
# 查找诊断或排查方法
python3 scripts/query.py "利用率 诊断" --type wiki-pattern --compact

# 查找入门教程
python3 scripts/query.py "入门" --type wiki-recipe --compact

# 查找工具参考
python3 scripts/query.py "编译" --type wiki-tool --compact
```

## 按硬件过滤

```bash
# 仅 C500 相关内容
python3 scripts/query.py "性能" --hardware c500 --compact

# 通用（不限定硬件）
python3 scripts/query.py "算子" --hardware unspecified --compact
```

## 按组件过滤

```bash
# 编译器相关内容
python3 scripts/query.py "优化" --component mxcc

# 性能分析相关内容
python3 scripts/query.py "profiling" --component mcprofiler

# 算子相关内容
python3 scripts/query.py "tolerance" --component operator-evaluation
```

## 按版本过滤

```bash
# 特定版本
python3 scripts/query.py "API" --version "3.7.1"

# 版本未指定
python3 scripts/query.py "quick start" --version unspecified
```

## 跟踪证据链

```bash
# 读取页面并跟随来源引用
python3 scripts/get_page.py pattern-establish-performance-baseline --follow-sources

# 读取评估页面
python3 scripts/get_page.py evaluation-compare-operator-backends --follow-sources

# 读取环境验证页面
python3 scripts/get_page.py recipe-verify-mxmaca-environment --follow-sources
```

## 全文搜索（符号、错误文本）

```bash
# 搜索 TileLang 或 MXMACA++ 引用
python3 scripts/grep_wiki.py "TileLang|MXMACA\+\+"

# 搜索 warp 或 roofline 相关概念
python3 scripts/grep_wiki.py "roofline|kWarpSize"

# 搜索 quantize 或 transpose 实现
python3 scripts/grep_wiki.py "quantize|transpose|contiguous"

# 搜索编译器相关符号
python3 scripts/grep_wiki.py "mxcc|__builtin_mxc"
```

## 模糊搜索（n-gram Jaccard 相似度）

```bash
# 精确搜索无结果时，使用模糊匹配
python3 scripts/query.py "kernel" "tuning" "roofline" --fuzzy --compact

# 自动回退：精确搜索返回 0 时自动启用模糊模式
python3 scripts/query.py "MXMACA" "BLAS" "优化" --auto-fuzzy --compact
```

`--fuzzy` 使用字符 bigram Jaccard 相似度评分，无需精确子串匹配。适合关键词拼写不精确、跨语言或探索性搜索场景。`--auto-fuzzy` 在精确 AND/OR 返回 0 结果时自动回退。

## 组合查询

```bash
# 查找 C500 上的算子评估
python3 scripts/query.py "算子" --hardware c500 --type wiki-pattern --compact

# 查找环境诊断方法（OR 模式提升召回率）
python3 scripts/query.py "环境 验证" --type wiki-recipe --mode or --compact
```

## 质量门控

```bash
# 快速 pre-commit 检查（仅 validate + test）
make check

# 完整硬性检查（CI 门控）
make all

# Advisory 质量检查（不阻塞合并，用于了解 corpus 健康度）
make check-advisory
make quality      # 质量指标（draft 比例等）
make coverage     # 覆盖度报告
make recall       # 检索召回率
make freshness    # 来源新鲜度
```

## Agent 触发模式

### Claude Code

```text
/macawiki <任意 MXMACA 相关问题>
```

Skill 会通过描述匹配自动加载；也可显式输入 `/macawiki` 激活。

### Codex / OpenCode

```text
$macawiki <任意 MXMACA 相关问题>
```

Skill 通过 `$macawiki` 前缀显式激活，或根据描述自动匹配。OpenCode 与 Codex 共享同一 skill 适配器目录。

### Codex

```text
$macawiki <任意 MXMACA 相关问题>
```

Skill 通过 `$macawiki` 前缀显式激活，或根据描述自动匹配。
