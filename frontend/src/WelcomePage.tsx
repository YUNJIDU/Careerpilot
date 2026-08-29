import "./welcome.css";

const capabilities = [
  ["01", "申请追踪", "集中查看岗位、阶段与最近变化"],
  ["02", "163 邮箱", "只读同步收件箱中的求职进展"],
  ["03", "Excel 同步", "以本地表格完整覆盖岗位看板"],
  ["04", "多份简历", "为不同岗位选择当前使用简历"],
] as const;

export default function WelcomePage() {
  return <div className="welcome-page">
    <header className="welcome-topbar">
      <a className="welcome-brand" href="#/welcome" aria-label="CareerPilot 首页">
        <span>CP</span><div><b>CareerPilot</b><small>职业领航员</small></div>
      </a>
      <span className="welcome-local"><i />本地运行</span>
    </header>

    <main className="welcome-hero">
      <section className="welcome-copy">
        <p className="welcome-kicker">LOCAL-FIRST CAREER WORKSPACE</p>
        <h1>让每一次求职进展<br />都有<span>清晰记录</span></h1>
        <p className="welcome-lead">集中管理申请、163 邮件、Excel 岗位数据与当前使用简历。数据默认保存在本机，关键操作始终由你确认。</p>
        <div className="welcome-actions">
          <a className="welcome-primary" href="#/overview">进入工作台 <span aria-hidden="true">→</span></a>
          <a className="welcome-secondary" href="#/settings">检查本机设置</a>
        </div>
        <p className="welcome-privacy"><span aria-hidden="true">✓</span> 数据默认留在本机 · 邮箱保持只读</p>
      </section>

      <section className="welcome-console" aria-label="CareerPilot 当前能力">
        <header><span>CAREERPILOT / READY</span><i>LOCAL</i></header>
        <div className="welcome-console-body">
          <p className="console-label">AVAILABLE WORKFLOWS</p>
          {capabilities.map(([number, title, detail]) => <article key={number}>
            <code>{number}</code><div><strong>{title}</strong><span>{detail}</span></div><b>READY</b>
          </article>)}
          <div className="console-status"><i /><span>等待你的下一步操作</span><time>127.0.0.1</time></div>
        </div>
      </section>
    </main>

    <footer className="welcome-footer"><span>CareerPilot</span><span>本地优先 · 人工确认 · 可随时导出</span></footer>
  </div>;
}
