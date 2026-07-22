# Macawiki

Macawiki 是面向 MXMACA 社区和 AI Agent 的可追溯知识库。项目借鉴 KernelWiki 的证据层、知识层和生成索引模式，但使用适合 MXMACA 软件栈、工具链、框架与 Kernel 优化的领域模型。

当前版本为 **v0.3 agent-ready foundation**：提供数据契约、可追溯公开来源、Codex/Claude Code Skill、查询与验证工具，以及不依赖 C500 的算子评估脚手架。它不是 MXMACA 官方文档的镜像，也不替代官方文档。

## 快速开始

知识库工具仅使用 Python 标准库，无需安装第三方依赖。

```bash
python3 scripts/validate.py
python3 scripts/query.py "性能优化" --compact
python3 scripts/get_page.py pattern-establish-performance-baseline --follow-sources
python3 scripts/generate_indices.py --check
python3 -m unittest discover -s tests -v
```

## 安装到 Agent

当前仓库已经包含 `.agents/skills/macawiki`（Codex）与 `.claude/skills/macawiki`（Claude Code）适配器。在本仓库启动对应 Agent 即可发现 Skill。

安装为用户级 Skill，供其他项目复用：

```bash
# 开发方式：链接当前仓库，更新立即生效
python3 scripts/install.py --agent both --scope user --mode symlink

# 发布方式：复制一个独立快照
python3 scripts/install.py --agent both --scope user --mode copy

python3 scripts/doctor.py
```

完整的安装、升级、卸载与故障排查见 [安装指南](docs/installation.md)，常见提问方式见 [使用指南](docs/usage.md)。

## 内容模型

- `sources/`：忠实记录单一公开来源的元数据与摘要。
- `wiki/`：基于来源形成可执行、带版本范围的综合知识。
- `queries/`：根据 frontmatter 自动生成的导航索引。
- `data/`：schema、词表、别名、来源注册表和版本声明。
- `candidates/`：候选来源的 include/defer/exclude 决策。
- `scripts/`：查询、页面读取、索引生成和验证工具。
- `benchmarks/`：PyTorch 基线、后续 TileLang/MXMACA++ 实现契约和结果格式。
- `evals/`：Agent 检索价值与回答约束的离线评估。

## 当前边界

- 只纳入公开页面的最小摘要与链接。
- 示例中的版本未知时明确标为 `unspecified`。
- 不复制官方文档附件，不批量抓取仓库，不保存许可证不明的代码资产。
- 所有性能知识均为方法性说明，没有独立 Benchmark 就不标记为已验证。
- 当前环境没有 C500 与 MXMACA；仓库不包含任何伪造性能数字。CPU 上的 PyTorch 运行只验证评估流程，不代表 C500 性能。

详细治理规则见 [AGENTS.md](AGENTS.md)，Agent 使用方式见 [SKILL.md](SKILL.md)，数据契约见 [references/schema.md](references/schema.md)，后续硬件验证门禁见 [评估计划](docs/hardware-validation.md)。

## 公开参考入口

- [MXMACA 官方文档中心](https://developer.metax-tech.com/doc)
- [MetaX-MACA Gitee 组织](https://gitee.com/metax-maca)
- [MXMACA Performance Optimization Guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)
- [KernelWiki](https://github.com/mit-han-lab/KernelWiki)

## 许可证

仓库自身代码与文档遵循根目录 `LICENSE`。外部来源和资产仍受各自许可证与使用条款约束；Macawiki 的索引或摘要不改变上游权利。
