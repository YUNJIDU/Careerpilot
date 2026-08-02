import { FormEvent, useEffect, useMemo, useState } from "react";
import type { Icon } from "@phosphor-icons/react";
import { ArrowUpRight, ArrowsLeftRight, ClockCounterClockwise, EnvelopeSimple, FileText, GearSix, House, ListChecks, PlugsConnected, ShieldCheck } from "@phosphor-icons/react";
import { api, Application, ApplicationDetail, Attachment, Job, MailAccount, MailSample, ResumeVersion, Settings, Summary } from "./api";
import AgentPage from "./AgentPage";
import EvidencePage from "./EvidencePage";
import IntegrationsPage from "./IntegrationsPage";
import WelcomePage from "./WelcomePage";
import "./stage5.css";
import "./stage6.css";
import "./app-theme.css";

type Page = "welcome" | "overview" | "applications" | "detail" | "evidence" | "agent" | "mail" | "resumes" | "integrations" | "excel" | "jobs" | "settings";

const NAV: Array<[Page, string, Icon]> = [
  ["overview", "总览", House],
  ["applications", "申请追踪", ListChecks],
  ["mail", "邮件同步", EnvelopeSimple],
  ["resumes", "简历管理", FileText],
  ["integrations", "外部集成", PlugsConnected],
  ["excel", "Excel 同步", ArrowsLeftRight],
  ["jobs", "任务", ClockCounterClockwise],
  ["settings", "设置", GearSix],
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
  const value = location.hash.slice(2) || "welcome";
  if (value.startsWith("applications/")) {
    const parts = value.split("/");
    return { page: parts[2] === "evidence" ? "evidence" : parts[2] === "agent" ? "agent" : "detail", id: parts[1] };
  }
  if (value === "welcome") return { page: "welcome" };
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
  const [summaries, setSummaries] = useState<Summary[]>([]);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [values, setValues] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [saved, setSaved] = useState("");
  const [closeStep, setCloseStep] = useState("笔试");
  const [closeReason, setCloseReason] = useState("未通过");
  const [dataLeavingConfirmed, setDataLeavingConfirmed] = useState(false);
  const [generating, setGenerating] = useState(false);
  const load = async () => {
    try {
      const [item, versions, files] = await Promise.all([api.application(id), api.summaries(id), api.attachments(id)]);
      setDetail(item); setSummaries(versions); setAttachments(files);
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
  const generateSummary = async () => {
    if (!dataLeavingConfirmed) return;
    setGenerating(true); setError(""); setSaved("");
    try {
      const result = await api.generateSummary(id);
      setSaved(`Summary v${result.summary.version} 已生成，并已更新 Markdown。`);
      setDataLeavingConfirmed(false); await load(); onChanged();
    } catch (value) { setError(String(value)); }
    finally { setGenerating(false); }
  };
  const approveAttachment = async (attachment: Attachment) => {
    setError(""); setSaved("");
    try {
      await api.approveAttachment(attachment.attachment_id);
      setSaved(`${attachment.filename} 已批准并安全保存。`); await load();
    } catch (value) { setError(String(value)); }
  };
  if (!detail) return <>{error ? <Notice kind="error">{error}</Notice> : <p className="empty">正在读取申请详情…</p>}</>;
  const stage = displayStage(detail.values);
  const terminal = TERMINAL_PATTERN.test(stage);
  return <>
    <header className="page-header"><div><a className="back" href="#/applications">← 返回申请追踪</a><h1>{detail.company}</h1><p>{detail.role}</p></div><div className="actions"><a className="button" href={`#/applications/${id}/evidence`}>证据分析</a><a className="button primary" href={`#/applications/${id}/agent`}>Agent 协助</a><span className="badge">版本 {detail.version}</span></div></header>
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
    <section className="panel"><div className="section-title"><div><h2>邮件附件</h2><p>这里只自动保存元数据；文件内容必须由你逐个批准后才会获取。</p></div></div>
      {attachments.length ? <div className="table-wrap"><table><thead><tr><th>文件</th><th>类型</th><th>大小</th><th>状态</th><th>操作</th></tr></thead><tbody>{attachments.map((attachment) => <tr key={attachment.attachment_id}><td>{attachment.filename}</td><td>{attachment.content_type}</td><td>{attachment.size == null ? "未知" : `${(attachment.size / 1024).toFixed(1)} KiB`}</td><td><span className={`status ${attachment.status === "stored" ? "succeeded" : attachment.status === "pending" ? "" : "failed"}`}>{attachment.status === "pending" ? "待批准" : attachment.status === "stored" ? "已保存" : "已拒绝"}</span>{attachment.rejection_reason && <small className="file-reason">{attachment.rejection_reason}</small>}</td><td>{attachment.status === "pending" ? <button className="button primary" onClick={() => void approveAttachment(attachment)}>批准获取</button> : attachment.download_url ? <a className="button" href={api.contentUrl(attachment.download_url)}>下载</a> : "—"}</td></tr>)}</tbody></table></div> : <p className="empty">关联邮件中没有附件。</p>}
    </section>
    <section className="panel summary-panel"><div className="section-title"><div><h2>公开信息 Summary</h2><p>手动调用 Tavily Top 5 和已配置模型；结果仅供信息整理。</p></div>{summaries.length > 0 && <a className="button" href={api.markdownUrl(id)} target="_blank" rel="noreferrer">查看 Markdown</a>}</div>
      <div className="data-warning"><strong>数据将离开本机</strong><p>公司、职位、现有客观邮件证据及公开网页正文会发送给已配置的模型服务。不会发送邮箱或 API 密钥。</p><label className="checkbox"><input type="checkbox" checked={dataLeavingConfirmed} onChange={(event) => setDataLeavingConfirmed(event.target.checked)} />我了解并确认本次调用</label><button className="button primary" disabled={!dataLeavingConfirmed || generating} onClick={() => void generateSummary()}>{generating ? "正在搜索并生成…" : "生成新 Summary"}</button></div>
      {summaries.length ? <SummaryView summary={summaries[0]} versions={summaries} /> : <p className="empty">尚未生成 Summary。</p>}
    </section>
  </>;
}

function SummaryView({ summary, versions }: { summary: Summary; versions: Summary[] }) {
  const sections: Array<[string, string[]]> = [
    ["JD 要点", summary.content.jd_highlights],
    ["流程线索", summary.content.process_clues],
    ["笔试信息", summary.content.written_test],
    ["面试信息", summary.content.interview],
    ["已知事实", summary.content.known_facts],
    ["未知与不确定项", summary.content.unknowns],
  ];
  return <article className="summary-result"><div className="summary-meta"><span className="badge">最新版本 v{summary.version}</span><span>{new Date(summary.created_at).toLocaleString()}</span><span>历史版本：{versions.map((item) => `v${item.version}`).join("、")}</span></div><p className="summary-overview">{summary.content.overview}</p><div className="summary-grid">{sections.map(([title, items]) => <section key={title}><h3>{title}</h3>{items.length ? <ul>{items.map((item, index) => <li key={`${title}-${index}`}>{item}</li>)}</ul> : <p>暂无信息</p>}</section>)}</div><h3>来源</h3><ol className="sources">{summary.content.sources.map((source) => <li key={source.url}><a href={source.url} target="_blank" rel="noreferrer">{source.title}</a><time>{new Date(source.fetched_at).toLocaleString()}</time></li>)}</ol></article>;
}

function MailPage({ settings, onDone }: { settings: Settings | null; onDone: () => void }) {
  const [accounts, setAccounts] = useState<MailAccount[]>([]);
  const [samples, setSamples] = useState<MailSample[]>([]);
  const [accountId, setAccountId] = useState("");
  const [email, setEmail] = useState("");
  const [authorizationCode, setAuthorizationCode] = useState("");
  const [sampleFile, setSampleFile] = useState<File | null>(null);
  const [sampleInputKey, setSampleInputKey] = useState(0);
  const [since, setSince] = useState(new Date(Date.now() - 30 * 86400000).toISOString().slice(0, 10));
  const [limit, setLimit] = useState(100);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const load = async () => {
    const [nextAccounts, nextSamples] = await Promise.all([api.mailAccounts(), api.mailSamples()]);
    setAccounts(nextAccounts); setSamples(nextSamples);
  };
  useEffect(() => { void load().catch((value) => setError(String(value))); }, []);
  const save = async (event: FormEvent) => {
    event.preventDefault(); setError(""); setMessage("");
    try {
      await api.saveMailAccount(accountId, {
        adapter: "imap163", email,
        ...(authorizationCode ? { authorization_code: authorizationCode } : {}),
      });
      setAccountId(""); setEmail(""); setAuthorizationCode("");
      await load(); setMessage("邮箱账户已保存，授权码不会回显。");
    } catch (value) { setMessage(""); setError(String(value)); }
  };
  const run = async (account: MailAccount, test: boolean) => {
    setError(""); setMessage(test ? `正在测试 ${account.email}…` : `正在同步 ${account.email}…`);
    try {
      if (test) { await api.testRegisteredMail(account.account_id); setMessage(`${account.email} 连接正常。`); }
      else { const result = await api.syncRegisteredMail(account.account_id, { since, limit, tracker_path: settings?.tracker_path }); setMessage(`${account.email} 同步完成，处理 ${result.processed} 封相关邮件。`); onDone(); }
    } catch (value) { setMessage(""); setError(String(value)); }
  };
  const toggle = async (account: MailAccount) => {
    try { await api.setMailAccountEnabled(account.account_id, !account.enabled); await load(); }
    catch (value) { setError(String(value)); }
  };
  const syncAll = async () => {
    setError(""); setMessage("正在按顺序同步全部邮箱…"); let processed = 0;
    try {
      for (const account of accounts.filter((item) => item.enabled && item.credential_saved)) {
        processed += (await api.syncRegisteredMail(account.account_id, { since, limit, tracker_path: settings?.tracker_path })).processed;
      }
      setMessage(`全部邮箱同步完成，共处理 ${processed} 封相关邮件。`); onDone();
    } catch (value) { setMessage(""); setError(String(value)); }
  };
  const importSample = async (event: FormEvent) => {
    event.preventDefault();
    if (!sampleFile) return;
    setError(""); setMessage("正在导入本地邮件样本…");
    try {
      const result = await api.importMailSample(sampleFile, settings?.tracker_path ?? "tracker.xlsx");
      setSampleFile(null); setSampleInputKey((value) => value + 1);
      await load();
      setMessage(`样本已安全保存，本次处理 ${result.processed} 封相关邮件。`);
      onDone();
    } catch (value) { setMessage(""); setError(String(value)); }
  };
  const syncable = accounts.filter((item) => item.enabled && item.credential_saved);
  return <><header className="page-header"><div><p className="eyebrow">只读 IMAP</p><h1>邮件同步</h1><p>管理多个 163 邮箱；仅读取，不标记、不移动、不删除邮件。</p></div><button className="button primary" onClick={() => void syncAll()} disabled={!syncable.length}>同步全部</button></header>
    {message && <Notice kind="success">{message}</Notice>}{error && <Notice kind="error">{error}</Notice>}
    <form className="panel inline-form" onSubmit={save}><label>账户 ID<input pattern="[A-Za-z0-9][A-Za-z0-9._-]{0,99}" value={accountId} onChange={(event) => setAccountId(event.target.value)} required /></label><label>163 邮箱<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required /></label><label>163 授权码<input type="password" autoComplete="new-password" value={authorizationCode} onChange={(event) => setAuthorizationCode(event.target.value)} placeholder="留空则只登记账户" /></label><button className="button primary">保存账户</button></form>
    <form className="panel form-stack" onSubmit={importSample}>
      <div className="section-title"><div><h2>导入本地 .eml</h2><p>原始邮件最多 2 MiB；仅在本机解析，不会调用搜索或模型服务。</p></div><button className="button primary" disabled={!sampleFile || sampleFile.size > 2 * 1024 * 1024}>导入样本</button></div>
      <label>邮件文件<input key={sampleInputKey} type="file" accept=".eml,message/rfc822" onChange={(event) => setSampleFile(event.target.files?.[0] ?? null)} /></label>
      {sampleFile && <p>{sampleFile.name} · {(sampleFile.size / 1024).toFixed(1)} KiB{sampleFile.size > 2 * 1024 * 1024 ? "（超过限制）" : ""}</p>}
    </form>
    <section className="panel"><h2>最近导入样本</h2>{samples.length ? <div className="table-wrap"><table><thead><tr><th>主题</th><th>发件人</th><th>邮件时间</th><th>大小</th></tr></thead><tbody>{samples.map((sample) => <tr key={sample.sample_id}><td>{sample.subject || "（无主题）"}</td><td>{sample.sender || "未知"}</td><td>{sample.sent_at ? new Date(sample.sent_at).toLocaleString() : "未知"}</td><td>{(sample.size / 1024).toFixed(1)} KiB</td></tr>)}</tbody></table></div> : <p className="empty">还没有本地邮件样本。</p>}</section>
    <section className="panel form-stack"><label>同步起始日期<input type="date" value={since} onChange={(e) => setSince(e.target.value)} /></label><label>每个邮箱最多读取<input type="number" min={1} max={500} value={limit} onChange={(e) => setLimit(Number(e.target.value))} /></label></section>
    <section className="panel"><h2>邮箱账户</h2>{accounts.length ? <div className="table-wrap"><table><thead><tr><th>账户</th><th>邮箱</th><th>授权码</th><th>状态</th><th>操作</th></tr></thead><tbody>{accounts.map((account) => <tr key={account.account_id}><td>{account.account_id}</td><td>{account.email}</td><td>{account.credential_saved ? "已保存" : "未保存"}</td><td><span className={`status ${account.enabled ? "succeeded" : "failed"}`}>{account.enabled ? "已启用" : "已停用"}</span></td><td><div className="actions"><button className="button" onClick={() => void run(account, true)} disabled={!account.enabled || !account.credential_saved}>测试</button><button className="button primary" onClick={() => void run(account, false)} disabled={!account.enabled || !account.credential_saved}>同步</button><button className="button" onClick={() => void toggle(account)}>{account.enabled ? "停用" : "启用"}</button></div></td></tr>)}</tbody></table></div> : <p className="empty">还没有邮箱账户。</p>}</section>
  </>;
}

function ResumesPage({ applications }: { applications: Application[] }) {
  const [versions, setVersions] = useState<ResumeVersion[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [label, setLabel] = useState("");
  const [resumeId, setResumeId] = useState("");
  const [applicationId, setApplicationId] = useState("");
  const [linkApplicationId, setLinkApplicationId] = useState("");
  const [inputKey, setInputKey] = useState(0);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const load = async () => setVersions(await api.resumes());
  useEffect(() => { void load().catch((value) => setError(String(value))); }, []);
  const upload = async (event: FormEvent) => {
    event.preventDefault(); if (!file) return;
    setMessage("正在安全保存简历…"); setError("");
    try {
      const saved = await api.uploadResume(file, label, resumeId || undefined, applicationId || undefined);
      setFile(null); setLabel(""); setResumeId(""); setApplicationId(""); setInputKey((value) => value + 1);
      await load(); setMessage(`${saved.label} v${saved.version} 已保存。`);
    } catch (value) { setMessage(""); setError(String(value)); }
  };
  const link = async (version: ResumeVersion) => {
    if (!linkApplicationId) return;
    try { await api.linkResume(version.version_id, linkApplicationId); await load(); setMessage("岗位关联已保存。"); }
    catch (value) { setError(String(value)); }
  };
  const documents = [...new Map(versions.map((item) => [item.resume_id, item])).values()];
  const applicationName = (id: string) => {
    const item = applications.find((application) => application.application_id === id);
    return item ? `${item.company} / ${item.role}` : id;
  };
  return <><header className="page-header"><div><p className="eyebrow">本地版本库</p><h1>简历管理</h1><p>安全保存 PDF、DOCX 或 TXT；这里只管理版本和岗位关联，不做解析、评分或自动投递。</p></div></header>
    {message && <Notice kind="success">{message}</Notice>}{error && <Notice kind="error">{error}</Notice>}
    <form className="panel form-stack" onSubmit={upload}><div className="section-title"><div><h2>新增简历版本</h2><p>最多 5 MiB；DOCX 宏、脚本、压缩包和伪造类型会被拒绝。</p></div><button className="button primary" disabled={!file || !label}>安全保存</button></div>
      <label>简历文件<input key={inputKey} type="file" accept=".pdf,.docx,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain" onChange={(event) => setFile(event.target.files?.[0] ?? null)} required /></label>
      <label>名称<input value={label} maxLength={200} onChange={(event) => setLabel(event.target.value)} placeholder="例如：后端开发简历" required /></label>
      <label>版本归属<select value={resumeId} onChange={(event) => setResumeId(event.target.value)}><option value="">新建一份简历</option>{documents.map((item) => <option key={item.resume_id} value={item.resume_id}>作为“{item.label}”的新版本</option>)}</select></label>
      <label>同时关联岗位<select value={applicationId} onChange={(event) => setApplicationId(event.target.value)}><option value="">暂不关联</option>{applications.map((item) => <option key={item.application_id} value={item.application_id}>{item.company} / {item.role}</option>)}</select></label>
      {file && <p>{file.name} · {(file.size / 1024).toFixed(1)} KiB</p>}
    </form>
    <section className="panel"><div className="section-title"><div><h2>已保存版本</h2><p>选择岗位后，可把任意具体版本关联到该岗位。</p></div><label>待关联岗位<select value={linkApplicationId} onChange={(event) => setLinkApplicationId(event.target.value)}><option value="">请选择</option>{applications.map((item) => <option key={item.application_id} value={item.application_id}>{item.company} / {item.role}</option>)}</select></label></div>
      {versions.length ? <div className="table-wrap"><table><thead><tr><th>简历</th><th>版本</th><th>文件</th><th>已关联岗位</th><th>操作</th></tr></thead><tbody>{versions.map((version) => <tr key={version.version_id}><td>{version.label}</td><td>v{version.version}</td><td>{version.filename}<small className="file-reason">{(version.size / 1024).toFixed(1)} KiB</small></td><td>{version.application_ids.length ? version.application_ids.map(applicationName).join("；") : "未关联"}</td><td><div className="actions"><a className="button" href={api.contentUrl(version.download_url)}>下载</a><button className="button primary" disabled={!linkApplicationId || version.application_ids.includes(linkApplicationId)} onClick={() => void link(version)}>关联</button></div></td></tr>)}</tbody></table></div> : <p className="empty">尚未保存简历。</p>}
    </section>
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
  useEffect(() => { if (value) setForm({ ...value, mail_secret: "", model_secret: "", tavily_secret: "", gmail_client_id: "", gmail_client_secret: "", outlook_client_id: "", outlook_client_secret: "" }); }, [value]);
  const field = (name: string, next: string) => setForm({ ...form, [name]: next });
  const save = async (event: FormEvent) => {
    event.preventDefault(); setError(""); setMessage("");
    try {
      const payload = Object.fromEntries(Object.entries(form).filter(([key, item]) => !key.endsWith("_saved") && item !== ""));
      const saved = await api.saveSettings(payload); onSaved(saved); setMessage("设置已保存，密钥不会回显。");
    } catch (value) { setError(String(value)); }
  };
  if (!value) return <p className="empty">正在读取设置…</p>;
  return <><header className="page-header"><div><p className="eyebrow">本机配置</p><h1>设置</h1><p>非敏感配置写入 data；Windows 密钥进入 Credential Manager，Docker 密钥在启动时注入。</p></div></header>
    {message && <Notice kind="success">{message}</Notice>}{error && <Notice kind="error">{error}</Notice>}
    <form className="panel settings-form" onSubmit={save}><h2>本地路径</h2><div className="field-grid">
      <label>Excel 路径<input value={String(form.tracker_path ?? "")} onChange={(e) => field("tracker_path", e.target.value)} required /></label>
      <label>Markdown 路径<input value={String(form.markdown_path ?? "")} onChange={(e) => field("markdown_path", e.target.value)} required /></label>
    </div><h2>Stage 4B 服务</h2><div className="field-grid">
      <label>模型 Base URL<input value={String(form.model_base_url ?? "")} onChange={(e) => field("model_base_url", e.target.value)} placeholder="https://api.example.com/v1" /></label>
      <label>模型名称<input value={String(form.model_name ?? "")} onChange={(e) => field("model_name", e.target.value)} /></label>
      <label>模型 API Key <small>{value.model_secret_saved ? "已保存" : "未保存"}</small><input type="password" autoComplete="new-password" value={String(form.model_secret ?? "")} onChange={(e) => field("model_secret", e.target.value)} placeholder="留空则不修改" /></label>
      <label>Tavily Search API Key <small>{value.tavily_secret_saved ? "已保存" : "未保存"}</small><input type="password" autoComplete="new-password" value={String(form.tavily_secret ?? "")} onChange={(e) => field("tavily_secret", e.target.value)} placeholder="留空则不修改" /></label>
    </div><h2>Stage 7 OAuth 客户端</h2><div className="field-grid">
      <label>Gmail Client ID <small>{value.gmail_client_id_saved ? "已保存" : "未保存"}</small><input type="password" autoComplete="new-password" value={String(form.gmail_client_id ?? "")} onChange={(e) => field("gmail_client_id", e.target.value)} placeholder="留空则不修改" /></label>
      <label>Gmail Client Secret <small>{value.gmail_client_secret_saved ? "已保存" : "可不填"}</small><input type="password" autoComplete="new-password" value={String(form.gmail_client_secret ?? "")} onChange={(e) => field("gmail_client_secret", e.target.value)} placeholder="公开客户端可留空" /></label>
      <label>Outlook Client ID <small>{value.outlook_client_id_saved ? "已保存" : "未保存"}</small><input type="password" autoComplete="new-password" value={String(form.outlook_client_id ?? "")} onChange={(e) => field("outlook_client_id", e.target.value)} placeholder="留空则不修改" /></label>
      <label>Outlook Client Secret <small>{value.outlook_client_secret_saved ? "已保存" : "可不填"}</small><input type="password" autoComplete="new-password" value={String(form.outlook_client_secret ?? "")} onChange={(e) => field("outlook_client_secret", e.target.value)} placeholder="公开客户端可留空" /></label>
    </div><Notice>自动调度保持关闭。Summary 只会由你手动触发；Gmail/Outlook 仅请求邮件只读权限。</Notice><button className="button primary">保存设置</button></form>
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
  useEffect(() => { if (current.page !== "welcome") void reload(); }, [refresh, current.page]);
  const changed = () => setRefresh((value) => value + 1);
  if (current.page === "welcome") return <WelcomePage />;
  let content: React.ReactNode;
  if (current.page === "overview") content = <Overview applications={applications} jobs={jobs} />;
  else if (current.page === "applications") content = <ApplicationsPage onChanged={changed} />;
  else if (current.page === "detail" && current.id) content = <DetailPage id={current.id} onChanged={changed} />;
  else if (current.page === "evidence" && current.id) content = <EvidencePage id={current.id} />;
  else if (current.page === "agent" && current.id) content = <AgentPage id={current.id} />;
  else if (current.page === "mail") content = <MailPage settings={settings} onDone={changed} />;
  else if (current.page === "resumes") content = <ResumesPage applications={applications} />;
  else if (current.page === "integrations") content = <IntegrationsPage applications={applications} />;
  else if (current.page === "excel") content = <ExcelPage settings={settings} onDone={changed} />;
  else if (current.page === "jobs") content = <JobsPage refresh={refresh} />;
  else content = <SettingsPage value={settings} onSaved={(next) => { setSettings(next); changed(); }} />;
  const workspaceTitle = ["detail", "evidence", "agent"].includes(current.page)
    ? "申请追踪"
    : NAV.find(([page]) => page === current.page)?.[1] ?? "工作台";
  return <div className="app-shell">
    <aside>
      <a className="brand" href="#/welcome"><span>CP</span><div><b>CareerPilot</b><small>职业领航员</small></div></a>
      <p className="workspace-label">CAREER OPERATING SYSTEM</p>
      <nav aria-label="工作台导航">{NAV.map(([page, label, NavIcon]) => <a key={page} href={`#/${page}`} className={current.page === page || (["detail", "evidence", "agent"].includes(current.page) && page === "applications") ? "active" : ""}><NavIcon size={20} weight="regular" />{label}</a>)}</nav>
      <div className="sidebar-trust"><ShieldCheck size={20} weight="duotone" /><span><b>本地优先</b><small>敏感凭证不进入业务页面</small></span></div>
      <div className="local"><span><i />服务正常</span><small>API 9998 · Web 9999</small></div>
    </aside>
    <main className="workspace-main">
      <header className="workspace-topbar"><span>CareerPilot / {workspaceTitle}</span><a href="#/welcome">产品首页 <ArrowUpRight size={17} /></a></header>
      <div className="workspace-content">{content}</div>
    </main>
  </div>;
}
