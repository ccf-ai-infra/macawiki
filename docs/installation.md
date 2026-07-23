# 安装与升级

Macawiki 同时是可独立审阅的知识库和按需加载的 Agent Skill。查询工具只要求 Python 3.9+；只有运行 PyTorch 基线时才需要 PyTorch。

## 前置条件

| 条件 | 版本要求 | 验证命令 | 必需/可选 |
|------|----------|----------|-----------|
| Git | 任意现代版本 | `git --version` | 必需 |
| Python | ≥ 3.9 | `python3 --version` | 必需 |
| Claude Code | 最新（支持 Skills） | `claude --version` | 使用 Claude Code 时必需 |
| Codex (ChatGPT) | 支持 Skills 的版本 | 见 ChatGPT 设置 | 使用 Codex 时必需 |
| PyTorch | ≥ 2.0 | `python3 -c "import torch; print(torch.__version__)"` | 仅运行基线时需要 |
| TileLang | 最新（MetaX 构建） | `python3 -c "import tilelang; print(tilelang.__version__)"` | 仅运行 TileLang 候选时需要 |

> ⚠️ 已测试平台：Linux 5.15.0-58-generic (x86_64, Ubuntu 22.04), Python 3.12.11, MACA 3.7.1.5（MetaX C500）。未标注"已验证"的平台不代表不可用，但安装路径与命令行为可能与文档描述不同。

## 1. 获取并检查仓库

```bash
git clone https://www.gitlink.org.cn/ccf-ai-infra/macawiki.git
cd macawiki
python3 scripts/doctor.py
make all
```

`doctor.py` 会检查 Python 版本、必需文件、语料库完整性、生成索引和可选的 PyTorch，不会安装驱动、SDK 或 Python 包。

预期输出：`Macawiki doctor: READY` — 5/5 checks pass。

## 2. 在当前仓库使用

仓库已经提交两个轻量适配器：

- Codex：`.agents/skills/macawiki/SKILL.md`
- Claude Code：`.claude/skills/macawiki/SKILL.md`

### Claude Code

从仓库根目录启动 Claude Code，输入 `/macawiki` 显式激活 Skill，或等待描述匹配后自动加载。根目录 `CLAUDE.md` 提供常驻的最低限度约束（不编造基准、声明硬件/版本/置信度）。

### Codex (ChatGPT)

从仓库根目录启动 Codex，在对话中输入 `$macawiki` 显式激活。根目录 `AGENTS.md` 提供常驻约束（来源规则、语料库规则、检查清单）。

## 3. 安装为用户级 Skill

让所有项目都能发现 Macawiki，而非仅限当前仓库。

### symlink 方式（推荐给知识库维护者）

```bash
python3 scripts/install.py --agent both --scope user --mode symlink
```

- 仓库 `git pull` 或切换 tag/commit 后立即生效。
- 升级前后运行 `make all` 确保一致性。
- 目标：Claude Code → `~/.claude/skills/macawiki`，Codex → `~/.agents/skills/macawiki`。

### copy 方式（推荐给固定版本使用者）

```bash
python3 scripts/install.py --agent both --scope user --mode copy
```

- 安装时锁定内容快照，不受后续仓库变更影响。
- 升级：审阅新版本后加 `--replace` 重新安装。
- 回退：从已保存版本目录重新执行 copy 安装。

### symlink vs copy 选择指南

| 条件 | symlink | copy |
|------|---------|------|
| 更新生效 | 立即（跟随仓库） | 仅重新安装后 |
| 磁盘占用 | 极小（仅链接） | 完整快照 |
| 是否可编辑目标 | 否（编辑影响源） | 是（独立副本） |
| 适用场景 | 活跃开发、频繁更新 | CI 流水线、稳定发布 |

### 仅安装到一个 Agent

```bash
# 仅 Claude Code
python3 scripts/install.py --agent claude --scope user --mode symlink

# 仅 Codex
python3 scripts/install.py --agent codex --scope user --mode copy
```

### 安全检查

- `--dry-run` 预览安装动作而不写任何文件：
  ```bash
  python3 scripts/install.py --agent both --scope user --mode symlink --dry-run
  ```
- 若目标已存在，安装器默认拒绝覆盖（`FileExistsError`）。审阅后用 `--replace` 强制替换：
  ```bash
  python3 scripts/install.py --agent both --scope user --mode copy --replace
  ```

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

### Claude Code

在 Claude Code 会话中输入：

```text
/macawiki 说明开始优化 C500 算子前必须冻结哪些基线条件
```

**通过标准**：
- 回答命中 `pattern-establish-performance-baseline`
- 引用 `repo-mxmaca-performance-tuning-guide` 来源
- 列出硬件、软件、输入形状、计时条件四类基线
- 拒绝给出当前仓库没有的性能数字

### Codex

在 Codex 会话中输入：

```text
$macawiki 如何核对 MXMACA 环境可用性
```

**通过标准**：
- 回答命中 `recipe-verify-mxmaca-environment`
- 引用 `doc-mxmaca-quick-start` 来源
- 给出版本化命令，而非通用安装指令
- 标注不确定的版本范围为 `unspecified`

## 6. Smoke Test（自动化）

运行以下命令快速验证仓库完整性：

```bash
# 1. 结构检查
python3 scripts/doctor.py
# 预期: Macawiki doctor: READY (5/5 checks pass)

# 2. 页面临检
python3 scripts/validate.py
# 预期: 无错误

# 3. 查询功能
python3 scripts/query.py "性能基线" --compact
# 预期: 包含 pattern-establish-performance-baseline 页面

# 4. 索引状态
python3 scripts/generate_indices.py --check
# 预期: 索引为最新

# 5. 单元测试
python3 -m unittest discover -s tests -v
# 预期: OK (38 tests, 3 项因无 PyTorch 跳过)

# 6. Agent 价值演练
python3 scripts/run_agent_value_eval.py
# 预期: 9/9 passed

# 7. 全量检查
make all
# 预期: 所有子命令通过
```

| 检查项 | 通过条件 |
|--------|----------|
| doctor.py | exit code 0，输出 "READY" |
| validate.py | exit code 0，无错误输出 |
| query.py | 包含 pattern-establish-performance-baseline |
| generate_indices.py | 索引为最新 |
| unittest | exit code 0，all pass |
| agent value eval | exit code 0，9/9 pass |
| make all | exit code 0 |

## 7. 升级与回退

### symlink 安装

```bash
# 升级
cd /path/to/macawiki
git pull
make all
# 重启 Agent 即生效

# 回退到特定版本
git checkout v0.3.0
make all
```

### copy 安装

```bash
# 升级：审阅新版本后重新安装
python3 scripts/install.py --agent both --scope user --mode copy --replace

# 回退：从之前保存的副本重新安装
python3 scripts/install.py --agent both --scope user --mode copy --replace --source /path/to/saved/version
```

## 8. 卸载

安装器不提供自动递归卸载命令，以人工确认保护用户数据。

### symlink 安装卸载

```bash
rm ~/.claude/skills/macawiki    # Claude Code
rm ~/.agents/skills/macawiki    # Codex
```

### copy 安装卸载

```bash
rm -rf ~/.claude/skills/macawiki
rm -rf ~/.agents/skills/macawiki
```

### 验证卸载

重启 Agent 后输入 `/macawiki` 或 `$macawiki`，应返回"Skill 未找到"或等效提示。

## 9. 故障排查

| 现象 | 可能原因 | 解决方案 |
|------|----------|----------|
| Skill 未出现在 Agent 命令列表中 | 启动目录不是仓库根目录 | 确认在 `macawiki/` 下启动 Agent |
| Skill 未出现 | 目标路径不存在或被删除 | 检查 `~/.claude/skills/macawiki/SKILL.md` 或 `~/.agents/skills/macawiki/SKILL.md` 是否存在；重新安装 |
| Skill 未出现 | 安装后未重启 Agent | 重启 Agent 会话 |
| 查询无结果 | 关键词太具体（AND 语义） | 减少关键词数量，或使用 `scripts/grep_wiki.py` 搜索 |
| 查询无结果 | 索引过期 | `python3 scripts/generate_indices.py` 重新生成 |
| `doctor.py` 报 PyTorch not found | 环境中无 PyTorch | 知识库功能不受影响，仅基线运行被跳过 |
| `install.py` 报 "target exists" | 已安装过 | 审阅后加 `--replace` 重新安装 |
| `install.py` 报 "source has no SKILL.md" | 源码路径不正确 | 确认 `--source` 指向仓库根目录 |
| symlink 方式查询返回旧知识 | 仓库处于旧版本 | `git pull` 后 `make all` |
| copy 方式查询返回旧知识 | 快照未更新 | 重新执行 copy 安装加 `--replace` |
| 权限拒绝 | `~/.claude/skills/` 或 `~/.agents/skills/` 不可写 | `mkdir -p ~/.claude/skills ~/.agents/skills` |
| C500 结果不可比较 | 环境指纹或输入契约不一致 | 检查 `docs/hardware-validation.md` 中的可比性门禁 |

> 参考：[Claude Code Extend with skills](https://code.claude.com/docs/en/slash-commands)、[Codex Build skills](https://learn.chatgpt.com/docs/build-skills)。安装路径属于外部工具约定，升级 Agent 后应重新核对官方文档。
