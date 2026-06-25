import React, { useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  AlertCircle,
  Bot,
  Brain,
  Check,
  ChevronDown,
  Clock3,
  Database,
  FileSpreadsheet,
  FolderUp,
  Loader2,
  MessageSquarePlus,
  Paperclip,
  Search,
  Send,
  Settings,
  Sparkles,
  TerminalSquare,
  User,
  Wrench,
} from "lucide-react";
import "./styles.css";

type Stage = "read" | "inspect" | "knowledge" | "retrieve" | "plan" | "tool" | "execute";
type Role = "user" | "assistant";

type Artifact = {
  name: string;
  path: string;
  relative_path: string;
  size_bytes: number;
  previewable: boolean;
  preview?: string;
};

type RunEvent = {
  kind: string;
  ts?: number;
  phase_id?: string;
  status?: "running" | "done" | "error";
  stage?: Stage;
  title?: string;
  summary?: string;
  detail?: string;
  tool?: string;
  answer?: string;
  delta?: string;
  tools?: string[];
  usage?: Record<string, number>;
  started_at?: number;
  ended_at?: number;
  duration_ms?: number;
  artifacts?: Artifact[];
};

type WorkflowPhase = RunEvent & {
  phase_id: string;
  open?: boolean;
};

type ChatMessage = {
  id: string;
  role: Role;
  content: string;
  files?: string[];
  artifacts?: Artifact[];
  error?: string;
  running?: boolean;
};

const stageMeta: Record<Stage, { label: string; icon: React.ElementType; color: string }> = {
  read: { label: "读取文件", icon: FileSpreadsheet, color: "#2563eb" },
  inspect: { label: "理解表格结构", icon: Database, color: "#0891b2" },
  knowledge: { label: "知识/Skill", icon: Sparkles, color: "#7c3aed" },
  retrieve: { label: "表格召回", icon: Search, color: "#0f766e" },
  plan: { label: "深度思考", icon: Brain, color: "#16a34a" },
  tool: { label: "工具调用", icon: Wrench, color: "#f97316" },
  execute: { label: "执行分析", icon: TerminalSquare, color: "#dc2626" },
};

const sampleThreads = ["新建演示任务", "北京大学录取分析", "xlsx 技能功能与逻辑", "四川应收账款排名"];

function cx(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

function uid(prefix = "id"): string {
  return `${prefix}-${Math.random().toString(16).slice(2)}-${Date.now().toString(16)}`;
}

function formatTime(ts?: number): string {
  if (!ts) return "--:--";
  return new Date(ts).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
}

function formatDuration(ms?: number): string {
  if (ms == null) return "";
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(ms < 10_000 ? 1 : 0)}s`;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark">
          <Bot size={25} />
        </div>
        <div>
          <div className="brand-name">TableAgent</div>
          <div className="brand-subtitle">表格智能体 Demo</div>
        </div>
      </div>
      <button className="new-chat">
        <MessageSquarePlus size={18} />
        新建任务
      </button>
      <div className="thread-label">最近会话</div>
      <div className="thread-list">
        {sampleThreads.map((thread, index) => (
          <button key={thread} className={cx("thread-item", index === 0 && "selected")}>
            <span>{thread}</span>
            <em>{index === 0 ? "进行中" : "已完成"}</em>
          </button>
        ))}
      </div>
      <div className="sidebar-footer">
        <div className="avatar">U</div>
        <span>demo-user</span>
        <Settings size={18} />
      </div>
    </aside>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const Icon = message.role === "user" ? User : Bot;
  return (
    <article className={cx("message", message.role)}>
      <div className="message-icon">
        <Icon size={18} />
      </div>
      <div className="message-body">
        {message.files && message.files.length > 0 && (
          <div className="message-files">
            {message.files.map((file) => (
              <span key={file}>
                <FileSpreadsheet size={14} />
                {file}
              </span>
            ))}
          </div>
        )}
        {message.error ? (
          <div className="inline-error">
            <AlertCircle size={17} />
            {message.error}
          </div>
        ) : message.content ? (
          <div className="markdown">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
          </div>
        ) : (
          <div className="typing">
            <Loader2 className="spin" size={18} />
            TableAgent 正在分析
          </div>
        )}
        {message.artifacts && message.artifacts.length > 0 && <Artifacts artifacts={message.artifacts} />}
      </div>
    </article>
  );
}

function Artifacts({ artifacts }: { artifacts: Artifact[] }) {
  return (
    <div className="artifacts">
      <div className="artifacts-title">生成文件</div>
      {artifacts.map((artifact) => (
        <details key={artifact.path} className="artifact-card">
          <summary>
            <span>{artifact.name}</span>
            <em>{formatBytes(artifact.size_bytes)}</em>
          </summary>
          <code>{artifact.path}</code>
          {artifact.previewable && artifact.preview && <pre>{artifact.preview}</pre>}
        </details>
      ))}
    </div>
  );
}

function WorkflowPanel({
  phases,
  running,
  onToggle,
}: {
  phases: WorkflowPhase[];
  running: boolean;
  onToggle: (phaseId: string) => void;
}) {
  const doneCount = phases.filter((phase) => phase.status === "done").length;
  return (
    <aside className="workflow">
      <div className="workflow-head">
        <div>
          <h2>Agent 工作流</h2>
          <p>开发观察面板：阶段、工具、原因、耗时与结果摘要。</p>
        </div>
        {running && <Loader2 className="spin" size={19} />}
      </div>
      <div className="workflow-stats">
        <span>{phases.length} 个阶段</span>
        <span>{doneCount} 已完成</span>
      </div>
      <div className="phase-list">
        {phases.length === 0 ? (
          <div className="empty-workflow">发送消息后显示工作流卡片</div>
        ) : (
          phases.map((phase, index) => <PhaseCard key={phase.phase_id} phase={phase} index={index} onToggle={onToggle} />)
        )}
      </div>
    </aside>
  );
}

function PhaseCard({
  phase,
  index,
  onToggle,
}: {
  phase: WorkflowPhase;
  index: number;
  onToggle: (phaseId: string) => void;
}) {
  const stage = phase.stage || "plan";
  const meta = stageMeta[stage];
  const Icon = meta.icon;
  const done = phase.status === "done";
  return (
    <article className={cx("phase-card", phase.open && "open")}>
      <button className="phase-main" onClick={() => onToggle(phase.phase_id)}>
        <span className="phase-caret">
          <ChevronDown size={16} />
        </span>
        <span className="phase-icon" style={{ color: meta.color, background: `${meta.color}14` }}>
          <Icon size={18} />
        </span>
        <span className="phase-text">
          <strong>{phase.title || meta.label}</strong>
          {phase.tool && <code>{phase.tool}</code>}
          <small>{phase.summary || meta.label}</small>
        </span>
        <span className="phase-side">
          <span>{formatTime(phase.ts || phase.ended_at || phase.started_at)}</span>
          {done ? <Check size={16} /> : <Loader2 className="spin" size={16} />}
          <em>#{index + 1}</em>
        </span>
      </button>
      {phase.open && (
        <div className="phase-detail">
          <div className="phase-meta">
            <span>
              <Clock3 size={14} />
              {formatDuration(phase.duration_ms) || "运行中"}
            </span>
            {phase.started_at && phase.ended_at && (
              <span>
                {formatTime(phase.started_at)} - {formatTime(phase.ended_at)}
              </span>
            )}
          </div>
          {phase.detail && <pre>{phase.detail}</pre>}
        </div>
      )}
    </article>
  );
}

function Composer({
  files,
  value,
  mock,
  running,
  onFiles,
  onValue,
  onMock,
  onSubmit,
}: {
  files: File[];
  value: string;
  mock: boolean;
  running: boolean;
  onFiles: (files: File[]) => void;
  onValue: (value: string) => void;
  onMock: (value: boolean) => void;
  onSubmit: () => void;
}) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  return (
    <section className="composer">
      {files.length > 0 && (
        <div className="file-pills">
          {files.map((file) => (
            <span key={`${file.name}-${file.size}`}>
              <FileSpreadsheet size={14} />
              {file.name}
            </span>
          ))}
        </div>
      )}
      <textarea
        value={value}
        placeholder="输入问题，或上传表格后让 TableAgent 分析..."
        onChange={(event) => onValue(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            onSubmit();
          }
        }}
        disabled={running}
      />
      <div className="composer-bottom">
        <div className="composer-tools">
          <button type="button" className="file-button" onClick={() => inputRef.current?.click()} disabled={running}>
            <FolderUp size={17} />
            上传
          </button>
          <input
            ref={inputRef}
            type="file"
            multiple
            accept=".xlsx,.xls,.csv,.tsv"
            onChange={(event) => onFiles(Array.from(event.target.files || []))}
            hidden
          />
          <Paperclip size={19} />
          <label className="mock-toggle">
            <input type="checkbox" checked={mock} disabled={running} onChange={(event) => onMock(event.target.checked)} />
            mock
          </label>
        </div>
        <button className="send-button" type="button" onClick={onSubmit} disabled={running || (!value.trim() && files.length === 0)}>
          {running ? <Loader2 className="spin" size={20} /> : <Send size={20} />}
        </button>
      </div>
    </section>
  );
}

function App() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [phases, setPhases] = useState<WorkflowPhase[]>([]);
  const [files, setFiles] = useState<File[]>([]);
  const [input, setInput] = useState("");
  const [mock, setMock] = useState(false);
  const [running, setRunning] = useState(false);
  const sessionIdRef = useRef(localStorage.getItem("tableagent-demo-session") || uid("session"));
  const currentAssistantId = useRef<string | null>(null);
  const chatEndRef = useRef<HTMLDivElement | null>(null);

  useMemo(() => {
    localStorage.setItem("tableagent-demo-session", sessionIdRef.current);
  }, []);

  function scrollSoon() {
    window.setTimeout(() => chatEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" }), 30);
  }

  function upsertPhase(event: RunEvent) {
    if (!event.phase_id) return;
    const phaseId = event.phase_id;
    setPhases((current) => {
      const index = current.findIndex((phase) => phase.phase_id === phaseId);
      if (index >= 0) {
        const next = current.slice();
        next[index] = { ...next[index], ...event, open: next[index].open };
        return next;
      }
      return [...current, { ...event, phase_id: phaseId, open: false }];
    });
  }

  function updateAssistant(patch: Partial<ChatMessage> | ((message: ChatMessage) => ChatMessage)) {
    const id = currentAssistantId.current;
    if (!id) return;
    setMessages((current) =>
      current.map((message) => {
        if (message.id !== id) return message;
        return typeof patch === "function" ? patch(message) : { ...message, ...patch };
      }),
    );
    scrollSoon();
  }

  async function submit() {
    if (running || (!input.trim() && files.length === 0)) return;
    const text = input.trim() || "请分析上传表格。";
    const fileNames = files.map((file) => file.name);
    const userMessage: ChatMessage = { id: uid("msg"), role: "user", content: text, files: fileNames };
    const assistantMessage: ChatMessage = { id: uid("msg"), role: "assistant", content: "", running: true };
    currentAssistantId.current = assistantMessage.id;
    setMessages((current) => [...current, userMessage, assistantMessage]);
    setPhases([]);
    setInput("");
    setRunning(true);
    scrollSoon();

    const body = new FormData();
    body.append("question", text);
    body.append("session_id", sessionIdRef.current);
    body.append("mock", String(mock));
    files.forEach((file) => body.append("files", file));
    setFiles([]);

    try {
      const response = await fetch("/api/runs", { method: "POST", body });
      if (!response.ok) throw new Error(await response.text());
      const data = (await response.json()) as { run_id: string; session_id: string };
      sessionIdRef.current = data.session_id;
      localStorage.setItem("tableagent-demo-session", data.session_id);
      const source = new EventSource(`/api/runs/${data.run_id}/events`);
      source.onmessage = (message) => {
        const event = JSON.parse(message.data) as RunEvent;
        if (event.kind === "phase_start" || event.kind === "phase_end") {
          upsertPhase(event);
          return;
        }
        if (event.kind === "answer_delta") {
          updateAssistant((current) => ({ ...current, content: current.content + (event.delta || "") }));
          return;
        }
        if (event.kind === "answer") {
          updateAssistant({ content: event.answer || "", running: false });
          return;
        }
        if (event.kind === "artifacts") {
          updateAssistant({ artifacts: event.artifacts || [] });
          return;
        }
        if (event.kind === "summary") {
          upsertPhase({
            ...event,
            phase_id: `summary-${Date.now()}`,
            stage: "execute",
            title: "运行摘要",
            summary: event.tools?.length ? `工具序列：${event.tools.join(" -> ")}` : "运行完成",
            detail: JSON.stringify({ usage: event.usage, tools: event.tools }, null, 2),
            status: "done",
            duration_ms: undefined,
          });
          return;
        }
        if (event.kind === "error") {
          updateAssistant({ error: event.detail || "运行失败", running: false });
          setRunning(false);
          source.close();
          return;
        }
        if (event.kind === "done") {
          updateAssistant({ running: false });
          setRunning(false);
          source.close();
        }
      };
      source.onerror = () => {
        updateAssistant({ error: "事件流连接中断。", running: false });
        setRunning(false);
        source.close();
      };
    } catch (exc) {
      updateAssistant({ error: exc instanceof Error ? exc.message : String(exc), running: false });
      setRunning(false);
    }
  }

  return (
    <div className="app">
      <Sidebar />
      <main className="chat-shell">
        <header className="topbar">
          <div>
            <h1>TableAgent</h1>
            <p>上传表格，像聊天一样连续分析；右侧保留可观察工作流。</p>
          </div>
          <span className={cx("status-dot", running && "live")} />
        </header>
        <section className="chat-scroll">
          {messages.length === 0 ? (
            <div className="welcome">
              <Bot size={34} />
              <h2>开始一个表格分析任务</h2>
              <p>上传 xlsx/csv，输入问题后，TableAgent 会在对话中回复，右侧展示读取、思考、工具调用和生成文件。</p>
            </div>
          ) : (
            messages.map((message) => <MessageBubble key={message.id} message={message} />)
          )}
          <div ref={chatEndRef} />
        </section>
        <Composer
          files={files}
          value={input}
          mock={mock}
          running={running}
          onFiles={setFiles}
          onValue={setInput}
          onMock={setMock}
          onSubmit={submit}
        />
      </main>
      <WorkflowPanel
        phases={phases}
        running={running}
        onToggle={(phaseId) =>
          setPhases((current) => current.map((phase) => (phase.phase_id === phaseId ? { ...phase, open: !phase.open } : phase)))
        }
      />
    </div>
  );
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
