# porting-ab: torch-scatter 移植 A/B 实验

端到端测量 Macawiki 对 Agent 的收益：同一个移植任务，A 组无 Macawiki skill、
B 组挂载 Macawiki skill（`--mode copy` 快照），在真实 C500 上对比结果。

本目录是**语料外实验区**：所有结果状态为 `recorded`、`reviewed: false`。
只有经维护者人工审查后，验证过的移植经验才可按 AGENTS.md 规则进入
`sources/` / `wiki/`；绝不自动赋予 `verified`。

## 设计

| 维度 | 取值 |
|------|------|
| 基线软件 | torch-scatter @ `f514c10f920b5aeed2eb162092f0ad20d3edee52`（未适配 MACA，不在本地 pip 与语料中） |
| 任务提示词 | `task.yaml` 中 `prompt` 字段，两组逐字相同，不提 Macawiki |
| 唯一自变量 | B 组 worktree 内安装 `.agents/skills/macawiki`（copy 快照） |
| Agent | codebuddy CLI 无头模式，固定 `--model`，`--max-turns 120`，`--no-session-persistence` |
| 隔离 | worktree 在 `/root/porting-ab-workspaces/<run-id>/`（仓库外）；fresh session-id；用户级无 macawiki skill（已核实）；A 组不加 `--add-dir` |
| 串行 | 单卡 C500，两组必须串行执行 |
| 提示词泄露控制 | prompt 只给最小环境事实；cu-bridge/CUCC_* 约定刻意保留（见 `task.yaml` 的 `environment_facts_deliberately_withheld`），这是 Macawiki 独有的关键知识 |

## 门控（映射 docs/hardware-validation.md 六门）

1. `environment` — `scripts/capture_environment.py` 指纹写入 `runs/<run-id>/environment.json`
2. `build` — `python3 -c "import torch_scatter"` 成功
3. `correctness` — 上游 `pytest test/` 退出码 0（skip 允许，断言不可改）
4. `timing` — 上游 `benchmark/` 脚本产出含 warmup+同步的计时日志
5. `comparability` — 两组环境指纹一致才比较；只比门控/耗时/token，不跨组比加速比
6. `conclusion` — 任一门控失败 → `not_run`/`not_comparable`；永不 `verified`

过程指标：wall time、turns、tokens（codebuddy JSON 输出）、tool 调用数、
B 组 Macawiki 查询次数（`runs/<run-id>/signals/query-log.jsonl`，由
`MACAWIKI_SIGNAL_DIR` 定向）。

## 使用

```bash
python3 scripts/run_porting_ab_eval.py --dry-run --group A      # 打印全部命令
python3 scripts/run_porting_ab_eval.py --group A                # 跑 A1（--repetition 2 跑 A2）
python3 scripts/run_porting_ab_eval.py --group B                # 跑 B1
python3 scripts/run_porting_ab_eval.py --group A --gates-only   # 只对已有 worktree 重跑门控
```

已知噪声控制：benchmark 用的 4 个 SuiteSparse 矩阵（约 560MB）在首次成功下载后
缓存于 `<workspaces>/cache/mats/`，新 worktree 会自动预置，避免慢速网络
污染 agent 阶段耗时（b1 曾花约 1.5h 下载）。门控只跑上游两个 benchmark
脚本（`gather.py`、`scatter_segment.py --reduce sum`），agent 自建脚本不计入门控。
agent 输出用 `stream-json` 事件流采集，超时被杀也能保留会话轨迹与 usage。

产物：

```
task.yaml                     # 固定任务定义（pin 的 commit、prompt）
manifests/<run-id>.yaml       # 运行清单（group、repetition、env 指纹、命令）
runs/<run-id>/                # session-stream.jsonl（stream-json 事件流）、门控日志、signals/
results/<run-id>.yaml         # 六门结果 + 过程指标，status: recorded, reviewed: false
reports/report-<date>.md      # 人工聚合报告
```
