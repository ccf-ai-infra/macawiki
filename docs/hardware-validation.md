# C500 算子验证计划

C500 与 MXMACA 已就绪。`benchmarks/results/` 下保存了在 MetaX C500 上实测的 PyTorch 基线与 TileLang 候选结果（环境指纹、硬件型号、MACA/mxcc 版本与运行命令见各 JSON 的 `environment`/`provenance` 字段）。以下门禁仍是一致性的硬约束，不是已完成报告的免责声明：matmul 因 TileLang/maca codegen 差距标记为 `not_comparable`，其余算子为同环境相对计时，非官方 C500 规格。

## 目标与基线算子

| 算子 | PyTorch 参考 | 主要行为 | 初始价值 |
|---|---|---|---|
| `add` | `torch.add` | 逐元素、内存带宽 | 最小 bring-up 与计时校验 |
| `softmax` | `torch.softmax` | 归约与数值稳定性 | 验证同步、精度和行长度影响 |
| `layer_norm` | `torch.nn.functional.layer_norm` | 归约、仿射、融合机会 | 覆盖常见模型算子 |
| `matmul` | `torch.matmul` | 计算密集、库与自定义核对比 | 检查形状和 dtype 的性能边界 |

参考接口：[torch.add](https://docs.pytorch.org/docs/stable/generated/torch.add.html)、[torch.softmax](https://docs.pytorch.org/docs/stable/generated/torch.softmax.html)、[LayerNorm](https://docs.pytorch.org/docs/stable/generated/torch.nn.LayerNorm.html)、[torch.matmul](https://docs.pytorch.org/docs/stable/generated/torch.matmul.html)。

## 门禁顺序

1. **环境门禁**：保存硬件、驱动、MXMACA、mxcc、PyTorch、mcTileLang 和源码 commit。
2. **构建门禁**：记录完整命令、编译选项、返回码和日志。
3. **正确性门禁**：使用相同 seed/shape/dtype/input distribution，以 PyTorch 输出为 reference，报告最大绝对/相对误差和 allclose。
4. **计时门禁**：完成预热；每次计时前后使用目标栈确认过的同步方式；保存所有样本而非只有最优值。
5. **可比性门禁**：三后端必须来自同一机器、同一软件栈、同一输入契约。任一条件不一致时禁止计算 speedup。
6. **结论门禁**：正确性失败、环境缺失或样本不足时，结论保持 `not_comparable`。

## 运行阶段

无 C500 的开发机：

```bash
python3 benchmarks/pytorch_baseline.py --list
python3 benchmarks/pytorch_baseline.py --operator add --device cpu --correctness-only
python3 scripts/run_agent_value_eval.py
```

C500 环境到位后，先执行：

```bash
python3 scripts/capture_environment.py --output results/environment.json
python3 benchmarks/pytorch_baseline.py \
  --operator all --device <validated-device> \
  --warmup 20 --iterations 100 \
  --output results/pytorch.json
```

再根据 `benchmarks/backends/` 契约接入 TileLang 和 MXMACA++。设备字符串、同步方式、编译器参数和 API 必须现场探测，不能从 CUDA 环境类推。

## 报告

必须同时保留：环境 JSON、每后端结果 JSON、源码/ref、运行命令和错误日志。`scripts/compare_benchmarks.py` 只在环境指纹、case ID、shape 和 dtype 一致且正确性通过时输出相对值。
