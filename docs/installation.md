# 安装与升级

Macawiki 同时是可独立审阅的知识库和按需加载的 Agent Skill。查询工具只要求 Python 3.9+；只有运行 PyTorch 基线时才需要 PyTorch。

## 1. 获取并检查仓库

```bash
git clone <macawiki-repository-url>
cd macawiki
python3 scripts/doctor.py
make all
```

`doctor.py` 会检查目录、数据、生成索引和可选的 PyTorch，不会安装驱动、SDK 或 Python 包。

## 2. 在当前仓库使用

仓库已经提交两个轻量适配器：

- Codex：`.agents/skills/macawiki/SKILL.md`
- Claude Code：`.claude/skills/macawiki/SKILL.md`

从仓库根目录启动 Agent。Codex 可用 `$macawiki` 显式激活；Claude Code 可用 `/macawiki`，也可通过匹配描述自动加载。根目录 `AGENTS.md` 和 `CLAUDE.md` 提供常驻的最低限度约束，完整知识仅在需要时读取。

## 3. 安装为用户级 Skill

让所有项目都能发现 Macawiki：

```bash
# 推荐给知识库维护者：链接工作树
python3 scripts/install.py --agent both --scope user --mode symlink

# 推荐给固定版本使用者：复制快照
python3 scripts/install.py --agent both --scope user --mode copy
```

安装目标遵循当前官方约定：Codex 为 `~/.agents/skills/macawiki`，Claude Code 为 `~/.claude/skills/macawiki`。可先用 `--dry-run` 查看动作。若目标已经存在，安装器默认拒绝覆盖；人工确认后才可加 `--replace`。

## 4. 安装到另一个项目

```bash
python3 scripts/install.py \
  --agent both \
  --scope project \
  --project-dir /path/to/your/project \
  --mode symlink
```

项目级目标分别为 `.agents/skills/macawiki` 和 `.claude/skills/macawiki`。不要对 Macawiki 自身运行项目级安装，它已包含适配器。

## 5. 验证 Agent 是否加载

向 Agent 提问：

```text
使用 macawiki，说明开始优化 C500 算子前必须冻结哪些基线条件；给出页面 ID、来源 ID、版本范围，并明确当前哪些结论还不能下。
```

合格回答应命中 `pattern-establish-performance-baseline`，引用 `repo-mxmaca-performance-tuning-guide`，并拒绝给出当前仓库没有的性能数字。

## 6. 升级与回退

- `symlink` 安装：切换仓库 tag/commit 后立即生效；升级前后都运行 `make all`。
- `copy` 安装：先审阅新版本，再用相同命令加 `--replace` 复制新快照。
- 回退：切回已审阅 tag（symlink），或从已保存版本重新执行 copy 安装。
- 卸载：先用 `python3 scripts/install.py ... --dry-run` 确认目标，再人工删除目标中的单个 `macawiki` 目录。安装器故意不自动递归卸载。

## 7. 故障排查

- Skill 未出现：确认启动目录、目标路径和 `SKILL.md`，然后重启 Agent。
- 查询无结果：减少关键词，或使用 `scripts/grep_wiki.py` 搜索符号和错误文本。
- 索引过期：运行 `python3 scripts/generate_indices.py`，然后重新验证。
- PyTorch 不存在：知识库仍可用；仅基线运行被跳过。请在后续 C500 验证环境按官方软件栈安装。

参考：[Codex Build skills](https://learn.chatgpt.com/docs/build-skills)、[Claude Code Extend Claude with skills](https://code.claude.com/docs/en/slash-commands)。安装路径属于外部工具约定，升级 Agent 后应重新核对官方文档。
