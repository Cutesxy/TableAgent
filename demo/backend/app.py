from __future__ import annotations

import asyncio
import json
import os
import shutil
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parents[2]
NANOBOT_SRC = ROOT / "nanobot"
if str(NANOBOT_SRC) not in sys.path:
    sys.path.insert(0, str(NANOBOT_SRC))

from nanobot.agent.hook import AgentHook, AgentHookContext  # noqa: E402
from nanobot.nanobot import Nanobot  # noqa: E402

ALLOWED_EXTENSIONS = {".xlsx", ".xls", ".csv", ".tsv"}
DEFAULT_CONFIG = ROOT / "nanobot/configs/tableclaw-bailian-dashscope.json"
RUNS_DIR = ROOT / "demo/runs"
STATIC_DIR = ROOT / "demo/frontend/dist"
WORKSPACE_BASE = ROOT / "workspace/demo"


def now_ms() -> int:
    return int(time.time() * 1000)


def event_payload(kind: str, **payload: Any) -> dict[str, Any]:
    return {"kind": kind, "ts": now_ms(), **payload}


def sse(event: dict[str, Any]) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


def compact(value: Any, max_len: int = 900) -> str:
    if value is None:
        return ""
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    text = " ".join(text.split())
    return text if len(text) <= max_len else text[: max_len - 1] + "..."


def compact_path(path: str | Path) -> str:
    p = Path(str(path))
    try:
        if p.is_absolute():
            return str(p.relative_to(ROOT))
    except ValueError:
        pass
    return str(p)


def tool_call_name(tool_call: Any) -> str:
    if hasattr(tool_call, "name"):
        return str(tool_call.name)
    if isinstance(tool_call, dict):
        fn = tool_call.get("function") or {}
        return str(fn.get("name") or tool_call.get("name") or "unknown")
    return "unknown"


def tool_call_id(tool_call: Any) -> str:
    if hasattr(tool_call, "id"):
        return str(tool_call.id)
    if isinstance(tool_call, dict):
        return str(tool_call.get("id") or uuid.uuid4().hex[:10])
    return uuid.uuid4().hex[:10]


def tool_call_args(tool_call: Any) -> Any:
    raw: Any = None
    if hasattr(tool_call, "arguments"):
        raw = tool_call.arguments
    elif isinstance(tool_call, dict):
        fn = tool_call.get("function") or {}
        raw = fn.get("arguments") or tool_call.get("arguments")
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw
    return raw or {}


def classify_tool(name: str) -> tuple[str, str]:
    if name == "tableclaw_retrieve_tables":
        return "retrieve", "召回候选表"
    if name == "tableclaw_domain_knowledge":
        return "knowledge", "读取领域知识"
    if name in {"tableclaw_inspect", "tableclaw_catalog_tables", "tableclaw_locate_column"}:
        return "inspect", "理解表格结构"
    if name.startswith("tableclaw_"):
        return "tool", "执行表格工具"
    if name in {"read_file", "list_directory", "glob", "grep"}:
        return "read", "读取工作区"
    if name in {"run_command", "exec"}:
        return "execute", "执行分析代码"
    return "tool", "调用工具"


def tool_reason(name: str, args: Any) -> str:
    data = args if isinstance(args, dict) else {}
    path = data.get("path") or data.get("file") or data.get("file_path")
    query = data.get("query") or data.get("question")
    if name == "tableclaw_inspect" and path:
        return f"检查表格结构：{Path(str(path)).name}"
    if name == "tableclaw_retrieve_tables":
        return f"根据问题召回候选表：{compact(query or data, 180)}"
    if name == "tableclaw_domain_knowledge":
        return f"读取领域口径、指标别名和推荐计划：{compact(query or data, 180)}"
    if name.startswith("tableclaw_"):
        return f"用结构化表格工具执行分析：{compact(data, 220)}"
    if name == "read_file" and path:
        return f"读取工作区文件：{Path(str(path)).name}"
    if name in {"exec", "run_command"}:
        return f"执行辅助分析：{compact(data, 220)}"
    return compact(data, 240) or name


def tool_detail(name: str, args: Any) -> str:
    data = args if isinstance(args, dict) else args
    if isinstance(data, dict):
        shown = dict(data)
        for key in ("path", "file", "file_path"):
            if key in shown:
                shown[key] = compact_path(shown[key])
        return compact(shown, 1400)
    return compact(data, 1400)


def build_prompt(question: str, uploaded_files: list[Path]) -> str:
    file_lines = "\n".join(f"- {path.name}: {path}" for path in uploaded_files)
    return f"""用户上传了以下表格文件，已保存到当前 workspace/uploads：
{file_lines}

用户任务：
{question}

请作为 TableAgent 完成这个表格任务。要求：
1. 优先使用 TableClaw / TableAgent 的表格工具、skill 和必要的简短代码完成分析。
2. 用简洁可读的方式说明你读取了哪些表、如何理解字段、如何规划步骤、调用了哪些 tool/skill。
3. 如需输出表格结果，请用 Markdown 表格；如生成文件，请说明文件路径。
4. 如果数据不足、字段缺失或执行异常，请明确列出异常项和 best-effort 结论。
5. 最后给出直接答案，并列出使用的上传文件名。"""


def safe_filename(name: str) -> str:
    stem = Path(name).name.strip().replace("\\", "_").replace("/", "_")
    return stem or f"upload-{uuid.uuid4().hex[:8]}"


def copy_domain_context(workspace: Path) -> None:
    repo_skills = ROOT / "skills"
    workspace_skills = workspace / "skills"
    if repo_skills.exists():
        workspace_skills.mkdir(parents=True, exist_ok=True)
        for source_skill in repo_skills.iterdir():
            target_skill = workspace_skills / source_skill.name
            if source_skill.is_dir() and not target_skill.exists():
                shutil.copytree(source_skill, target_skill)
            elif source_skill.is_file() and not target_skill.exists():
                shutil.copy2(source_skill, target_skill)

    for folder in ("skills", "domain_knowledge"):
        src = ROOT / "workspace" / folder
        dst = workspace / folder
        if src.exists() and not dst.exists():
            shutil.copytree(src, dst)
    builtin_skill = ROOT / "domain_packs/sichuan-finance/skills/sichuan-finance"
    skill_dst = workspace / "skills/sichuan-finance"
    if builtin_skill.exists() and not skill_dst.exists():
        skill_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(builtin_skill, skill_dst)
    builtin_knowledge = ROOT / "domain_packs/sichuan-finance/knowledge/tableclaw_industrial_finance.json"
    knowledge_dst = workspace / "domain_knowledge/tableclaw_industrial_finance.json"
    if builtin_knowledge.exists() and not knowledge_dst.exists():
        knowledge_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(builtin_knowledge, knowledge_dst)


def discover_artifacts(workspace: Path, started_at: float) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    excluded_parts = {"uploads", "skills", "domain_knowledge", "sessions", "memory", "table_cache"}
    preview_exts = {".csv", ".tsv", ".txt", ".md", ".json"}
    for path in sorted(workspace.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(workspace)
        if rel.parts and rel.parts[0] in excluded_parts:
            continue
        try:
            stat = path.stat()
        except OSError:
            continue
        if stat.st_mtime < started_at - 1:
            continue
        item: dict[str, Any] = {
            "name": path.name,
            "path": str(path),
            "relative_path": str(rel),
            "size_bytes": stat.st_size,
            "previewable": path.suffix.lower() in preview_exts,
        }
        if item["previewable"]:
            try:
                item["preview"] = path.read_text(encoding="utf-8", errors="replace")[:2000]
            except OSError:
                item["preview"] = ""
        artifacts.append(item)
    return artifacts[:20]


class DemoStreamHook(AgentHook):
    def __init__(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        super().__init__()
        self.queue = queue
        self._answer_parts: list[str] = []
        self._seq = 0
        self._reasoning_started_at: int | None = None
        self._reasoning_buffer: list[str] = []
        self._tool_phases: dict[str, dict[str, Any]] = {}

    def wants_streaming(self) -> bool:
        return True

    def _phase_id(self, prefix: str) -> str:
        self._seq += 1
        return f"{prefix}-{self._seq}"

    async def _flush_reasoning(self) -> None:
        text = "".join(self._reasoning_buffer).strip()
        if not text:
            self._reasoning_buffer = []
            self._reasoning_started_at = None
            return
        started = self._reasoning_started_at or now_ms()
        ended = now_ms()
        phase_id = self._phase_id("reason")
        await self.queue.put(
            event_payload(
                "phase_end",
                phase_id=phase_id,
                status="done",
                stage="plan",
                title="深度思考归纳",
                summary="模型在读取上下文后形成下一步计划。",
                detail=compact(text, 2600),
                started_at=started,
                ended_at=ended,
                duration_ms=max(0, ended - started),
            )
        )
        self._reasoning_buffer = []
        self._reasoning_started_at = None

    async def before_iteration(self, context: AgentHookContext) -> None:
        return None

    async def emit_reasoning(self, reasoning_content: str | None) -> None:
        if reasoning_content:
            if self._reasoning_started_at is None:
                self._reasoning_started_at = now_ms()
            self._reasoning_buffer.append(reasoning_content)

    async def emit_reasoning_end(self) -> None:
        await self._flush_reasoning()

    async def on_stream(self, context: AgentHookContext, delta: str) -> None:
        if not delta:
            return
        self._answer_parts.append(delta)
        await self.queue.put(event_payload("answer_delta", delta=delta))

    async def before_execute_tools(self, context: AgentHookContext) -> None:
        await self._flush_reasoning()
        for tool_call in context.tool_calls:
            name = tool_call_name(tool_call)
            call_id = tool_call_id(tool_call)
            args = tool_call_args(tool_call)
            stage, title = classify_tool(name)
            phase_id = self._phase_id("tool")
            started = now_ms()
            self._tool_phases[call_id] = {
                "phase_id": phase_id,
                "started_at": started,
                "tool": name,
                "stage": stage,
                "title": title,
            }
            await self.queue.put(
                event_payload(
                    "phase_start",
                    phase_id=phase_id,
                    tool_call_id=call_id,
                    status="running",
                    stage=stage,
                    title=title,
                    tool=name,
                    summary=tool_reason(name, args),
                    detail=tool_detail(name, args),
                    started_at=started,
                )
            )

    async def after_iteration(self, context: AgentHookContext) -> None:
        await self._flush_reasoning()
        for index, result in enumerate(context.tool_results):
            tool_call = context.tool_calls[index] if index < len(context.tool_calls) else None
            tool_name = tool_call_name(tool_call) if tool_call is not None else "tool"
            call_id = tool_call_id(tool_call) if tool_call is not None else f"unknown-{index}"
            phase = self._tool_phases.pop(call_id, None)
            stage, title = classify_tool(tool_name)
            started = int((phase or {}).get("started_at") or now_ms())
            ended = now_ms()
            await self.queue.put(
                event_payload(
                    "phase_end",
                    phase_id=(phase or {}).get("phase_id") or self._phase_id("tool"),
                    tool_call_id=call_id,
                    status="done",
                    stage=stage,
                    title=title,
                    tool=tool_name,
                    summary=f"{title}完成",
                    detail=compact(result, 2400),
                    started_at=started,
                    ended_at=ended,
                    duration_ms=max(0, ended - started),
                )
            )
        if context.final_content:
            await self.queue.put(event_payload("answer", answer=context.final_content))


@dataclass
class DemoRun:
    run_id: str
    session_id: str
    workspace: Path
    queue: asyncio.Queue[dict[str, Any]]
    created_at: float = field(default_factory=time.time)
    task: asyncio.Task[None] | None = None


runs: dict[str, DemoRun] = {}
app = FastAPI(title="TableAgent Demo", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def mock_run(queue: asyncio.Queue[dict[str, Any]], question: str, files: list[Path], workspace: Path) -> None:
    steps = [
        ("read", "读取上传表格", f"已接收 {len(files)} 个文件：" + "、".join(path.name for path in files)),
        ("plan", "深度思考归纳", "归纳用户任务、上传表格与可用 skill，形成 inspect -> extract/rank -> 校验 -> 回复的执行路线。"),
        ("inspect", "理解表格结构", "tableclaw_inspect", "检查 workbook/sheet、表头候选、样例行和数值列类型。"),
        ("tool", "执行表格工具", "tableclaw_rank", "按问题指标抽取候选列、排序并校验异常项。"),
    ]
    for item in steps:
        stage = item[0]
        title = item[1]
        summary = item[2]
        detail = item[3] if len(item) > 3 else item[2]
        phase_id = f"mock-{uuid.uuid4().hex[:8]}"
        started = now_ms()
        await queue.put(
            event_payload(
                "phase_start",
                phase_id=phase_id,
                status="running",
                stage=stage,
                title=title,
                tool=summary if summary.startswith("tableclaw_") else None,
                summary=summary,
                detail=detail,
                started_at=started,
            )
        )
        await asyncio.sleep(0.35)
        ended = now_ms()
        await queue.put(
            event_payload(
                "phase_end",
                phase_id=phase_id,
                status="done",
                stage=stage,
                title=title,
                tool=summary if summary.startswith("tableclaw_") else None,
                summary=summary,
                detail=detail,
                started_at=started,
                ended_at=ended,
                duration_ms=ended - started,
            )
        )
    answer = (
        "这是 mock 演示结果。真实模式会调用 TableAgent/Nanobot SDK。\n\n"
        "| 项目 | 结果 |\n| --- | --- |\n"
        f"| 上传文件 | {', '.join(path.name for path in files) or '无'} |\n"
        f"| 用户任务 | {question} |\n"
        "| 工作流 | 读取表格 -> 理解任务 -> 规划步骤 -> 调用工具 -> 生成结果 |\n\n"
        "异常项：无。"
    )
    artifacts = discover_artifacts(workspace, time.time() - 3600)
    if artifacts:
        await queue.put(event_payload("artifacts", artifacts=artifacts))
    await queue.put(event_payload("answer", answer=answer))
    await queue.put(event_payload("done", status="done"))


async def real_run(queue: asyncio.Queue[dict[str, Any]], question: str, files: list[Path], workspace: Path, session_id: str) -> None:
    config = Path(os.environ.get("TABLEAGENT_DEMO_CONFIG", DEFAULT_CONFIG)).expanduser()
    session_key = f"demo:{session_id}"
    started_at = time.time()
    started_ms = now_ms()
    ended_ms = started_ms
    await queue.put(
        event_payload(
            "phase_end",
            phase_id=f"upload-{uuid.uuid4().hex[:8]}",
            status="done",
            stage="read",
            title="接收上传表格",
            summary=", ".join(path.name for path in files) or "本轮未上传新文件",
            detail="\n".join(compact_path(path) for path in files) or "沿用当前会话 workspace。",
            started_at=started_ms,
            ended_at=ended_ms,
            duration_ms=0,
        )
    )
    init_started = now_ms()
    bot = Nanobot.from_config(config, workspace=workspace)
    init_ended = now_ms()
    await queue.put(
        event_payload(
            "phase_end",
            phase_id=f"init-{uuid.uuid4().hex[:8]}",
            status="done",
            stage="plan",
            title="初始化 TableAgent",
            summary="加载配置、workspace、skills 与工具注册表。",
            detail=f"config={compact_path(config)}\nworkspace={compact_path(workspace)}\nsession={session_key}",
            started_at=init_started,
            ended_at=init_ended,
            duration_ms=init_ended - init_started,
        )
    )
    hook = DemoStreamHook(queue)
    try:
        result = await bot.run(build_prompt(question, files), session_key=session_key, hooks=[hook])
        usage = dict(getattr(bot._loop, "_last_usage", {}) or {})
        artifacts = discover_artifacts(workspace, started_at)
        if artifacts:
            await queue.put(event_payload("artifacts", artifacts=artifacts))
        await queue.put(
            event_payload(
                "summary",
                status="done",
                tools=result.tools_used,
                usage=usage,
                message_count=len(result.messages),
            )
        )
        await queue.put(event_payload("answer", answer=result.content))
        await queue.put(event_payload("done", status="done"))
    finally:
        await bot._loop.close_mcp()


async def run_wrapper(queue: asyncio.Queue[dict[str, Any]], question: str, files: list[Path], workspace: Path, session_id: str, mock: bool) -> None:
    try:
        if mock:
            await mock_run(queue, question, files, workspace)
        else:
            await real_run(queue, question, files, workspace, session_id)
    except Exception as exc:
        await queue.put(event_payload("error", status="error", title="运行失败", detail=f"{type(exc).__name__}: {exc}"))
    finally:
        await queue.put(event_payload("close"))


@app.get("/api/health")
async def health() -> dict[str, Any]:
    return {
        "ok": True,
        "root": str(ROOT),
        "default_config": str(DEFAULT_CONFIG),
        "mock_default": os.environ.get("TABLEAGENT_DEMO_MOCK", "0") == "1",
    }


@app.post("/api/runs")
async def create_run(
    question: str = Form(...),
    session_id: str | None = Form(None),
    mock: bool = Form(False),
    files: list[UploadFile] = File(default=[]),
) -> dict[str, Any]:
    question = question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="请输入问题或任务。")
    run_id = uuid.uuid4().hex[:12]
    clean_session_id = (session_id or "").strip() or uuid.uuid4().hex[:12]
    clean_session_id = "".join(ch for ch in clean_session_id if ch.isalnum() or ch in ("-", "_"))[:48] or uuid.uuid4().hex[:12]
    workspace = WORKSPACE_BASE / clean_session_id
    upload_dir = workspace / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    copy_domain_context(workspace)

    saved_files: list[Path] = []
    for upload in files:
        filename = safe_filename(upload.filename or "")
        suffix = Path(filename).suffix.lower()
        if suffix not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail=f"不支持的文件类型：{filename}")
        target = upload_dir / filename
        if target.exists():
            target = upload_dir / f"{target.stem}-{uuid.uuid4().hex[:6]}{target.suffix}"
        with target.open("wb") as handle:
            shutil.copyfileobj(upload.file, handle)
        saved_files.append(target)

    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    demo_run = DemoRun(run_id=run_id, session_id=clean_session_id, workspace=workspace, queue=queue)
    run_mock = mock or os.environ.get("TABLEAGENT_DEMO_MOCK", "0") == "1"
    demo_run.task = asyncio.create_task(run_wrapper(queue, question, saved_files, workspace, clean_session_id, run_mock))
    runs[run_id] = demo_run
    return {"run_id": run_id, "session_id": clean_session_id, "mock": run_mock, "files": [path.name for path in saved_files]}


@app.get("/api/runs/{run_id}/events")
async def run_events(run_id: str) -> StreamingResponse:
    demo_run = runs.get(run_id)
    if demo_run is None:
        raise HTTPException(status_code=404, detail="run 不存在或已过期。")

    async def stream() -> Any:
        yield sse(event_payload("hello", run_id=run_id))
        while True:
            event = await demo_run.queue.get()
            if event.get("kind") == "close":
                break
            yield sse(event)

    return StreamingResponse(stream(), media_type="text/event-stream")


if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")


@app.get("/{path:path}")
async def index(path: str = "") -> FileResponse:
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="前端尚未构建，请先运行 npm run build。")
    return FileResponse(index_file)
