# PKU Admission Score Workbook Eval

> 日期：2026-06-23
> Run ID：`pku-admission-real-user-20260623-102936`
> Session：`cli:pku-admission-real-user-20260623-102936`
> 模型：`deepseek-v4-pro` via DashScope OpenAI-compatible
> 配置：`nanobot/configs/tableclaw-bailian-dashscope.json`
> 输入：`workspace/uploads/北京大学各省各专业录取情况.xlsx`

## 1. 评测目的

这条 run 用来评估 TableClaw 在“真实用户默认交互配置”下处理教育招生类复杂 workbook artifact 的能力。

和 Hermes run 不同，本次没有使用 `anthropic-xlsx-only` 专用配置，而是按默认交互配置启动，观察模型是否会自己选择合适的 spreadsheet skill 和工具链。为了保持通用任务 workspace 干净，启动时设置了 `TABLECLAW_SYNC_DOMAIN_PACK=0`，不把业务领域包同步进 `workspace/skills/` 和 `workspace/domain_knowledge/`。

核心观察点：

- 模型是否能识别这是复杂 Excel 清洗、公式统计和图表生成任务。
- 模型是否会自主读取通用 spreadsheet skill。
- 是否能识别合并单元格、重复表头、空列、表头污染、多级表头等脏结构。
- 是否能生成新的 workbook，保留原始表并新增清洗、统计和图表 sheet。
- 是否能在 workbook 中写入 Excel 动态公式和原生图表对象。
- 是否能记录 tool trace、token、耗时、产物和最终回复。

本次评测是 artifact smoke / workflow trace，不是自动打分 benchmark。

## 2. 用户任务

用户要求处理投档分数线 Excel：

1. 解读文件里分批次、分文理科、艺术类的原始投档数据结构。
2. 识别合并单元格、拆分乱行、空行、错位表头等脏数据。
3. 新建工作表清洗规整全量数据，保留原始数据，不覆盖源表。
4. 运用 `VLOOKUP`、`COUNTIFS`、`IF` 等 Excel 动态函数统计各批次文理分数线极值、均分、分段院校数。
5. 生成柱状图、饼图等 Excel 原生可视化图表，对比文理科与各批次分数差异。

完整 prompt：

- [prompt.txt](artifacts/pku-admission-real-user-20260623/logs/prompt.txt)

## 3. Skill / Tool 可见性设计

本次是默认真实用户配置：

```text
nanobot/configs/tableclaw-bailian-dashscope.json
```

启动命令中设置：

```text
TABLECLAW_SYNC_DOMAIN_PACK=0
```

含义：

- 默认 builtin skills 可见。
- workspace domain skill / domain knowledge 不重新同步。
- 模型根据任务自行选择 skill。

实际 trace 显示，模型第一步自主读取了 `anthropic-xlsx`：

```text
read …/skills/anthropic-xlsx/SKILL.md
tableclaw_inspect("…/workspace/uploads/北京大学各省各专业录取情况.xlsx")
```

## 4. 运行统计

Usage 记录：

```json
{
  "latency_ms": 530144,
  "model": "deepseek-v4-pro",
  "provider": "OpenAICompatProvider",
  "session_key": "cli:pku-admission-real-user-20260623-102936",
  "stop_reason": "completed",
  "tools_used": [
    "read_file",
    "tableclaw_inspect",
    "read_file",
    "read_file",
    "read_file",
    "exec",
    "exec",
    "exec",
    "exec",
    "write_file",
    "exec",
    "edit_file",
    "exec",
    "exec",
    "exec",
    "exec",
    "exec",
    "exec",
    "exec",
    "exec"
  ],
  "usage": {
    "cached_tokens": 476672,
    "completion_tokens": 29385,
    "prompt_tokens": 730040,
    "total_tokens": 759425
  }
}
```

汇总：

| 指标 | 值 |
| --- | ---: |
| 总耗时 | 530.1 秒 |
| 总 token | 759,425 |
| prompt tokens | 730,040 |
| completion tokens | 29,385 |
| cached tokens | 476,672 |
| 工具调用数 | 20 |
| 结束状态 | completed |

## 5. DeepSeek-V4-Pro 最终回复

最终面向用户的回复已从 session `cli:pku-admission-real-user-20260623-102936` 抽取并归档：

- [final_assistant_response.md](artifacts/pku-admission-real-user-20260623/logs/final_assistant_response.md)

最终回复核心结论：

- 使用 `anthropic-xlsx`。
- 调用 `tableclaw_inspect` 和多轮 `exec (python3 + openpyxl)`。
- 识别 7 类原始结构问题。
- 生成 5 个 sheet。
- 在 `统计分析` sheet 写入 `COUNTIFS`、`MINIFS`、`MAXIFS`、`AVERAGEIFS`、`IFERROR`、`VLOOKUP` 等公式。
- 在 `可视化图表` sheet 生成 4 张 Excel 原生图表。
- 输出文件保存到 `workspace/北京大学各省各专业录取情况_评测结果.xlsx`。

## 6. 工具轨迹

| 阶段 | 工具 / 动作 | 作用 |
| --- | --- | --- |
| 1 | `read_file` | 读取 `anthropic-xlsx/SKILL.md`，建立 Excel artifact 任务策略。 |
| 2 | `tableclaw_inspect` | 快速扫描原始 workbook：sheet、行列、合并单元格、预览文本。 |
| 3 | `read_file` | 读取 inspect 结果和 tool result。 |
| 4 | `exec (python/openpyxl)` | 深入分析 `Sheet1` 和 `Sheet2` 的表头、合并单元格、重复表头、特殊值。 |
| 5 | `write_file` | 写入处理脚本，避免长命令 heredoc 不稳定。 |
| 6 | `exec (python/openpyxl)` | 生成输出 workbook：原始数据、清洗数据、统计分析、可视化图表。 |
| 7 | `edit_file` + `exec` | 修正脚本，保留 Excel 公式而不是把公式覆盖成静态值。 |
| 8 | `exec (python/openpyxl)` | 验证 sheet、公式、图表对象和输出文件大小。 |
| 9 | `exec rm` | 删除临时脚本。 |

完整日志：

- [run_cli_output.txt](artifacts/pku-admission-real-user-20260623/logs/run_cli_output.txt)
- [session.jsonl](artifacts/pku-admission-real-user-20260623/logs/session.jsonl)
- [usage.jsonl](artifacts/pku-admission-real-user-20260623/logs/usage.jsonl)
- [workbook_summary.json](artifacts/pku-admission-real-user-20260623/logs/workbook_summary.json)
- [tool result 1](artifacts/pku-admission-real-user-20260623/tool-results/call_20b4e2a06b4440ff9fb7c8d4.txt)
- [tool result 2](artifacts/pku-admission-real-user-20260623/tool-results/call_9a426c33198b463b83612484.txt)
- [tool result 3](artifacts/pku-admission-real-user-20260623/tool-results/call_faf3e92d7f5b457d83b29e74.txt)

## 7. 关键中间判断

模型识别到的原始结构问题：

1. 数据从 B 列开始，A 列为空。
2. B 列存在多个 merged ranges，省份名只在分组首行出现。
3. 第 1 行为空白行，表头在第 2 行。
4. 第 170-171 行、第 346-347 行出现重复空行和重复表头。
5. 合并范围中出现“生源地”等表头文本污染数据。
6. G 列控线存在 `——` 特殊值，H 列录取线差对应为空。
7. `Sheet2` 是完全不同结构：第 1 行标题、第 2 行专业名、第 3 行最高分/最低分/平均分子列。

重要恢复点：

- 第一次输出后，模型意识到重算/覆盖逻辑会把公式变成静态值，于是重新生成 workbook，保留 Excel 公式。
- 用户要求 `VLOOKUP`，模型额外补充了 VLOOKUP 查询示例区域。
- 输出 workbook 保留了原始 sheet 复制件，没有覆盖源表。

## 8. 输出产物

### 8.1 输出 Workbook

文件：

- [北京大学各省各专业录取情况_评测结果.xlsx](artifacts/pku-admission-real-user-20260623/outputs/北京大学各省各专业录取情况_评测结果.xlsx)

输入源文件归档：

- [北京大学各省各专业录取情况.xlsx](artifacts/pku-admission-real-user-20260623/inputs/北京大学各省各专业录取情况.xlsx)

### 8.2 Workbook 结构

| Sheet | 行数 | 列数 | 非空单元格 | 公式数 | 图表数 | 合并单元格数 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 原始数据 | 509 | 8 | 3,057 | 0 | 0 | 26 |
| 原始数据_理科专业 | 37 | 75 | 1,175 | 0 | 0 | 47 |
| 清洗数据 | 504 | 8 | 4,016 | 0 | 0 | 0 |
| 统计分析 | 111 | 8 | 438 | 308 | 0 | 5 |
| 可视化图表 | 1 | 1 | 0 | 0 | 4 | 0 |

### 8.3 预览图

清洗数据：

![PKU cleaned data preview](artifacts/pku-admission-real-user-20260623/previews/pku_cleaned_data_preview.jpg)

统计分析公式区：

![PKU statistics preview](artifacts/pku-admission-real-user-20260623/previews/pku_statistics_preview.jpg)

Excel 图表对象：

![PKU chart objects preview](artifacts/pku-admission-real-user-20260623/previews/pku_chart_objects_preview.jpg)

## 9. 公式与图表核验

`统计分析` sheet 保留了 Excel 公式，而不是静态值。公式样例：

| Cell | Formula |
| --- | --- |
| `C3` | `=COUNTIFS(清洗数据!B2:B504,"文",清洗数据!C2:C504,1)` |
| `D3` | `=MINIFS(清洗数据!E2:E504,清洗数据!B2:B504,"文",清洗数据!C2:C504,1)` |
| `E3` | `=MAXIFS(清洗数据!E2:E504,清洗数据!B2:B504,"文",清洗数据!C2:C504,1)` |
| `F3` | `=AVERAGEIFS(清洗数据!E2:E504,清洗数据!B2:B504,"文",清洗数据!C2:C504,1)` |
| `H3` | `=IFERROR(AVERAGEIFS(清洗数据!H2:H504,清洗数据!B2:B504,"文",清洗数据!C2:C504,1),"无控线")` |

图表对象：

- `可视化图表` sheet 中有 4 个 openpyxl chart objects。
- 包含柱状图、饼图和横向柱状图。

限制：

- 当前本地未发现 LibreOffice / soffice，因此没有做 LibreOffice 公式重算和真实 Excel 渲染截图。
- openpyxl 能验证公式字符串、sheet 结构和 chart object 是否存在，但不能替代 Excel/WPS 打开后的视觉 QA。

## 10. 结果判断

本次 run 判定为：**通过通用 workbook artifact smoke v0**。

通过点：

- 默认真实用户配置下，模型自主读取 `anthropic-xlsx`。
- 成功识别复杂招生表结构和典型脏数据。
- 输出了新的 `.xlsx` workbook，保留原始数据并新增清洗、统计和图表 sheet。
- `统计分析` sheet 保留 308 个 Excel 公式，覆盖 `COUNTIFS`、`MINIFS`、`MAXIFS`、`AVERAGEIFS`、`IFERROR`、`VLOOKUP`。
- `可视化图表` sheet 包含 4 个 Excel 原生 chart object。
- 日志、session、usage、tool-results、最终回复和产物已归档。

边界：

- token 和耗时仍然较高：约 530 秒、759,425 tokens。
- 模型最终回复中提到“艺术类”，但输出 workbook 的核心统计仍主要围绕文/理和批次；艺术类是否被充分单独统计，需要后续人工打开源表进一步核验。
- 本地没有 LibreOffice，未执行公式重算、公式错误扫描和全 workbook render 检查。
- 当前只是单任务 artifact smoke，不代表通用教育招生类任务集的稳定准确率。

## 11. 后续改进

下一轮通用 workbook artifact eval 建议补：

- 自动 artifact checker：验证 sheet/header/formula/chart object 是否满足任务约束。
- LibreOffice/WPS/Excel 打开性检查：确认公式能重算，图表可见且不空白。
- 对教育招生类表格补一个小型任务集，覆盖投档线、专业分数线、一分一段、艺术/体育类等结构。
- 低 token 路径：对这类 workbook 先做 schema summary，再让模型基于摘要写脚本，减少反复读取 tool result。
- 把“公式保留 vs 静态值覆盖”加入 artifact checker，避免第一次生成时公式被重算脚本覆盖。
