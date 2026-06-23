# TableClaw 启动指南

从 GitHub 拉取代码后，按以下步骤在本地启动 TableClaw。

## 前置要求

- Python 3.11+
- Git
- 有效的 DashScope API Key（[百炼控制台](https://bailian.console.aliyun.com/) 获取）

## 1. 克隆代码

```bash
git clone <repo-url>
cd TableClaw
```

## 2. 创建虚拟环境并安装依赖

打开终端，在项目根目录下执行：

```bash
cd nanobot
python3 -m venv .venv
.venv/bin/python -m pip install -e .
```

## 3. 设置 API Key

### macOS / Linux

```bash
export DASHSCOPE_API_KEY='你的DeepSeek-V4-Key'
```

也可以写入 `~/.zshrc` 或 `~/.bashrc` 持久化：

```bash
echo 'export DASHSCOPE_API_KEY="你的Key"' >> ~/.zshrc
source ~/.zshrc
```

### Windows (PowerShell)

```powershell
$env:DASHSCOPE_API_KEY = "你的DeepSeek-V4-Key"
```

持久化（PowerShell 管理员模式）：

```powershell
[System.Environment]::SetEnvironmentVariable('DASHSCOPE_API_KEY', '你的Key', 'User')
```

### Windows (CMD)

```cmd
set DASHSCOPE_API_KEY=你的DeepSeek-V4-Key
```

持久化：

```cmd
setx DASHSCOPE_API_KEY "你的Key"
```

## 4. 导入业务表格（可选）

如果需要进行四川财资业务表格问答，将业务测试包中的表格放入 `workspace/uploads/`：

```bash
# macOS / Linux / Git Bash
mkdir -p workspace/uploads
cp 业务测试包/tables/*.xlsx workspace/uploads/
```

```powershell
# Windows PowerShell
New-Item -ItemType Directory -Force -Path workspace\uploads
Copy-Item 业务测试包\tables\*.xlsx workspace\uploads\
```

> 注意：`业务测试包/` 目录需单独获取（不在 GitHub 仓库中）。
> 仅做通用表格问答可跳过此步。

## 5. 启动 TableClaw

### macOS / Linux

```bash
# 在项目根目录下
./start.sh
```

### Windows (PowerShell)

```powershell
# 在项目根目录下（TableClaw/）
cd nanobot
.venv\Scripts\python -m nanobot agent --config configs/tableclaw-bailian-dashscope.json
```

### Windows (CMD)

```cmd
cd nanobot
.venv\Scripts\python -m nanobot agent --config configs/tableclaw-bailian-dashscope.json
```

### Windows (Git Bash)

```bash
# 在项目根目录下（TableClaw/）
cd nanobot
.venv/Scripts/python -m nanobot agent --config configs/tableclaw-bailian-dashscope.json
```

## 6. 验证启动成功

启动后看到交互界面，输入一个问题测试：

```
你好，请介绍一下你能做什么
```

如果能正常回复，说明启动成功。输入 `exit` 或 `quit` 退出。

## 目录结构说明

```
TableClaw/
├── start.sh              # macOS/Linux 一键启动脚本
├── nanobot/               # Agent 框架源码
│   ├── configs/           # 配置文件
│   │   └── tableclaw-bailian-dashscope.json  # 默认交互配置
│   └── .venv/             # 虚拟环境（需自行创建，不进 git）
├── workspace/             # 运行时工作区（上传表、会话、记忆等）
├── domain_packs/          # 领域知识包
├── eval_test/             # 评测数据集
│   └── test_dataset/
│       ├── gold_cases.jsonl       # 40 条 gold cases
│       ├── bad_cases.jsonl        # 122 条 badcase
│       └── query_variants_100*.jsonl  # 500 条 query rewrite
└── docs/                  # 项目文档
```

## 配置文件说明

| 配置文件 | 用途 |
| --- | --- |
| `tableclaw-bailian-dashscope.json` | 默认交互配置（temperature=1.0） |
| `tableclaw-bailian-dashscope-eval.json` | 低温评测配置（temperature=0.2） |
| `tableclaw-bailian-dashscope-no-xlsx-skill.json` | 禁用 spreadsheet skill 对照 |
| `tableclaw-bailian-dashscope-anthropic-xlsx-only.json` | 仅保留 spreadsheet skill |
| `tableclaw-uniapi-gpt55.json` | GPT-5.5 对照配置 |
| `tableclaw-xfyun-qwen36.json` | 讯飞 Qwen 备用配置 |

所有配置的 API Key 均通过环境变量注入，不在文件中保存明文。

## 常见问题

### Q: 启动报 "DASHSCOPE_API_KEY is required"

确认已执行第 3 步设置环境变量。如果已设置，检查是否在当前终端窗口生效：

```bash
echo $DASHSCOPE_API_KEY          # macOS/Linux
echo $env:DASHSCOPE_API_KEY      # Windows PowerShell
```

### Q: 启动报 "Missing nanobot virtual environment"

确认已执行第 2 步创建虚拟环境并安装依赖。

### Q: Windows 上报 "python 不是内部或外部命令"

确保 Python 已安装并添加到系统 PATH。在 PowerShell 中尝试用 `python3` 或 `py` 替代 `python`。

### Q: 如何切换配置

```bash
# macOS/Linux
TABLECLAW_CONFIG=nanobot/configs/tableclaw-bailian-dashscope-eval.json ./start.sh

# Windows
.venv\Scripts\python -m nanobot agent --config configs/tableclaw-bailian-dashscope-eval.json
```

### Q: 如何指定 workspace 目录

```bash
python -m nanobot agent --config configs/tableclaw-bailian-dashscope.json --workspace /path/to/workspace
```