import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  api,
  ApplicationDetail,
  CompanyResearch,
  EvidenceMap,
  Gap,
  JDVersion,
  ResumeVersion,
  Review,
} from "./api";

function Notice({ kind = "info", children }: { kind?: "info" | "error" | "success"; children: React.ReactNode }) {
  return <div className={`notice ${kind}`} role={kind === "error" ? "alert" : "status"}>{children}</div>;
}

const STATUS_LABELS = {
  matched: "已匹配",
  partial: "部分匹配",
  missing: "未找到证据",
  unknown: "无法判断",
};

const CATEGORY_LABELS: Record<string, string> = {
  responsibility: "岗位职责", required: "必备条件", preferred: "加分条件",
  benefit: "待遇福利", process: "招聘流程", other: "其他",
};

function ReviewButtons({ applicationId, artifactType, artifactId, itemId, reviews, onSaved }: {
  applicationId: string;
  artifactType: "jd" | "research" | "evidence_map";
  artifactId: string;
  itemId: string;
  reviews: Review[];
  onSaved: () => Promise<void>;
}) {
  const [busy, setBusy] = useState(false);
  const latest = reviews.find((item) => item.artifact_id === artifactId && item.item_id === itemId);
  const save = async (decision: Review["decision"]) => {
    setBusy(true);
    try {
      await api.createReview(applicationId, {
        artifact_type: artifactType, artifact_id: artifactId, item_id: itemId, decision, note: null,
      });
      await onSaved();
    } finally { setBusy(false); }
  };
  return <div className="review-actions" aria-label="人工复盘">
    {latest && <span className="review-state">最近复盘：{latest.decision}</span>}
    <button className="button" disabled={busy} onClick={() => void save("confirmed")}>确认</button>
    <button className="button" disabled={busy} onClick={() => void save("needs_revision")}>需修正</button>
    <button className="button danger" disabled={busy} onClick={() => void save("rejected")}>拒绝</button>
  </div>;
}

export default function EvidencePage({ id }: { id: string }) {
  const [application, setApplication] = useState<ApplicationDetail | null>(null);
  const [jds, setJds] = useState<JDVersion[]>([]);
  const [research, setResearch] = useState<CompanyResearch[]>([]);
  const [maps, setMaps] = useState<EvidenceMap[]>([]);
  const [resumes, setResumes] = useState<ResumeVersion[]>([]);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [gaps, setGaps] = useState<Gap[]>([]);
  const [jdText, setJdText] = useState("");
  const [jdUrl, setJdUrl] = useState("");
  const [jdVersionId, setJdVersionId] = useState("");
  const [resumeVersionId, setResumeVersionId] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const load = async () => {
    const [nextApplication, nextJds, nextResearch, nextMaps, nextResumes, nextReviews] = await Promise.all([
      api.application(id), api.jdVersions(id), api.companyResearch(id), api.evidenceMaps(id),
      api.resumes(), api.reviews(id),
    ]);
    setApplication(nextApplication); setJds(nextJds); setResearch(nextResearch); setMaps(nextMaps);
    setResumes(nextResumes.filter((item) => item.application_ids.includes(id))); setReviews(nextReviews);
    if (!jdVersionId && nextJds[0]?.structure) setJdVersionId(nextJds[0].jd_version_id);
    if (!resumeVersionId) {
      const linked = nextResumes.find((item) => item.application_ids.includes(id));
      if (linked) setResumeVersionId(linked.version_id);
    }
    setGaps(nextMaps[0] ? (await api.gaps(nextMaps[0].map_id)).gaps : []);
  };
  useEffect(() => { void load().catch((value) => setError(String(value))); }, [id]);

  const run = async (name: string, action: () => Promise<void>, success: string) => {
    setBusy(name); setError(""); setMessage("");
    try {
      await action(); await load(); setMessage(success);
      if (["structure", "research", "map"].includes(name)) setConfirmed(false);
    }
    catch (value) { setError(String(value)); }
    finally { setBusy(""); }
  };
  const createJD = async (event: FormEvent) => {
    event.preventDefault();
    await run("create-jd", async () => {
      if (Boolean(jdText.trim()) === Boolean(jdUrl.trim())) throw new Error("请只填写 JD 正文或公开网址中的一种。");
      const saved = await api.createJD(id, jdText.trim() ? { raw_text: jdText.trim() } : { source_url: jdUrl.trim() });
      setJdVersionId(saved.jd_version_id); setJdText(""); setJdUrl("");
    }, "JD 新版本已保存；原文不会被后续分析覆盖。");
  };

  const latestJD = jds[0];
  const latestResearch = research[0];
  const latestMap = maps[0];
  const selectedJD = useMemo(() => jds.find((item) => item.jd_version_id === jdVersionId), [jds, jdVersionId]);
  if (!application) return error ? <Notice kind="error">{error}</Notice> : <p className="empty">正在读取证据工作台…</p>;

  return <>
    <header className="page-header"><div><a className="back" href={`#/applications/${id}`}>← 返回申请详情</a><p className="eyebrow">Stage 5 · Evidence Intelligence</p><h1>证据分析</h1><p>{application.company} / {application.role}；这里只整理证据，不评分、不预测录用结果。</p></div></header>
    {message && <Notice kind="success">{message}</Notice>}{error && <Notice kind="error">{error}</Notice>}

    <section className="panel"><div className="section-title"><div><h2>1. JD 版本与结构化</h2><p>粘贴原文或抓取一个公开网页；每条结构化结论必须附原文定位。</p></div></div>
      <form className="form-stack wide-form" onSubmit={(event) => void createJD(event)}><label>JD 正文<textarea value={jdText} maxLength={50000} onChange={(event) => setJdText(event.target.value)} placeholder="与下方网址二选一" /></label><label>公开 JD 网址<input type="url" value={jdUrl} onChange={(event) => setJdUrl(event.target.value)} placeholder="https://…（与正文二选一）" /></label><button className="button primary" disabled={busy === "create-jd"}>保存 JD 新版本</button></form>
      {latestJD && <div className="artifact-block"><div className="section-title"><div><h3>JD v{latestJD.version}</h3><p>{latestJD.source_type === "url" ? latestJD.source_title : "人工粘贴"} · SHA-256 {latestJD.content_hash.slice(0, 12)}…</p></div><button className="button primary" disabled={!confirmed || Boolean(busy)} onClick={() => void run("structure", async () => { await api.structureJD(latestJD.jd_version_id); }, "JD 结构化完成并通过原文引用校验。")}>结构化此版本</button></div>
        {latestJD.structure ? latestJD.structure.items.map((item) => <article className="evidence-card" key={item.item_id}><span className="badge">{CATEGORY_LABELS[item.category]}</span><h4>{item.statement}</h4><blockquote>“{item.evidence_quote}”</blockquote><small>{item.locator}</small><ReviewButtons applicationId={id} artifactType="jd" artifactId={latestJD.jd_version_id} itemId={item.item_id} reviews={reviews} onSaved={load} /></article>) : <p className="empty">该版本尚未结构化。</p>}
      </div>}
    </section>

    <section className="panel"><div className="section-title"><div><h2>2. 公司研究</h2><p>Tavily 搜索公开来源，模型只能生成可回溯到网页原文的事实。</p></div><button className="button primary" disabled={!confirmed || Boolean(busy)} onClick={() => void run("research", async () => { await api.generateCompanyResearch(id); }, "公司研究已生成，所有事实均通过来源引用校验。")}>生成公司研究</button></div>
      {latestResearch ? <div className="artifact-block"><p>研究版本 v{latestResearch.version} · {latestResearch.content.sources.length} 个公开来源</p>{latestResearch.content.claims.map((claim) => <article className="evidence-card" key={claim.claim_id}><span className="badge">{claim.topic}</span><h4>{claim.statement}</h4><blockquote>“{claim.evidence_quote}”</blockquote><a href={claim.source_url} target="_blank" rel="noreferrer">{claim.locator} · 查看来源</a><ReviewButtons applicationId={id} artifactType="research" artifactId={latestResearch.research_id} itemId={claim.claim_id} reviews={reviews} onSaved={load} /></article>)}</div> : <p className="empty">尚未生成公司研究。</p>}
    </section>

    <section className="panel"><div className="section-title"><div><h2>3. 简历—JD 证据映射</h2><p>只使用已关联岗位的具体简历版本；状态固定为 matched / partial / missing / unknown。</p></div></div>
      <div className="field-grid"><label>已结构化 JD<select value={jdVersionId} onChange={(event) => setJdVersionId(event.target.value)}><option value="">请选择</option>{jds.filter((item) => item.structure).map((item) => <option key={item.jd_version_id} value={item.jd_version_id}>JD v{item.version}</option>)}</select></label><label>已关联简历版本<select value={resumeVersionId} onChange={(event) => setResumeVersionId(event.target.value)}><option value="">请选择</option>{resumes.map((item) => <option key={item.version_id} value={item.version_id}>{item.label} v{item.version}</option>)}</select></label></div>
      {!resumes.length && <Notice>该岗位尚未关联简历，请先到“简历管理”上传并关联一个 PDF、DOCX 或 TXT 版本。</Notice>}
      <button className="button primary stage5-action" disabled={!confirmed || !selectedJD?.structure || !resumeVersionId || Boolean(busy)} onClick={() => void run("map", async () => { await api.generateEvidenceMap(id, jdVersionId, resumeVersionId); }, "证据映射与缺口分析已完成。")}>生成证据映射</button>
      {latestMap ? <div className="artifact-block">{latestMap.content.mappings.map((mapping) => {
        const jdItem = jds.find((item) => item.jd_version_id === latestMap.jd_version_id)?.structure?.items.find((item) => item.item_id === mapping.jd_item_id);
        return <article className={`evidence-card map-${mapping.status}`} key={mapping.jd_item_id}><span className={`status ${mapping.status}`}>{STATUS_LABELS[mapping.status]}</span><h4>{jdItem?.statement ?? mapping.jd_item_id}</h4><p>{mapping.rationale}</p>{mapping.resume_evidence.map((evidence, index) => <blockquote key={index}>“{evidence.quote}”<small>{evidence.locator}</small></blockquote>)}<ReviewButtons applicationId={id} artifactType="evidence_map" artifactId={latestMap.map_id} itemId={mapping.jd_item_id} reviews={reviews} onSaved={load} /></article>;
      })}</div> : <p className="empty">尚未生成证据映射。</p>}
    </section>

    <section className="panel"><h2>4. 缺口分析与人工复盘</h2><p>缺口由映射状态确定性生成，不再次调用模型。“未找到证据”不等于你没有相关能力。</p>{gaps.length ? gaps.map((gap) => <article className="gap-card" key={gap.jd_item_id}><span className={`status ${gap.status}`}>{STATUS_LABELS[gap.status]}</span><h4>{gap.statement}</h4><p>{gap.finding}</p><strong>{gap.review_question}</strong></article>) : <p className="empty">当前没有待复盘缺口，或尚未生成映射。</p>}</section>
    <section className="data-warning"><strong>数据离开本机确认</strong><p>勾选后，JD、公开网页正文或所选简历正文会发送给设置中配置的模型服务。API Key 不会放入提示词；网页与文件内容一律按不可信证据处理。</p><label className="checkbox"><input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} />我了解并确认本页的下一次模型调用</label></section>
  </>;
}
