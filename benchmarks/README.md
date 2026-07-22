# 三后端算子评估脚手架

本目录定义同一组 PyTorch、TileLang、MXMACA++ 算子比较的输入契约和结果格式。PyTorch 基线与 TileLang 候选已在 MetaX C500 上实测，结果见 `results/`（同环境相对计时，非官方规格；环境指纹与运行命令随结果 JSON 保存）。MXMACA++ 后端尚未接入。

## 统一契约

每个 case 必须固定：`case_id`、算子、shape、dtype、布局、seed、输入分布、容差、warmup、iterations、同步策略和环境指纹。后端必须输出同一 schema 的 JSON；`status` 可为 `completed`、`not_run` 或 `not_comparable`。

PyTorch 是参考实现，不等于“最快实现”。TileLang 和 MXMACA++ 只有在 C500 环境到位后才填入真实结果。

```bash
python3 benchmarks/pytorch_baseline.py --list
python3 benchmarks/pytorch_baseline.py --operator add --device cpu --correctness-only
python3 benchmarks/pytorch_baseline.py --operator all --profile smoke --device cpu --output /tmp/pytorch.json
python3 scripts/compare_benchmarks.py --baseline /tmp/pytorch.json --candidate results/tilelang.json
```

## 选取的 PyTorch 算子

- `add`：逐元素、带宽受限的最小案例。
- `softmax`：行归约与数值稳定性。
- `layer_norm`：归约、仿射参数和常见模型路径。
- `matmul`：计算密集型库调用与自定义 kernel 对比。

这些算子都由 PyTorch 提供；case 规格见 `operator_cases.yaml`。

## 后端状态

`backends/tilelang_contract.yaml` 与 `backends/mxmacacpp_contract.yaml` 描述后续实现必须满足的输入、构建、同步、正确性和输出要求。它们故意不包含无法在当前环境验证的 API 或性能数字。
