# TableClaw Skill 模块设计

> 最后更新：2026-06-23
>
> 用途：记录 nanobot skill 的加载机制，以及 TableClaw 在“通用骨架 + 可插拔领域包 + 通用 workbook skill”路线下的 skill 边界。

## 当前结论

TableClaw 不再在 nanobot 内置层维护多套碎片化 table skills。当前主线是：

```text
nanobot/nanobot/skills/anthropic-xlsx/   # 唯一内置表格/workbook skill
domain_packs/<domain>/skills/            # 领域/客户策略 skill
workspace/skills/                        # 运行时挂载和用户覆盖层
```

设计原则：

- `anthropic-xlsx` 是当前唯一的 builtin spreadsheet skill，负责通用 workbook/artifact 工作流：清洗、重构、公式、格式、图表、预测模型和 `.xlsx` 交付。
- 业务知识不进入 `anthropic-xlsx`，也不写入通用 table tools；它通过 `domain_packs/<domain>/` 挂载。
- nanobot 骨架只保留清晰的大表格 skill，避免 `xlsx`、`table-read`、`table-clean`、`table-chart` 等小 skill 并存造成选择噪声。
- 未来若需要轻量 native skill，应基于稳定评测结果重新设计，例如 `tableclaw-table` 或 `tableclaw-workbook`，而不是恢复旧碎片 skill。

## Skill 来源

nanobot 当前有两个 skill 来源。

### Builtin Skill

路径：

```text
nanobot/nanobot/skills/<skill-name>/SKILL.md
```

适合：

- 产品内置能力。
- 所有用户都应该拥有的通用能力。
- 需要随代码版本发布、测试和回滚的能力。

当前表格相关 builtin skill：

| Skill | 定位 |
| --- | --- |
| `anthropic-xlsx` | 通用 spreadsheet/workbook 大 skill，面向复杂 Excel artifact 任务。 |

其他 builtin skill 仍保留 nanobot 原生能力，例如 `memory`、`summarize`、`github`、`cron`、`tmux`、`skill-creator`、`image-generation` 等。

### Workspace / Domain Skill

路径：

```text
workspace/skills/<skill-name>/SKILL.md
domain_packs/<domain>/skills/<skill-name>/SKILL.md
```

适合：

- 用户自定义流程。
- 客户私有业务规则。
- 项目级临时实验。
- 某个行业/客户的稳定 workflow 经验。

`domain_packs/<domain>/` 是版本化来源；启动或评测前可同步到 `workspace/skills/`。workspace 同名 skill 会覆盖 builtin skill，因此 workspace 是运行时覆盖层。

## 加载优先级

加载逻辑在：

```text
nanobot/nanobot/agent/skills.py
```

核心规则：

1. 先扫描 `workspace/skills/`。
2. 再扫描 `nanobot/nanobot/skills/`。
3. 如果 workspace 和 builtin 有同名 skill，workspace 版本优先，builtin 版本会被跳过。
4. 如果配置里设置了 `disabledSkills`，对应 skill 会从可用列表里移除。
5. 如果 skill frontmatter 声明了依赖，例如二进制命令或环境变量，依赖不满足时会标记为 unavailable。

## Skill 如何进入模型上下文

相关代码：

```text
nanobot/nanobot/agent/context.py
nanobot/nanobot/templates/agent/skills_section.md
```

每轮对话前，`ContextBuilder` 会构建 system prompt。构建流程里会调用 `SkillsLoader`：

1. 读取 always skill。
2. 把 always skill 的完整内容直接放入 `# Active Skills`。
3. 读取普通 skill 的摘要。
4. 把普通 skill 的 name、description、`SKILL.md` 路径放入 `# Skills`。

普通 skill 不会默认把全文塞进 prompt，而是只给模型一个摘要列表。模型需要根据任务判断是否读取完整 skill。

示意流程：

```text
用户问题
  ↓
system prompt 中包含 skills summary
  ↓
模型判断某个 skill 相关
  ↓
模型调用 read_file 读取 SKILL.md
  ↓
模型按照 skill 指令调用工具
  ↓
模型返回答案或产物
```

在终端中，如果看到类似：

```text
read …/nanobot/nanobot/skills/anthropic-xlsx/SKILL.md
```

就说明模型确实选择并读取了该 skill。

## `anthropic-xlsx` 的当前定位

当前内置路径：

```text
nanobot/nanobot/skills/anthropic-xlsx/
├── SKILL.md
├── LICENSE.txt
└── scripts/
    ├── recalc.py
    └── office/
```

适合任务：

- 清洗和重构复杂 workbook。
- 从堆叠表、多级表头、错位表头中整理结构化 sheet。
- 写公式、统一格式、构建财务模型。
- 生成可交付 `.xlsx` artifact。
- 对关键 workbook 进行重算、错误扫描和视觉检查。

不适合任务：

- 高频、低成本、单问单答的表格 QA。
- 只需要从一张表里抽一个数值的简单问题。
- 需要强业务口径的任务；这类任务应通过 domain pack 和 table tools 协同完成。

当前验证：

- Hermes 长表 artifact smoke 已验证它能完成长表清洗、同行对标框架和 2026-2030 预测模型 workbook。
- 归档报告：[Hermes Anthropic XLSX Skill Eval](../实验评测/generic-table-tasks/hermes-anthropic-xlsx-20260622.md)。

## Skill 可见性与评测模式

常用模式：

| 模式 | 配置 | 用途 |
| --- | --- | --- |
| 默认交互 | `nanobot/configs/tableclaw-bailian-dashscope.json` | 默认开发和交互，当前表格 builtin skill 为 `anthropic-xlsx`。 |
| 低温评测 | `nanobot/configs/tableclaw-bailian-dashscope-eval.json` | 主线业务 benchmark，降低路径漂移。 |
| No spreadsheet skill 对照 | `nanobot/configs/tableclaw-bailian-dashscope-no-xlsx-skill.json` | 禁用 `anthropic-xlsx`，用于观察没有内置 spreadsheet skill 时的能力。 |
| 通用 workbook/artifact 测试 | `nanobot/configs/tableclaw-bailian-dashscope-anthropic-xlsx-only.json` | 以 `anthropic-xlsx` 为主要 spreadsheet skill，评估通用 artifact workflow。 |

注意：

- 不建议把大型 spreadsheet skill 设为 `always`，否则每轮都会消耗大量上下文。
- `disabledSkills` 同时作用于 builtin 和 workspace skill。
- 业务 domain pack 的启用/禁用属于评测配置问题，不应写进通用 spreadsheet skill。

## 与 Domain Pack 的边界

TableClaw 的通用层和领域层应该解耦：

```text
通用 builtin skill
  anthropic-xlsx：怎么处理复杂 workbook artifact

通用 tools
  inspect / retrieve / extract / rank / filter / time_series / validate

domain pack
  某个行业/客户的术语、指标别名、cohort、排序口径、表族经验、fallback 规则
```

判断规则：

- 如果是所有表格都可能遇到的结构问题，例如多行表头、合并单元格、空列、错位数据、公式错误，优先沉淀到通用 tools 或 `anthropic-xlsx`。
- 如果是某个领域的业务口径，例如专属指标、固定名单、行业表族、客户报表命名习惯，放进 domain pack。
- 如果是某个用户/会话的临时口径，放进 memory。

## 后续方向

当前清理后的主线更清楚：

```text
Agent Core
  + Generic Table Tools
  + anthropic-xlsx
  + optional Domain Pack
  + Memory / RAG
  + Eval Harness
```

后续可继续探索：

- 从 `anthropic-xlsx` 和真实 badcase 中抽取 TableClaw 自己的 native workbook skill。
- 为通用 artifact 任务补自动 checker：文件可打开性、公式错误、关键 sheet/header、渲染截图和来源 citation。
- 对比 `anthropic-xlsx`、no-skill、未来 native skill 在不同任务类型上的成本、速度和成功率。
- 保持 domain pack 插拔，不把业务知识塞回通用 skill 或通用工具。
