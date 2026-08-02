import {
  ArrowRight,
  CheckCircle,
  EnvelopeSimple,
  FileText,
  ListChecks,
  MagnifyingGlass,
  ShieldCheck,
  UserCheck,
} from "@phosphor-icons/react";
import dataLayers from "./assets/careerpilot-data-layers.png";
import "./welcome.css";

const pipeline = [
  ["信号捕获", "邮件解析完成", "10:24:31"],
  ["证据归档", "JD 证据已关联", "10:25:02"],
  ["简历匹配", "版本 v3 已选用", "10:25:18"],
  ["申请追踪", "Stage 6 · Acceptance", "10:25:41"],
] as const;

const sources = [
  ["SRC-20260802-1741", "岗位官网", "已验证"],
  ["SRC-20260802-1742", "公司研究", "已验证"],
  ["SRC-20260802-1743", "招聘邮件", "已验证"],
] as const;

const capabilities = [
  [EnvelopeSimple, "邮件信号"],
  [FileText, "简历版本"],
  [MagnifyingGlass, "JD 证据"],
  [ListChecks, "申请阶段"],
  [UserCheck, "人工确认"],
] as const;

function scrollTo(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

export default function WelcomePage() {
  return <div className="welcome-page">
    <header className="welcome-topbar">
      <a className="welcome-brand" href="#/welcome" aria-label="CareerPilot 首页">
        <span className="welcome-logo">CP</span>
        <span><b>CareerPilot</b><small>职业领航员</small></span>
      </a>
      <nav aria-label="首页导航">
        <button type="button" className="active" onClick={() => scrollTo("welcome-product")}>产品</button>
        <button type="button" onClick={() => scrollTo("welcome-mechanism")}>机制</button>
        <button type="button" onClick={() => scrollTo("welcome-privacy")}>隐私</button>
      </nav>
      <span className="welcome-running"><i />本地运行</span>
    </header>

    <main id="welcome-product" className="welcome-hero">
      <section className="welcome-copy" aria-labelledby="welcome-title">
        <p className="welcome-kicker">LOCAL-FIRST CAREER OPERATING SYSTEM</p>
        <h1 id="welcome-title">求职不是信息堆积，<br />而是一套<span>可运行的<wbr />系统</span></h1>
        <p className="welcome-lead">CareerPilot 把邮件、简历、岗位证据和申请进度组织成清晰、可恢复、可追溯的工作流。</p>
        <div className="welcome-actions">
          <a className="welcome-primary" href="#/overview">进入主工作台 <ArrowRight size={20} weight="bold" /></a>
          <button type="button" className="welcome-secondary" onClick={() => scrollTo("welcome-mechanism")}>探索运行机制 <ArrowRight size={18} /></button>
        </div>
        <ul className="welcome-capabilities" aria-label="核心能力">
          {capabilities.map(([Icon, label]) => <li key={label}><Icon size={20} weight="regular" />{label}</li>)}
        </ul>
        <p id="welcome-privacy" className="welcome-privacy"><ShieldCheck size={21} weight="duotone" />数据默认留在本机 <b>· 自动化写入必须审批</b></p>
      </section>

      <section className="welcome-visual" aria-label="CareerPilot 数据处理机制预览">
        <img src={dataLayers} alt="由岗位证据、简历和申请信息组成的数据层" />
        <div className="welcome-pipeline">
          <p>APPLICATION PIPELINE</p>
          {pipeline.map(([title, detail, time], index) => <article key={title} style={{ animationDelay: `${index * 0.45}s` }}>
            <i />
            <strong>{title}</strong>
            <span>{detail}</span>
            <time>{time}</time>
          </article>)}
          <article className="approval-step">
            <i />
            <strong>人工确认</strong>
            <span>写入需本人批准</span>
            <time>待确认</time>
          </article>
        </div>
        <div className="welcome-sources">
          <p>SOURCE TRACE</p>
          {sources.map(([id, source, state]) => <div key={id}><code>{id}</code><span>{source}</span><b>{state}</b></div>)}
          <p className="terminal-label">TERMINAL FEED</p>
          <code className="terminal-feed">10:24:31&nbsp; MAIL&nbsp;&nbsp; Parsed 3 new messages<br />10:24:44&nbsp; JD&nbsp;&nbsp;&nbsp;&nbsp; Evidence linked<br />10:25:18&nbsp; RESUME Selected v3<br />10:25:41&nbsp; WRITE&nbsp; Pending approval</code>
        </div>
      </section>
    </main>

    <section id="welcome-mechanism" className="welcome-workspace" aria-labelledby="workspace-title">
      <header><div><p>本地工作台</p><h2 id="workspace-title">申请总览</h2><span>从最新变化开始，所有结论均可返回来源。</span></div><a href="#/overview">打开完整工作台 <ArrowRight size={18} /></a></header>
      <div className="workspace-body">
        <div className="workspace-nav" aria-hidden="true"><b>CP</b><span>总览</span><span>申请追踪</span><span>邮件同步</span><span>简历管理</span><span>任务</span></div>
        <div className="workspace-table">
          <div className="workspace-head"><span>公司 / 职位</span><span>阶段</span><span>来源</span><span>最近更新</span></div>
          <div><strong>宁德时代<br /><small>智能制造与数智化</small></strong><span>面试准备</span><span>邮件 · 岗位 JD</span><time>今天 10:25</time></div>
          <div><strong>北方华创<br /><small>Agent 开发工程师</small></strong><span>已投递</span><span>招聘官网</span><time>昨天 22:18</time></div>
          <div><strong>蔚来<br /><small>算法工程师</small></strong><span>测评进行中</span><span>邮件 · 简历 v3</span><time>昨天 18:05</time></div>
        </div>
        <div className="workspace-events"><h3>最近信号</h3><p><CheckCircle size={17} weight="fill" />HR 邮件已关联</p><p><CheckCircle size={17} weight="fill" />简历 v3 已选用</p><p><CheckCircle size={17} weight="fill" />JD 证据已归档</p></div>
      </div>
    </section>
  </div>;
}
