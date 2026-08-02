import { FormEvent, useEffect, useState } from "react";
import {
  api,
  Application,
  NotificationItem,
  OAuthConnection,
  PrefillSession,
  Reminder,
} from "./api";
import "./stage7.css";

function Message({ error, message }: { error: string; message: string }) {
  if (error) return <div className="notice error" role="alert">{error}</div>;
  if (message) return <div className="notice success" role="status">{message}</div>;
  return null;
}

export default function IntegrationsPage({ applications }: { applications: Application[] }) {
  const [connections, setConnections] = useState<OAuthConnection[]>([]);
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [provider, setProvider] = useState<"gmail" | "outlook">("gmail");
  const [accountId, setAccountId] = useState("");
  const [email, setEmail] = useState("");
  const [applicationId, setApplicationId] = useState("");
  const [title, setTitle] = useState("");
  const [dueAt, setDueAt] = useState("");
  const [prefillApplicationId, setPrefillApplicationId] = useState("");
  const [targetUrl, setTargetUrl] = useState("");
  const [profile, setProfile] = useState<Record<string, string>>({});
  const [session, setSession] = useState<PrefillSession | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const load = async () => {
    const [nextConnections, nextReminders, nextNotifications] = await Promise.all([
      api.oauthConnections(),
      api.reminders(),
      api.scanNotifications(),
    ]);
    setConnections(nextConnections);
    setReminders(nextReminders);
    setNotifications(nextNotifications);
  };

  useEffect(() => {
    void load().catch((value) => setError(String(value)));
  }, []);

  const connect = async (event: FormEvent) => {
    event.preventDefault(); setError(""); setMessage("正在创建最小权限授权请求…");
    try {
      const result = await api.startOAuth(provider, accountId, email);
      window.location.assign(result.authorization_url);
    } catch (value) { setMessage(""); setError(String(value)); }
  };

  const disconnect = async (connection: OAuthConnection) => {
    setError(""); setMessage("");
    try {
      await api.disconnectOAuth(connection.account_id);
      await load(); setMessage(`${connection.email} 已断开，本机令牌已移除。`);
    } catch (value) { setError(String(value)); }
  };

  const addReminder = async (event: FormEvent) => {
    event.preventDefault(); setError(""); setMessage("");
    try {
      await api.createReminder(applicationId, title, new Date(dueAt).toISOString());
      setTitle(""); setDueAt(""); await load(); setMessage("提醒已保存，可导出到系统日历。");
    } catch (value) { setError(String(value)); }
  };

  const dismiss = async (item: Reminder) => {
    try { await api.dismissReminder(item.reminder_id); await load(); }
    catch (value) { setError(String(value)); }
  };

  const enableBrowserNotifications = async () => {
    setError("");
    if (!("Notification" in window)) { setError("当前浏览器不支持系统通知。"); return; }
    const permission = await Notification.requestPermission();
    if (permission !== "granted") { setError("浏览器通知未获授权；站内提醒仍然可用。"); return; }
    const unread = notifications.filter((item) => item.status === "unread");
    unread.slice(0, 3).forEach((item) => new Notification(item.title, {
      body: `${item.company} / ${item.role} · ${new Date(item.due_at).toLocaleString()}`,
      tag: item.notification_id,
    }));
    setMessage(unread.length ? "已发送当前待办的浏览器通知。" : "通知权限已开启，当前没有待办提醒。");
  };

  const markRead = async (item: NotificationItem) => {
    try { await api.readNotification(item.notification_id); await load(); }
    catch (value) { setError(String(value)); }
  };

  const createPrefill = async (event: FormEvent) => {
    event.preventDefault(); setError(""); setMessage("");
    try {
      const created = await api.createPrefillSession(prefillApplicationId, targetUrl, profile);
      setSession(created); setMessage("预填会话已创建。请在目标网页中打开 CareerPilot 本地扩展进行差异预览。");
    } catch (value) { setError(String(value)); }
  };

  const profileField = (key: string, value: string) => setProfile({ ...profile, [key]: value });
  return <>
    <header className="page-header"><div><p className="eyebrow">Stage 7 · External integrations</p><h1>外部集成</h1><p>只读连接邮箱、安排提醒，并在人工确认后预填网页表单。验证码与最终提交始终由你完成。</p></div><a className="button" href={api.reminderIcsUrl()}>导出 ICS 日历</a></header>
    <Message error={error} message={message} />
    <section className="panel integration-section"><div className="section-title"><div><h2>Gmail / Outlook 只读连接</h2><p>使用 OAuth 与最小邮件读取权限；令牌只进入系统密钥库，不写入业务数据库。</p></div></div>
      <form className="inline-form" onSubmit={connect}><label>服务<select value={provider} onChange={(event) => setProvider(event.target.value as "gmail" | "outlook")}><option value="gmail">Gmail</option><option value="outlook">Outlook</option></select></label><label>账户 ID<input value={accountId} onChange={(event) => setAccountId(event.target.value)} pattern="[A-Za-z0-9][A-Za-z0-9._-]{0,99}" placeholder="work-mail" required /></label><label>邮箱<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required /></label><button className="button primary">前往授权</button></form>
      {connections.length ? <div className="integration-list">{connections.map((item) => <article key={item.account_id}><div><b>{item.email}</b><span>{item.provider === "gmail" ? "Gmail API" : "Microsoft Graph"} · 只读</span></div><span className={`status ${item.status === "connected" ? "succeeded" : ""}`}>{item.status === "connected" ? "已连接" : item.status}</span><button className="button" onClick={() => void disconnect(item)} disabled={!item.token_saved}>断开</button></article>)}</div> : <p className="empty">尚未连接 Gmail 或 Outlook。</p>}
    </section>
    <div className="integration-grid">
      <section className="panel"><div className="section-title"><div><h2>提醒与日历</h2><p>本地保存，到期前 3 天生成站内提醒。</p></div></div><form className="form-stack compact" onSubmit={addReminder}><label>岗位<select value={applicationId} onChange={(event) => setApplicationId(event.target.value)} required><option value="">请选择</option>{applications.map((item) => <option key={item.application_id} value={item.application_id}>{item.company} / {item.role}</option>)}</select></label><label>提醒内容<input value={title} onChange={(event) => setTitle(event.target.value)} maxLength={300} placeholder="准备面试材料" required /></label><label>时间<input type="datetime-local" value={dueAt} onChange={(event) => setDueAt(event.target.value)} required /></label><button className="button primary">添加提醒</button></form>
        <div className="reminder-list">{reminders.filter((item) => item.status === "scheduled").map((item) => <article key={item.reminder_id}><div><b>{item.title}</b><span>{item.company} / {item.role}</span><time>{new Date(item.due_at).toLocaleString()}</time></div><button className="button" onClick={() => void dismiss(item)}>完成</button></article>)}</div>
      </section>
      <section className="panel"><div className="section-title"><div><h2>通知中心</h2><p>系统通知必须由你主动授权；拒绝后不影响站内提醒。</p></div><button className="button" onClick={() => void enableBrowserNotifications()}>开启浏览器通知</button></div>
        <div className="notification-list">{notifications.length ? notifications.map((item) => <button key={item.notification_id} className={item.status} onClick={() => void markRead(item)}><span className={`signal ${item.kind}`} /><span><b>{item.title}</b><small>{item.company} · {new Date(item.due_at).toLocaleString()}</small></span></button>) : <p className="empty">未来 3 天没有提醒。</p>}</div>
      </section>
    </div>
    <section className="panel integration-section"><div className="section-title"><div><h2>浏览器表单预填</h2><p>本地扩展仅在当前标签页识别字段、显示差异并填值；不会读取密码、上传文件、处理验证码或提交表单。</p></div><span className="badge">人工确认边界</span></div>
      <form className="prefill-form" onSubmit={createPrefill}><label>岗位<select value={prefillApplicationId} onChange={(event) => setPrefillApplicationId(event.target.value)} required><option value="">请选择</option>{applications.map((item) => <option key={item.application_id} value={item.application_id}>{item.company} / {item.role}</option>)}</select></label><label>目标表单网址<input type="url" value={targetUrl} onChange={(event) => setTargetUrl(event.target.value)} placeholder="https://jobs.example.com/apply" required /></label><label>姓名<input value={profile.full_name ?? ""} onChange={(event) => profileField("full_name", event.target.value)} /></label><label>邮箱<input type="email" value={profile.email ?? ""} onChange={(event) => profileField("email", event.target.value)} /></label><label>电话<input type="tel" value={profile.phone ?? ""} onChange={(event) => profileField("phone", event.target.value)} /></label><label>所在地<input value={profile.location ?? ""} onChange={(event) => profileField("location", event.target.value)} /></label><label>个人网站<input type="url" value={profile.website ?? ""} onChange={(event) => profileField("website", event.target.value)} /></label><label>LinkedIn<input type="url" value={profile.linkedin ?? ""} onChange={(event) => profileField("linkedin", event.target.value)} /></label><button className="button primary">创建预填会话</button></form>
      {session && <div className="prefill-handoff"><div><span>会话 ID</span><code>{session.session_id}</code></div><div><span>允许网站</span><code>{session.target_origin}</code></div><p>在 Chrome/Edge 扩展管理页加载仓库中的 <code>browser-extension</code> 文件夹，然后打开目标表单，点击扩展并粘贴会话 ID。扩展会先展示差异；检测到验证码时会停止。</p></div>}
    </section>
  </>;
}
