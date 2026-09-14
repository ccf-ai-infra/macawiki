---
{
  "id": "diagnostics-mctracer-basics",
  "title": "mcTracer 追踪工具基础（C500 实测安装证据）",
  "type": "wiki-tool",
  "status": "reviewed",
  "summary": "mcTracer 是 MXMACA 的应用追踪工具。本页给出 C500/MACA 3.7.1.5 上的实测证据，含一个 --version 不报版本、须改用 --help 的实测陷阱。",
  "languages": ["zh-CN"],
  "tags": ["diagnostics", "installation", "profiling"],
  "hardware": ["c500"],
  "mxmaca_versions": ["3.7.1.5"],
  "components": ["mctracer", "mxmaca-sdk", "mxmaca-runtime", "diagnostics"],
  "sources": ["local-c500-maca-sdk-install"],
  "related": ["diagnostics-mcprofiler-basics", "diagnostics-mx-smi", "recipe-verify-mxmaca-environment", "reference-mxcc-compiler-basics"],
  "prerequisites": ["recipe-verify-mxmaca-environment"],
  "verified_at": "2026-09-14",
  "confidence": "source-reported",
  "reproducibility": "procedure",
  "aliases": ["mcTracer", "Tracer", "MXMACA 追踪", "应用追踪"]
}
---

# 概述

mcTracer 是 MXMACA 的应用级追踪工具，用于记录目标程序的运行轨迹。它的调用形态是「追踪选项 + 目标命令」，即把被追踪程序作为 mcTracer 的参数启动，而不是 attach 到已有进程。

> ✅ **证据状态**：本页的安装与版本证据来自 2026-09-14 在 MetaX C500（MACA 3.7.1.5）上的实测捕获，可复现产物见 `benchmarks/results/environment-c500-components.json`（hostname 已脱敏）。

## 实测安装布局（MACA 3.7.1.5 / C500）

| 项 | 值 |
|----|----|
| 可执行文件 | `/opt/maca/bin/mcTracer` |
| 版本 | `3.7.1.5-ef9e10e`（来自 `--help` 输出） |
| 调用形态 | `/opt/maca/bin/mcTracer <trace options> '[target commands]'` |

## 实测陷阱：`--version` 不报版本

这是本页最实用的一条。按惯例用 `--version` 查版本在此工具上**无效**：

```
$ mcTracer --version
(Tracer): 03:07:37 [INFO ] Tracer startup
(Tracer): 03:07:37 [INFO ] User process ends execution.
execvpe: No such file or directory
```

返回码是 0，但输出里没有任何版本号，且尾部 `execvpe: No such file or directory` 说明它把 `--version` 当成了**要启动的目标程序**——因为该文件不存在而报错。`-h` 与裸 `version` 参数的行为相同。

版本号实际在 `--help` 输出里：

```
(Tracer): [INFO ] ***** Version:
(Tracer): [INFO ] *****         3.7.1.5-ef9e10e
```

**结论**：环境探测脚本若用 `--version` 提取 mcTracer 版本，会静默拿到空值。必须改用 `--help` 并从中解析 `Version:` 之后的行。

本仓库已经按此修好：`scripts/capture_environment.py` 对 mcTracer 改用 `--help` 探测，并在产物的每个工具条目里记录实际使用的参数（`version_args` 字段），使「用什么参数拿到这个版本」本身可审计。`benchmarks/results/environment-c500-components.json` 的 mcTracer 条目因此带有 `3.7.1.5-ef9e10e` 与 `version_args: ["--help"]`。

## 版本证据的强度与边界

- 版本字符串 `3.7.1.5-ef9e10e` 的主版本部分与 MXMACA 版本（`3.7.1.5`）一致，后缀 `ef9e10e` 是构建标识。这是单信号，`confidence` 记为 `source-reported`。
- 「版本号与 MXMACA 主版本一致」不等于「mcTracer 与 MXMACA 运行时版本必须匹配」这一结论；后者需官方文档或实测多版本才能主张，本页不主张。

## 使用注意事项

- mcTracer 与 mcProfiler 是**两个不同工具**：mcTracer 偏应用轨迹追踪，mcProfiler 偏硬件性能计数（见 `diagnostics-mcprofiler-basics`）。本页不混淆两者的能力边界。
- 追踪选项与输出格式因 MXMACA 版本而异；上述路径与版本针对 MACA 3.7.1.5，其他版本需重新捕获。
- 本页不含任何追踪结果或性能数据——未实际追踪任何目标程序。

## 复现方式

```bash
/opt/maca/bin/mcTracer --help 2>&1 | grep -A1 "Version:"
# 注意：--version 不报版本，不要用它做版本探测
```
