import { FormEvent, useEffect, useMemo, useState } from "react";
import { api, Application, ApplicationDetail, Job, Settings } from "./api";

type Page = "overview" | "applications" | "detail" | "mail" | "excel" | "jobs" | "settings";

const NAV: Array<[Page, string, string]> = [
  ["overview", "总览", "⌂"],
  ["applications", "申请追踪", "▤"],
  ["mail", "邮件同步", "✉"],
  ["excel", "Excel 同步", "↔"],
  ["jobs", "任务", "◷"],
  ["settings", "设置", "⚙"],
];

const EDITABLE_FIELDS = ["公司名称", "岗位", "当前阶段", "投递时间", "截止时间", "JD 链接", "备注"];
const PROCESS_FIELDS = ["简历通过", "测评", "笔试", "一面", "二面", "三面", "HR 面", "终面"];
const TERMINAL_PATTERN = /已结束|已拒绝|已撤回|已归档|未通过|淘汰|流程终止|挂/;

function displayStage(values: Record<string, unknown>) {
  for (const field of [...PROCESS_FIELDS].reverse()) {
    const result = String(values[field] ?? "");
    if (TERMINAL_PATTERN.test(result)) {
      return result.includes("主动") ? "已结束（主动结束）" : `已结束（${field}未通过）`;
    }
  }
  const stage = String(values["当前阶段"] ?? "未设置");
  if (stage === "已拒绝") return "已结束（流程未通过）";
  return stage;
}

function StageBadge({ value }: { value: unknown }) {
  const stage = String(value || "未设置");
  return <span className={`badge ${TERMINAL_PATTERN.test(stage) ? "closed" : ""}`}>{stage}</span>;
}

function route(): { page: Page; id?: string } {
  const value = location.hash.slice(2) || "overview";
  if (value.startsWith("applications/")) return { page: "detail", id: value.split("/")[1] };
  return { page: (NAV.some(([key]) => key === value) ? value : "overview") as Page };
}

function useRoute() {
  const [current, setCurrent] = useState(route);
  useEffect(() => {
    const update = () => setCurrent(route());
    window.addEventListener("hashchange", update);
    return () => window.removeEventListener("hashchange", update);
  }, []);
  return current;
}

function Notice({ kind = "info", children }: { kind?: "info" | "error" | "success"; children: React.ReactNode }) {
  return <div className={`notice ${kind}`} role={kind === "error" ? "alert" : "status"}>{children}</div>;
}

function Overview({ applications, jobs }: { applications: Application[]; jobs: Job[] }) {
  const recent = applications.slice(-5).reverse();
  const active = applications.filter((item) => !TERMINAL_PATTERN.test(displayStage(item.values))).length;
  return <>
    <header className="page-header"><div><p className="eyebrow">本地工作台</p><h1>申请总览</h1><p>集中查看最近变化，并从明确动作开始。</p></div><a className="button primary" href="#/mail">同步邮箱</a></header>
    <section className="stats">
      <article><span>进行中</span><strong>{active}</strong></article>
      <article><span>全部申请</span><strong>{applications.length}</strong></article>
      <article><span>待处理任务</span><strong>{jobs.filter((job) => job.status === "failed").length}</strong></article>
    </section>
    <section className="panel"><div className="section-title"><div><h2>最近申请</h2><p>数据库中的最新申请记录</p></div><a href="#/applications">查看全部</a></div>
      {recent.length ? <div className="table-wrap"><table><thead><tr><th>公司</th><th>职位</th><th>阶段</th><th></th></tr></thead><tbody>
        {recent.map((item) => <tr key={item.application_id}><td>{item.company}</td><td>{item.role}</td><td><StageBadge value={displayStage(item.values)} /></td><td><a href={`#/applications/${item.application_id}`}>详情</a></td></tr>)}
      </tbody></table></div> : <p className="empty">还没有申请记录。先添加一条或同步邮箱。</p>}
    </section>
  </>;
}

function ApplicationsPage({ onChanged }: { onChanged: () => void }) {
  const [items, setItems] = useState<Application[]>([]);
  const [query, setQuery] = useState("");
  const [stage, setStage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(true);
  const load = async () => {
    setBusy(true); setError("");
    try { setItems(await api.applications()); } catch (value) { setError(String(value)); }
    finally { setBusy(false); }
  };
  useEffect(() => { void load(); }, []);
  const filtered = useMemo(() => items.filter((item) => {
    const text = `${item.company} ${item.role}`.toLowerCase();
    return text.includes(query.toLowerCase()) && (!stage || displayStage(item.values) === stage);
  }), [items, query, stage]);
  const stages = [...new Set(items.map((item) => displayStage(item.values)).filter(Boolean))];
  const create = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    try {
      const item = await api.createApplication(String(data.get("company")), String(data.get("role")));
      form.reset(); await load(); onChanged(); location.hash = `/applications/${item.application_id}`;
    } catch (value) { setError(String(value)); }
  };
  return <>
    <header className="page-header"><div><p className="eyebrow">Tracker</p><h1>申请追踪</h1><p>人工填写的非空字段优先于后续导入。</p></div></header>
    {error && <Notice kind="error">{error}</Notice>}
    <section className="panel"><h2>新增申请</h2><form className="inline-form" onSubmit={create}><label>公司<input name="company" required maxLength={200} /></label><label>职位<input name="role" required maxLength={200} /></label><button className="button primary">新增</button></form></section>
    <section className="panel"><div className="filters"><label>搜索<input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="公司或职位" /></label><label>阶段<select value={stage} onChange={(e) => setStage(e.target.value)}><option value="">全部</option>{stages.map((value) => <option key={value}>{value}</option>)}</select></label></div>
      {busy ? <p className="empty">正在读取…</p> : filtered.length ? <div className="table-wrap"><table><thead><tr><th>公司</th><th>职位</th><th>阶段</th><th>投递时间</th><th></th></tr></thead><tbody>
        {filtered.map((item) => <tr key={item.application_id}><td>{item.company}</td><td>{item.role}</td><td><StageBadge value={displayStage(item.values)} /></td><td>{String(item.values["投递时间"] ?? "—")}</td><td><a href={`#/applications/${item.application_id}`}>查看</a></td></tr>)}
      </tbody></table></div> : <p className="empty">没有符合条件的申请。</p>}
    </section>
  </>;
}

function DetailPage({ id, onChanged }: { id: string; onChanged: () => void }) {
  const [detail, setDetail] = useState<ApplicationDetail | null>(null);
  const [values, setValues] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [saved, setSaved] = useState("");
  const [closeStep, setCloseStep] = useState("笔试");
  const [closeReason, setCloseReason] = useState("未通过");
  const load = async () => {
    try {
      const item = await api.application(id); setDetail(item);
      setValues(Object.fromEntries(EDITABLE_FIELDS.map((field) => [field, String(item.values[field] ?? "")])));
    } catch (value) { setError(String(value)); }
  };
  useEffect(() => { void load(); }, [id]);
  const save = async (event: FormEvent) => {
    event.preventDefault(); if (!detail) return; setError(""); setSaved("");
    try {
      const changes = Object.fromEntries(
        Object.entries(values).filter(([field, value]) => value !== String(detail.values[field] ?? "")),
      );
      if (
        changes["当前阶段"]
        && !TERMINAL_PATTERN.test(String(changes["当前阶段"]))
        && TERMINAL_PATTERN.test(String(detail.values["当前阶段"] ?? ""))
      ) {
        for (const field of PROCESS_FIELDS) {
          if (TERMINAL_PATTERN.test(String(detail.values[field] ?? ""))) changes[field] = "";
        }
      }
      if (!Object.keys(changes).length) { setSaved("没有需要保存的变化。"); return; }
      await api.updateApplication(id, changes, detail.version);
      setSaved("已保存人工修改。"); await load(); onChanged();
    } catch (value) { setError(String(value)); }
  };
  const closeApplication = async () => {
    if (!detail) return;
    setError(""); setSaved("");
    try {
      await api.updateApplication(id, { [closeStep]: closeReason }, detail.version);
      setSaved("已记录结束环节和结果。"); await load(); onChanged();
    } catch (value) { setError(String(value)); }
  };
  if (!detail) return <>{error ? <Notice kind="error">{error}</Notice> : <p className="empty">正在读取申请详情…</p>}</>;
  const stage = displayStage(detail.values);
  const terminal = TERMINAL_PATTERN.test(stage);
  return <>
    <header className="page-header"><div><a className="back" href="#/applications">← 返回申请追踪</a><h1>{detail.company}</h1><p>{detail.role}</p></div><span className="badge">版本 {detail.version}</span></header>
    {terminal && <div className="terminal-banner"><strong>已结束</strong><span>{stage}</span></div>}
    {error && <Notice kind="error">{error}</Notice>}{saved && <Notice kind="success">{saved}</Notice>}
    <div className="detail-grid"><section className="panel"><h2>申请字段</h2><form className="field-grid" onSubmit={save}>
      {EDITABLE_FIELDS.map((field) => <label key={field}>{field}{field === "备注" ? <textarea value={values[field]} onChange={(e) => setValues({ ...values, [field]: e.target.value })} /> : <input type={field.includes("时间") ? "date" : "text"} value={values[field]} onChange={(e) => setValues({ ...values, [field]: e.target.value })} />}</label>)}
      <button className="button primary">保存修改</button></form>
      <div className="close-box"><h3>结束本次申请</h3><p>记录流程停止在哪个环节；之后仍可通过修改“当前阶段”重新开启。</p><div className="actions"><label>结束环节<select value={closeStep} onChange={(event) => setCloseStep(event.target.value)}>{PROCESS_FIELDS.map((field) => <option key={field}>{field}</option>)}</select></label><label>结果<select value={closeReason} onChange={(event) => setCloseReason(event.target.value)}><option>未通过</option><option>主动结束</option></select></label><button type="button" className="button danger" onClick={() => void closeApplication()}>标记已结束</button></div></div>
      </section>
      <div><section className="panel"><h2>时间线</h2>{detail.timeline.length ? <ol className="timeline">{detail.timeline.map((item, index) => <li key={`${item.created_at}-${index}`}><b>{String(item.payload.field ?? item.event_type)}</b><span>{String(item.payload.value ?? "")}</span><time>{new Date(item.created_at).toLocaleString()}</time></li>)}</ol> : <p className="empty">暂无时间线。</p>}</section>
      <section className="panel"><h2>邮件证据</h2>{detail.emails.length ? detail.emails.map((mail, index) => <article className="evidence" key={`${mail.subject}-${index}`}><b>{mail.subject}</b><span>{mail.sender}</span><time>{mail.sent_at ? new Date(mail.sent_at).toLocaleString() : "时间未知"}</time></article>) : <p className="empty">暂无关联邮件。</p>}</section></div>
    </div>
  </>;
}

function MailPage({ settings, onDone }: { settings: Settings | null; onDone: () => void }) {
  const [since, setSince] = useState(new Date(Date.now() - 30 * 86400000).toISOString().slice(0, 10));
  const [limit, setLimit] = useState(100);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const body = { account_id: settings?.account_id, email: settings?.email, since, limit };
  const run = async (test: boolean) => {
    setError(""); setMessage(test ? "正在测试连接…" : "正在同步邮箱…");
    try {
      if (test) { await api.testMail(body); setMessage("163 邮箱连接正常。"); }
      else {
        const result = await api.syncMail({ ...body, tracker_path: settings?.tracker_path });
        setMessage(`同步完成，处理 ${result.processed} 封相关邮件。`); onDone();
      }
    } catch (value) { setMessage(""); setError(String(value)); }
  };
  return <><header className="page-header"><div><p className="eyebrow">只读 IMAP</p><h1>邮件同步</h1><p>仅读取收件箱，不标记、不移动、不删除邮件。</p></div></header>
    {!settings?.email && <Notice kind="info">请先在设置中填写 163 邮箱并保存授权码。</Notice>}
    {message && <Notice kind="success">{message}</Notice>}{error && <Notice kind="error">{error}</Notice>}
    <section className="panel form-stack"><label>同步起始日期<input type="date" value={since} onChange={(e) => setSince(e.target.value)} /></label><label>最多读取<input type="number" min={1} max={500} value={limit} onChange={(e) => setLimit(Number(e.target.value))} /></label><div className="actions"><button className="button" onClick={() => void run(true)} disabled={!settings?.email}>测试连接</button><button className="button primary" onClick={() => void run(false)} disabled={!settings?.email}>同步邮箱</button></div></section>
  </>;
}

function ExcelPage({ settings, onDone }: { settings: Settings | null; onDone: () => void }) {
  const [message, setMessage] = useState(""); const [error, setError] = useState("");
  const run = async (direction: "import" | "export") => {
    setError(""); setMessage("正在执行…");
    try { await api.syncExcel(settings?.tracker_path ?? "tracker.xlsx", direction); setMessage(direction === "import" ? "Excel 导入完成。" : "Excel 导出完成。"); onDone(); }
    catch (value) { setMessage(""); setError(String(value)); }
  };
  return <><header className="page-header"><div><p className="eyebrow">双向同步</p><h1>Excel 同步</h1><p>路径：{settings?.tracker_path ?? "tracker.xlsx"}</p></div></header>
    {message && <Notice kind="success">{message}</Notice>}{error && <Notice kind="error">{error}</Notice>}
    <section className="panel"><h2>选择方向</h2><p>导入会把工作簿中的人工内容写入数据库；导出会生成最新 Tracker。</p><div className="actions"><button className="button" onClick={() => void run("import")}>从 Excel 导入</button><button className="button primary" onClick={() => void run("export")}>导出到 Excel</button></div></section>
  </>;
}

function JobsPage({ refresh }: { refresh: number }) {
  const [jobs, setJobs] = useState<Job[]>([]); const [error, setError] = useState("");
  const load = async () => { try { setJobs(await api.jobs()); } catch (value) { setError(String(value)); } };
  useEffect(() => { void load(); }, [refresh]);
  const resume = async (id: string) => { try { await api.resumeJob(id); await load(); } catch (value) { setError(String(value)); } };
  return <><header className="page-header"><div><p className="eyebrow">可恢复任务</p><h1>任务</h1><p>查看同步进度、安全错误和恢复入口。</p></div><button className="button" onClick={() => void load()}>刷新</button></header>
    {error && <Notice kind="error">{error}</Notice>}<section className="panel">{jobs.length ? <div className="job-list">{jobs.map((job) => <article key={job.job_id}><div><b>{job.job_type}</b><span className={`status ${job.status}`}>{job.status}</span><p>{job.current_step ?? "等待开始"}</p>{job.error_message_safe && <p className="error-text">{job.error_message_safe}</p>}</div>{job.retryable && <button className="button" onClick={() => void resume(job.job_id)}>继续任务</button>}</article>)}</div> : <p className="empty">还没有后台任务。</p>}</section>
  </>;
}

function SettingsPage({ value, onSaved }: { value: Settings | null; onSaved: (settings: Settings) => void }) {
  const [form, setForm] = useState<Record<string, string | boolean>>({});
  const [message, setMessage] = useState(""); const [error, setError] = useState("");
  useEffect(() => { if (value) setForm({ ...value, mail_secret: "", model_secret: "", brave_secret: "" }); }, [value]);
  const field = (name: string, next: string) => setForm({ ...form, [name]: next });
  const save = async (event: FormEvent) => {
    event.preventDefault(); setError(""); setMessage("");
    try {
      const payload = Object.fromEntries(Object.entries(form).filter(([key, item]) => !key.endsWith("_saved") && item !== ""));
      const saved = await api.saveSettings(payload); onSaved(saved); setMessage("设置已保存，密钥不会回显。");
    } catch (value) { setError(String(value)); }
  };
  if (!value) return <p className="empty">正在读取设置…</p>;
  return <><header className="page-header"><div><p className="eyebrow">本机配置</p><h1>设置</h1><p>非敏感配置写入 data；密钥进入 Windows Credential Manager。</p></div></header>
    {message && <Notice kind="success">{message}</Notice>}{error && <Notice kind="error">{error}</Notice>}
    <form className="panel settings-form" onSubmit={save}><h2>邮箱与路径</h2><div className="field-grid">
      <label>账户 ID<input value={String(form.account_id ?? "")} onChange={(e) => field("account_id", e.target.value)} required /></label>
      <label>163 邮箱<input type="email" value={String(form.email ?? "")} onChange={(e) => field("email", e.target.value)} /></label>
      <label>Excel 路径<input value={String(form.tracker_path ?? "")} onChange={(e) => field("tracker_path", e.target.value)} required /></label>
      <label>Markdown 路径<input value={String(form.markdown_path ?? "")} onChange={(e) => field("markdown_path", e.target.value)} required /></label>
      <label>163 授权码 <small>{value.mail_secret_saved ? "已保存" : "未保存"}</small><input type="password" autoComplete="new-password" value={String(form.mail_secret ?? "")} onChange={(e) => field("mail_secret", e.target.value)} placeholder="留空则不修改" /></label>
    </div><h2>Stage 4B 服务</h2><div className="field-grid">
      <label>模型 Base URL<input value={String(form.model_base_url ?? "")} onChange={(e) => field("model_base_url", e.target.value)} placeholder="https://api.example.com/v1" /></label>
      <label>模型名称<input value={String(form.model_name ?? "")} onChange={(e) => field("model_name", e.target.value)} /></label>
      <label>模型 API Key <small>{value.model_secret_saved ? "已保存" : "未保存"}</small><input type="password" autoComplete="new-password" value={String(form.model_secret ?? "")} onChange={(e) => field("model_secret", e.target.value)} placeholder="留空则不修改" /></label>
      <label>Brave Search API Key <small>{value.brave_secret_saved ? "已保存" : "未保存"}</small><input type="password" autoComplete="new-password" value={String(form.brave_secret ?? "")} onChange={(e) => field("brave_secret", e.target.value)} placeholder="留空则不修改" /></label>
    </div><Notice>自动调度保持关闭。Summary 只会在 4B 中由你手动触发。</Notice><button className="button primary">保存设置</button></form>
  </>;
}

export default function App() {
  const current = useRoute();
  const [applications, setApplications] = useState<Application[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [settings, setSettings] = useState<Settings | null>(null);
  const [refresh, setRefresh] = useState(0);
  const reload = async () => {
    const [nextApplications, nextJobs, nextSettings] = await Promise.all([
      api.applications(), api.jobs(), api.settings(),
    ]);
    setApplications(nextApplications); setJobs(nextJobs); setSettings(nextSettings);
  };
  useEffect(() => { void reload(); }, [refresh]);
  const changed = () => setRefresh((value) => value + 1);
  let content: React.ReactNode;
  if (current.page === "overview") content = <Overview applications={applications} jobs={jobs} />;
  else if (current.page === "applications") content = <ApplicationsPage onChanged={changed} />;
  else if (current.page === "detail" && current.id) content = <DetailPage id={current.id} onChanged={changed} />;
  else if (current.page === "mail") content = <MailPage settings={settings} onDone={changed} />;
  else if (current.page === "excel") content = <ExcelPage settings={settings} onDone={changed} />;
  else if (current.page === "jobs") content = <JobsPage refresh={refresh} />;
  else content = <SettingsPage value={settings} onSaved={(next) => { setSettings(next); changed(); }} />;
  return <div className="app-shell"><aside><a className="brand" href="#/overview"><span>CP</span><div><b>CareerPilot</b><small>职业领航员</small></div></a><nav>{NAV.map(([page, label, icon]) => <a key={page} href={`#/${page}`} className={current.page === page || (current.page === "detail" && page === "applications") ? "active" : ""}><span>{icon}</span>{label}</a>)}</nav><div className="local"><i />本地运行 · 9998</div></aside><main>{content}</main></div>;
}
