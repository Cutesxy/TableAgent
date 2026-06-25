# TableAgent Demo UI

一个面向演示的 TableAgent 可视化界面：上传 `xlsx/csv`，输入问题，后端调用现有 Nanobot/TableClaw SDK，并把执行过程通过 SSE 推到前端。

## 启动

```bash
cd /home/rick/tableagent
cd nanobot
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -m pip install -r ../demo/requirements.txt

cd ../demo/frontend
npm install
npm run build

cd ../..
./demo/start_demo.sh
```

打开 `http://127.0.0.1:8787`。

如果只是看 UI，不想调用真实模型：

```bash
TABLEAGENT_DEMO_MOCK=1 ./demo/start_demo.sh
```

真实模式默认使用 `nanobot/configs/tableclaw-bailian-dashscope.json`，需要按配置导出对应 API key。可用 `TABLEAGENT_DEMO_CONFIG=/path/to/config.json` 指向其他配置。
