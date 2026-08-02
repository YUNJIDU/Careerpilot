import { FormEvent, useEffect, useState } from "react";
import { AgentLimits, AgentRun, api, ApplicationDetail } from "./api";

const DEFAULT_LIMITS: AgentLimits = {
  max_steps: 8,
  max_model_calls: 6,
  max_tool_calls: 8,
  max_write_approvals: 2,
  max_elapsed_seconds: 180,
};

const STATUS_LABELS: Record<string, string> = {
  pending: "等待运行",
  running: "运行中",
  waiting_approval: "等待人工审批",
  succeeded: "已完成",
  failed: "失败",
  cancelled: "已取消",
  budget_exhausted: "预算已用尽",
  timed_out: "已超时",
};

function Notice({ kind = "info", children }: { kind?: "info" | "error" | "success"; children: React.ReactNode }) {
  return <div className={`notice ${kind}`} role={kind === "error" ? "alert" : "status"}>{children}</div>;
}

export default function AgentPage({ id }: { id: string }) {
  const [application, setApplication] = useState<ApplicationDetail | null>(null);
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [selected, setSelected] = useState<AgentRun | null>(null);
  const [requestText, setRequestText] = useState("整理这个岗位已有证据，列出已确认内容和仍需核实的问题。");
  const [confirmed, setConfirmed] = useState(false);
  const [limits, setLimits] = useState(DEFAULT_LIMITS);
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const load = async (preferredRunId?: string) => {
    const [nextApplication, nextRuns] = await Promise.all([api.application(id), api.agentRuns(id)]);
    setApplication(nextApplication); setRuns(nextRuns);
    const next = nextRuns.find((item) => item.run_id === preferredRunId)
      ?? nextRuns.find((item) => item.run_id === selected?.run_id)
      ?? nextRuns[0]
      ?? null;
    setSelected(next);
  };
  useEffect(() => { void load().catch((value) => setError(String(value))); }, [id]);

  const start = async (event: FormEvent) => {
    event.preventDefault(); setBusy("start"); setError(""); setMessage("");
    try {
      const run = await api.createAgentRun(id, requestText.trim(), limits);
      await load(run.run_id); setConfirmed(false);
      setMessage(run.status === "waiting_approval" ? "Agent 已暂停，等待你的审批。" : "Agent Run 已结束并保存审计记录。");
    } catch (value) {
      setError(String(value)); await load().catch(() => undefined);
    } finally { setBusy(""); }
  };

  const decide = async (approvalId: string, decision: "approved" | "rejected") => {
    if (!selected) return;
    setBusy(approvalId); setError(""); setMessage("");
    try {
      const run = await api.decideAgentApproval(selected.run_id, approvalId, decision);
      await load(run.run_id);
      setMessage(decision === "approved" ? "写入已批准并通过业务 Service 执行。" : "写入已拒绝，岗位数据未修改。");
    } catch (value) { setError(String(value)); await load(selected.run_id).catch(() => undefined); }
    finally { setBusy(""); }
  };

  const runAction = async (action: "resume" | "cancel") => {
    if (!selected) return;
    setBusy(action); setError(""); setMessage("");
    try {
      const run = action === "resume"
        ? await api.resumeAgentRun(selected.run_id)
        : await api.cancelAgentRun(selected.run_id);
      await load(run.run_id); setMessage(action === "resume" ? "Run 已从检查点恢复。" : "Run 已取消，待审批写入不会执行。");
    } catch (value) { setError(String(value)); }
    finally { setBusy(""); }
  };

  const numberField = (key: keyof AgentLimits, value: number) => setLimits({ ...limits, [key]: value });
  if (!application) return error ? <Notice kind="error">{error}</Notice> : <p className="empty">正在读取 Agent 工作台…</p>;

  return <>
    <header className="page-header"><div><a className="back" href={`#/applications/${id}`}>← 返回申请详情</a><p className="eyebrow">Stage 6 · Controlled Agent</p><h1>Agent 协助</h1><p>{application.company} / {application.role}；只整理当前岗位，写入必须由你批准。</p></div></header>
    {message && <Notice kind="success">{message}</Notice>}{error && <Notice kind="error">{error}</Notice>}

    <form className="panel agent-start" onSubmit={(event) => void start(event)}>
      <div className="section-title"><div><h2>新建受控 Run</h2><p>Agent 只调用内置白名单工具，不运行代码、Shell、SQL 或任意插件。</p></div><button className="button primary" disabled={!confirmed || !requestText.trim() || Boolean(busy)}>{busy === "start" ? "正在运行…" : "启动 Agent"}</button></div>
      <label>任务<textarea value={requestText} maxLength={4000} onChange={(event) => setRequestText(event.target.value)} /></label>
      <details><summary>预算设置</summary><div className="agent-limit-grid">
        <label>最大步骤<input type="number" min={1} max={12} value={limits.max_steps} onChange={(event) => numberField("max_steps", Number(event.target.value))} /></label>
        <label>模型调用<input type="number" min={1} max={8} value={limits.max_model_calls} onChange={(event) => numberField("max_model_calls", Number(event.target.value))} /></label>
        <label>工具调用<input type="number" min={0} max={12} value={limits.max_tool_calls} onChange={(event) => numberField("max_tool_calls", Number(event.target.value))} /></label>
        <label>写入审批<input type="number" min={0} max={3} value={limits.max_write_approvals} onChange={(event) => numberField("max_write_approvals", Number(event.target.value))} /></label>
        <label>运行秒数<input type="number" min={10} max={300} value={limits.max_elapsed_seconds} onChange={(event) => numberField("max_elapsed_seconds", Number(event.target.value))} /></label>
      </div></details>
      <div className="data-warning"><strong>本次 Run 的数据离开本机确认</strong><p>最小必要的岗位字段和已保存证据会发送给设置中的模型服务；邮箱授权码、模型 Key 和 Tavily Key 不会进入提示词。确认只对本次 Run 有效。</p><label className="checkbox"><input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} />我了解并确认本次 Agent 模型调用</label></div>
    </form>

    <section className="agent-layout">
      <section className="panel agent-history"><h2>历史 Run</h2>{runs.length ? runs.map((run) => <button key={run.run_id} className={selected?.run_id === run.run_id ? "selected" : ""} onClick={() => setSelected(run)}><strong>{STATUS_LABELS[run.status] ?? run.status}</strong><span>{new Date(run.created_at).toLocaleString()}</span><small>{run.request_text}</small></button>) : <p className="empty">还没有 Agent Run。</p>}</section>
      <div>{selected ? <RunView run={selected} busy={busy} onDecide={decide} onAction={runAction} /> : <section className="panel"><p className="empty">启动一个 Run 后在此查看审计结果。</p></section>}</div>
    </section>
  </>;
}

function RunView({ run, busy, onDecide, onAction }: {
  run: AgentRun;
  busy: string;
  onDecide: (approvalId: string, decision: "approved" | "rejected") => Promise<void>;
  onAction: (action: "resume" | "cancel") => Promise<void>;
}) {
  const pending = run.approvals.filter((item) => item.status === "pending");
  const resumable = run.status === "failed" && run.error_code === "job.interrupted";
  return <>
    <section className="panel"><div className="section-title"><div><h2>Run 状态</h2><p>{run.request_text}</p></div><span className={`status ${run.status}`}>{STATUS_LABELS[run.status] ?? run.status}</span></div>
      <div className="agent-budget"><span>步骤 {run.usage.steps}/{run.limits.max_steps}</span><span>模型 {run.usage.model_calls}/{run.limits.max_model_calls}</span><span>工具 {run.usage.tool_calls}/{run.limits.max_tool_calls}</span><span>审批 {run.usage.write_approvals}/{run.limits.max_write_approvals}</span><span>耗时 {(run.usage.elapsed_ms / 1000).toFixed(1)}s/{run.limits.max_elapsed_seconds}s</span></div>
      {run.error_code && <Notice kind="error">{run.error_code}：{run.error_message_safe}</Notice>}
      <div className="actions">{resumable && <button className="button primary" disabled={Boolean(busy)} onClick={() => void onAction("resume")}>从检查点恢复</button>}{["pending", "running", "waiting_approval"].includes(run.status) && <button className="button danger" disabled={Boolean(busy)} onClick={() => void onAction("cancel")}>取消 Run</button>}</div>
    </section>

    {pending.map((approval) => <section className="panel approval-card" key={approval.approval_id}><div className="section-title"><div><h2>等待人工审批</h2><p>批准前不会修改岗位数据；页面刷新不会丢失此审批。</p></div><span className="status partial">待审批</span></div><pre>{approval.request_summary}</pre><div className="actions"><button className="button primary" disabled={Boolean(busy)} onClick={() => void onDecide(approval.approval_id, "approved")}>批准写入</button><button className="button danger" disabled={Boolean(busy)} onClick={() => void onDecide(approval.approval_id, "rejected")}>拒绝</button></div></section>)}

    <section className="panel"><h2>工具时间线</h2>{run.tool_calls.length ? <ol className="agent-tools">{run.tool_calls.map((call) => <li key={call.tool_call_id}><div><b>{call.tool_name}</b><span className={`status ${call.status}`}>{call.status}</span><small>{call.risk_level === "read" ? "只读" : "人工审批写入"}</small></div><p>{call.reason}</p>{call.result_summary_safe && <strong>{call.result_summary_safe}</strong>}{call.result_refs.length > 0 && <code>{call.result_refs.join(" · ")}</code>}</li>)}</ol> : <p className="empty">本 Run 尚未执行工具。</p>}</section>

    {run.final_output && <section className="panel agent-result"><h2>最终结果</h2><p className="summary-overview">{run.final_output.summary}</p><h3>有来源的事实</h3>{run.final_output.facts.length ? run.final_output.facts.map((fact) => <article key={`${fact.source_id}-${fact.statement}`}><p>{fact.statement}</p><code>{fact.source_id}</code><small>{fact.locator}</small></article>) : <p className="empty">没有可引用为事实的内容。</p>}<div className="summary-grid"><section><h3>未知项</h3><ul>{run.final_output.unknowns.map((item) => <li key={item}>{item}</li>)}</ul></section><section><h3>待核实问题</h3><ul>{run.final_output.next_questions.map((item) => <li key={item}>{item}</li>)}</ul></section></div></section>}
  </>;
}
