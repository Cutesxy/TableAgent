# Generic Table Tasks Eval

> 最后更新：2026-06-24

本目录维护 TableClaw 第二阶段的通用表格上下游任务评测。它和四川财资 `gold-cases/` 主线不同：这里不评估某个业务 domain pack 的拟合效果，而是观察 TableClaw 在不依赖业务知识时，能否通过通用 spreadsheet skill、inspect、代码执行和 artifact 验证完成真实复杂表格任务。

## 评测目标

通用 table task 不只看最终自然语言答案，而是看完整工作流：

```text
用户上传/指定真实 workbook
-> 模型识别这是通用表格任务
-> 选择并读取通用 spreadsheet skill
-> inspect workbook 结构
-> 使用 Python/openpyxl/pandas/LibreOffice 或 TableClaw tools 执行
-> 产出 xlsx / 图表 / 报告 / PPT 上游数据等 artifact
-> 记录 skill 选择、tool trace、耗时、token、输出文件和验证结果
```

## Skill 可见性原则

通用评测以当前 nanobot 内置的唯一表格 skill 为主：

- `anthropic-xlsx`

它用于观察一个完整 spreadsheet skill 是否能覆盖复杂 workbook artifact 任务。业务或客户专属知识应通过 domain pack / workspace skill 插拔，不进入通用 workbook skill。

当前运行建议：

```text
nanobot/configs/tableclaw-bailian-dashscope.json
```

通用任务评测建议保持 `anthropic-xlsx` 作为主要 spreadsheet skill；业务或客户专属知识通过 domain pack / workspace skill 插拔，不写入通用 workbook skill。如果需要避免运行时同步业务 domain pack，可以设置 `TABLECLAW_SYNC_DOMAIN_PACK=0`。

## 当前 Runs

| Run | 任务 | 配置 | 结果 |
| --- | --- | --- | --- |
| [Hermes Anthropic XLSX Skill Eval](hermes-anthropic-xlsx-20260622.md) | Hermès 20 年长表清洗、奢侈品同行对标、2026-2030 财务预测模型 | `anthropic-xlsx` | 综合人工评分 **76/100**：结构化清洗和预测 workbook 产物成立；同行经营数据为估算框架，仍需外部数据/RAG 和 artifact checker |
| [PKU Admission Score Workbook Eval](pku-admission-real-user-20260623.md) | 北京大学各省各专业录取情况表清洗、公式统计、图表生成 | 默认真实用户配置 | 综合人工评分 **72/100**：主表 artifact 约 **84/100**；full workbook 覆盖、艺术类解析和公式重算仍需补强 |
| [Jingmen Budget XLS Cleanup Eval](jingmen-budget-xls-20260624.md) | PDF 另存政府决算 `.xls` 左右半表清洗为标准收支明细 | 默认真实用户配置 | 综合人工评分 **88/100**：左右半表和双层表头恢复较好，收入/支出与层级完整；`.xls` inspect、审计追溯字段和重算校验仍需补强 |
| [BOQ Cleanup Lightweight Eval](boq-cleanup-20260624-143239.md) | 工程量清单层级整理为可筛选明细表，并标记金额 Top10 子项 | 默认真实用户配置 | LLM judge **92/100**：一级工程/二级清单/子项关系补齐较好，汇总行与明细行可筛选；重复明细和非叶子节点计入口径仍需人工复核 |

## 当前 Artifact 评测口径

本目录当前是 v0 smoke/eval，先评估以下内容：

- 是否正确识别并读取通用 spreadsheet skill。
- 是否能 inspect 原始 workbook，并恢复真实 sheet/section 结构。
- 是否产出用户要求的文件。
- 输出 workbook 是否包含合理 sheet、关键字段和公式。
- 是否记录工具轨迹、耗时、token、日志和中间判断。

后续需要补充自动化指标：

- 文件可打开性。
- LibreOffice 重算和公式错误扫描。
- 关键单元格/关键公式断言。
- 渲染截图检查：标题、表格、图表是否可读。
- 数据来源校验：外部 peer 数据是否有来源或明确标注为估算。
- 与 no-spreadsheet-skill / 未来 TableClaw native workbook skill / 其他模型的 A/B 对比。

## 维护规则

- 每个通用任务一个独立 run 文档。
- 产物归档到 `artifacts/<run-id>/`，包括 xlsx、日志、usage、tool-results 和预览图。
- 不把 `workspace/` 作为正式归档来源；workspace 只是运行态目录。
- 正式通用评测要写清楚 skill 可见性，避免和四川财资 domain pack 结果混淆。
