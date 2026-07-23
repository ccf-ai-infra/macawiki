# 贡献指南

Macawiki 欢迎对 MXMACA 知识库的贡献。本文档说明如何添加来源、编写知识页面、提交算子案例和创建 PR。

## 快速开始

1. 阅读 [README.md](README.md) 了解项目背景和内容模型
2. 阅读 [AGENTS.md](AGENTS.md) 了解安全规则和语料库约束
3. 运行 `make all` 确认当前状态为绿色
4. 保持改动小而聚焦——一个 PR 只做一件事

## 检查命令

提交 PR 前必须运行以下命令并通过：

```bash
make all                    # validate + generate indices + unittest + agent-value eval + doctor + repo_status
git diff --check            # 无空白字符错误
```

对于新增语料库内容的 PR，额外运行：

```bash
python3 scripts/generate_indices.py --check   # 索引必须为最新
python3 scripts/run_agent_value_eval.py       # 所有 agent-value cases 必须通过
python3 scripts/repo_status.py                # 检查页面数量和类型分布
```

## 内容类型与元数据要求

### Wiki 页面（`wiki/`）

| 字段 | 必需 | 说明 |
|------|------|------|
| `id` | 是 | 小写字母数字+连字符，如 `pattern-establish-performance-baseline` |
| `type` | 是 | `wiki-pattern` / `wiki-recipe` / `wiki-tool` / `wiki-reference` / `wiki-migration` |
| `status` | 是 | `draft` / `reviewed` / `deprecated` / `superseded` |
| `mxmaca_versions` | 是 | 明确版本列表或 `["unspecified"]` |
| `confidence` | 是 | `verified` / `source-reported` / `corroborated` / `inferred` / `experimental` |
| `sources` | 是（≥1） | 引用来源 ID 列表 |
| `languages` | 是 | ISO 语言代码 |
| `tags` | 推荐 | 受控词表（见 `data/tags.yaml`） |
| `components` | 推荐 | 受控词表（见 `data/aliases.yaml`） |
| `hardware` | 条件 | 如涉及特定硬件 |
| `prerequisites` | 条件 | 前置页面 ID 列表 |
| `verified_at` | 条件 | 最后审查日期 |

### 来源记录（`sources/`）

| 字段 | 必需 | 说明 |
|------|------|------|
| `id` | 是 | 如 `doc-mxmaca-quick-start` / `repo-mcpytorch` |
| `type` | 是 | `source-doc` / `source-repo` |
| `url` | 是 | 公开 URL（https 优先） |
| `title` | 是 | 人类可读标题 |
| `summary` | 是 | 一句话范围描述 |
| `retrieval_date` | 是 | YYYY-MM-DD |
| `license_status` | 是 | `known`（附许可证名） / `unknown` / `pending` |
| `mxmaca_versions` | 是 | 明确版本或 `["unspecified"]` |
| `tags` | 推荐 | 受控词表 |
| `components` | 推荐 | 受控词表 |

### 算子案例（`benchmarks/operator_cases.yaml`）

| 字段 | 必需 | 说明 |
|------|------|------|
| `name` | 是 | 算子名（add, matmul 等） |
| `case_id` | 是 | 如 `add-f32-4096` |
| `shape` | 是 | 整数数组 |
| `dtype` | 是 | 与 `cases["dtype"]` 保持一致 |
| `parameters` | 是 | 算子特定参数 |
| `tolerance` | 是 | `atol` + `rtol` |
| `contract` | 条件 | 如 transpose 的 materialized 要求 |

### 评测结果（`benchmarks/results/`）

| 字段 | 必需 | 说明 |
|------|------|------|
| `schema_version` | 是 | 当前为 1 |
| `status` | 是 | `completed` / `not_comparable` |
| `environment` | 是 | 硬件/软件环境指纹 |
| `provenance` | 是 | git commit、运行命令、采集时间 |
| `cases` | 是 | 每个 case 的正确性+计时结果 |

## 添加 Wiki 页面的工作流

1. **先创建来源记录**：在 `sources/` 中添加新文件或在 `data/source-registry.yaml` 中注册
2. **编写综合页面**：在 `wiki/` 中创建页面，引用至少一个来源 ID
3. **更新别名/标签**：如需新术语，编辑 `data/aliases.yaml` 或 `data/tags.yaml`
4. **运行检查**：`make all`
5. **提交 PR**：附带来源引用、版本范围和验证输出

## 添加算子案例的工作流

1. **更新 case 定义**：在 `benchmarks/operator_cases.yaml` 中添加条目
2. **添加实现**：在 `benchmarks/pytorch_baseline.py` 的 `_run_op()` 和 `benchmarks/tilelang_candidate.py` 的 `_reference()` 中添加分支
3. **添加 TileLang kernel**：在 `tilelang_candidate.py` 的 `_load_tilelang_backend()` 中添加 kernel 定义
4. **运行 CPU smoke test**：
   ```bash
   python3 benchmarks/pytorch_baseline.py --operator <name> --device cpu --correctness-only
   ```
5. **在 C500 环境到位后**：运行完整 profile 并保存结果到 `benchmarks/results/`
6. **更新文档**：在 `docs/hardware-validation.md` 中更新算子状态表

## 单一事实来源原则

- 同一事实只在一处权威位置维护
- 硬件状态以 `docs/hardware-validation.md` 为准
- 版本信息以 `data/version-claims.yaml` 和 `data/version-matrix.yaml` 为准
- 基准结果以 `benchmarks/results/` 下 JSON 为准
- 其他文档只能引用，不能复制定义
- 生成文件（`queries/` 目录）从不手动编辑

## 生成文件规则

| 文件/目录 | 生成器 | 何时更新 | 验证方式 |
|-----------|--------|---------|---------|
| `queries/*.md` | `scripts/generate_indices.py` | 添加/删除/修改页面后 | `--check` 标志 |

## PR 检查清单

提交 PR 前逐项确认：

- [ ] `make all` 通过（validate + indices + test + eval + doctor + status）
- [ ] `git diff --check` 干净
- [ ] 新增页面：索引已重新生成，agent-value eval 通过
- [ ] 新增来源：包含 URL、许可证状态和检索日期
- [ ] 新增 wiki 页面：至少引用一个来源 ID，声明版本范围和置信度
- [ ] 新增算子案例：在 `_run_op` 和 `_reference` 中均有实现
- [ ] 所有版本敏感声明标注了版本范围（不推断）
- [ ] 未引入虚构性能数字
- [ ] 未假设 CUDA 行为等价于 MXMACA
- [ ] 生成文件未手动编辑
- [ ] 不确定的事实标记为 `unspecified` / `not_run` / `not_comparable`
- [ ] 无空正文或占位符页面（正文至少 50 字符）
- [ ] 查询召回率未下降（`make recall` 达标，阈值 ≥ 70%）
- [ ] PR 标题格式：`type: description`（feat: / fix: / docs: / refactor: / test: / chore:）
- [ ] PR 正文：变更摘要 + 验证输出 + 未解决问题

## 质量门控（advisory）

以下门控通过 `make quality`、`make coverage`、`make recall`、`make freshness` 单独运行，当前为 advisory（不阻塞 PR），待 corpus 成熟后将逐步集成到 `make all`：

| 门控 | 命令 | 说明 |
|------|------|------|
| 质量门控 | `make quality` | draft 比例、unspecified 版本比例、verified 置信度比例 |
| 覆盖度报告 | `make coverage` | 受控词汇表覆盖度缺口 |
| 召回率检查 | `make recall` | 基于 gold questions 的检索召回率 |
| 来源新鲜度 | `make freshness` | URL 可达性、检索日期过期、许可证状态 |

## 审查流程

1. 贡献者提交 PR
2. CI 运行 `make all`（validate + indices + test + eval + doctor + status）
3. 审查者检查来源可追溯性（每个 wiki 声明追溯至来源 ID）
4. 审查者检查版本声明准确性（不推断，不编造）
5. 审查者检查无伪造数字
6. 审查者检查生成文件未手动编辑
7. 审查者检查页面正文非空（≥ 50 字符）
8. 通过后 squash-merge 到 master

## 状态术语

全仓库统一使用以下状态术语（权威定义见 `docs/hardware-validation.md`）：

| 术语 | 含义 |
|------|------|
| `verified` | 在目标硬件上通过正确性+计时门禁 |
| `recorded` | 仓库有带环境指纹+来源信息的历史结果 |
| `implemented` | 代码/案例存在，未在目标环境验证 |
| `not_run` | 已定义契约/计划，尚未在目标环境执行 |
| `not_comparable` | 环境/实现不同，禁止比较 |

## 行为准则

所有贡献者须遵守仓库的 [AGENTS.md](AGENTS.md) 安全与范围规则。仅使用公开来源；不复制访问受限、保密或许可证不明的文档；不编造或推断未验证的性能数据。
