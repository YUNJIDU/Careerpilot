# Job Application Tracker 开源参考与选型清单

> 2026-09-05 适用范围：本文保留原阶段设计；Excel 真源、永久删除、邮件字段增量、简历定义、全面面试准备、建议输出、Harness 与评测冲突项已由[当前规则](../CURRENT-POLICY.md)替代。首发限制仅适用于 Stage 0–4；长期愿景为候选，不自动进入近期范围。

更新时间：2026-09-05

## 1. 结论

目前没有一个公开仓库完整覆盖“邮箱识别 → 申请追踪 → Excel 同步 → JD/公司研究 → 分阶段笔试面试准备 → 个性化训练 → 多 Agent → 商业化部署”。

最稳妥的做法不是拼接多个完整产品，而是：

1. 借鉴 Job Tracker 的字段、页面和状态流。
2. 借鉴邮件项目的分类及去重逻辑。
3. 用 Python 自己维护统一数据模型和主流程。
4. 通过适配器调用抓取、模型和导出工具。
5. MVP 跑通后才引入 Agent 编排、长期记忆和自动填报。

> 许可证、维护状态和依赖安全会变化。正式复制代码前应再次检查仓库的 `LICENSE`、最近提交、Issue 和安全公告。

## 2. 完整产品与 Job Tracker 参考

| 项目 | 技术与能力 | 可借鉴内容 | 不建议直接照搬 |
|---|---|---|---|
| [viviannnli/job-tracker](https://github.com/viviannnli/job-tracker) | 视频中的原项目；画面显示 Gmail 只读、邮件分类、Application 列表、公司快照和面试准备 | 产品流程、页面字段、阶段触发 | 当前仓库非公开，不能作为可复用代码来源 |
| [fatehaliaamir2100/Job-Application-Tracker](https://github.com/fatehaliaamir2100/Job-Application-Tracker) | Python、FastAPI、Gmail API、Ollama，本地优先 | Python 后端组织、邮件到申请记录的流程、本地模型接入 | Gmail 适配需要替换为通用邮箱接口；先核验代码成熟度 |
| [Gsync/jobsync](https://github.com/Gsync/jobsync) | Next.js、Prisma、SQLite、AI 简历审查、岗位匹配、Tracker 和仪表盘 | 页面布局、字段、筛选、统计、简历与岗位关联方式 | 不继承其 TypeScript 业务层；只作为产品/UI 参考 |
| [jobtopbob/jobtopbob](https://github.com/jobtopbob/jobtopbob) | Go/Next.js、自托管、简历管理、AI 助手、Gmail 集成 | 完整产品的信息架构和用户流程 | 技术栈较重，不适合作为当前 Python MVP 基座 |
| [coolbrother/apply-potato](https://github.com/coolbrother/apply-potato) | Python、Gmail、Google Sheets、AI 提取、状态检测、职位抓取 | 邮件状态分类、去重、表格同步、职位筛选 | 来源和表格实现绑定 Google；只借鉴逻辑 |
| [shelialia/jobhunttrackingbot](https://github.com/shelialia/jobhunttrackingbot) | Python、SQLite、Gmail、LLM、提醒和漏斗图 | 轻量 Tracker、状态统计、提醒 | Telegram 不是当前入口 |
| [santifer/career-ops](https://github.com/career-ops-hq/career-ops) | 职位评估、简历定制、公司研究、面试准备、Tracker | “岗位研究报告”的内容结构、人工确认、故事库思路 | 面向 Claude Code 工作流，不宜直接作为 Web 后端 |
| [Pickle-Pixel/ApplyPilot](https://github.com/Pickle-Pixel/ApplyPilot) | 职位发现、JD 抓取、匹配、简历定制、自动投递 | 后期自动投递的阶段拆分、dry-run 和人工确认 | 自动投递风险高，不进入 MVP |
| [proficientlyjobs/proficiently-claude-skills](https://github.com/proficientlyjobs/proficiently-claude-skills) | 搜岗、简历定制、求职信、表单填报、按岗位保存文件 | 每个 Application 独立保存 JD、简历、求职信和投递记录 | 与特定 Agent CLI 绑定，适合作为后期流程参考 |
| [Dinesh-Satram/job_application_agent_SL](https://github.com/Dinesh-Satram/job_application_agent_SL) | Python、FastAPI、Streamlit、browser-use、MCP、自动填表 | 后期浏览器自动填报、Streamlit 调试界面 | LinkedIn 自动化、凭证和反爬风险较高 |

## 3. Python MVP 基础组件

| 需求 | 优先选择 | 备选 | 备注 |
|---|---|---|---|
| HTTP API | [FastAPI](https://github.com/fastapi/fastapi) | Flask | FastAPI 的类型验证和自动 API 文档更适合结构化 AI 输出 |
| 数据验证 | [Pydantic](https://github.com/pydantic/pydantic) | dataclasses | 邮件解析、LLM 输出和 API 边界统一使用同一模型 |
| ORM/持久化 | [SQLAlchemy](https://github.com/sqlalchemy/sqlalchemy) | SQLModel | MVP 用 SQLite，后续迁移 PostgreSQL |
| 数据库迁移 | [Alembic](https://github.com/sqlalchemy/alembic) | MVP 早期手工迁移 | 数据进入真实使用后立即启用 |
| Excel | [openpyxl](https://foss.heptapod.net/openpyxl/openpyxl) | pandas + XlsxWriter | Excel 是岗位字段事实源，数据库承载运行与证据 |
| 邮件协议 | Python `imaplib` + `email` 标准库 | [email-mcp](https://github.com/codefuturist/email-mcp) | 首发实现统一 MailAdapter 和 163 IMAP 只读适配器 |
| 本地 Web | 进入 Stage 4 时选型 | Streamlit / React / 其他 | 已确定本地 Web 是首发主要入口，但框架不在总体阶段提前锁死 |
| 定时任务 | APScheduler | Celery/RQ | MVP 单机定时轮询足够；多用户/高并发时再升级 |
| 测试 | pytest | unittest | 每个主流程保留一条端到端测试 |

## 4. 邮件接入与解析参考

### 推荐边界

定义统一的 `MailAdapter` 概念，但 MVP 只实现一个适配器。业务层只接收标准化邮件：

- `message_id`
- `account_id`
- `from_address`
- `subject`
- `sent_at`
- `plain_text`
- `html_text`
- `attachments`
- `source_folder`
- `raw_hash`

### 参考项目

- [codefuturist/email-mcp](https://github.com/codefuturist/email-mcp)：IMAP/SMTP、多账户、搜索、IMAP IDLE 和邮件分类参考。MVP 不必引入 MCP，可直接借鉴其协议边界。
- [IdeoaLabs/Open-Sable](https://github.com/IdeoaLabs/Open-Sable)：通用 IMAP/SMTP 和 Python 办公文件能力参考。
- [coolbrother/apply-potato](https://github.com/coolbrother/apply-potato)：确认信、OA、面试、Offer、拒信的状态映射参考。
- Python 标准库：优先用 `imaplib` 和 `email` 完成最小 IMAP 读取与 MIME 解析，避免为一个邮箱供应商增加重依赖。

### 必须自行补齐

- 幂等：`account_id + message_id` 唯一。
- 误判保护：不明确字段留空，所有提取值保存来源和证据；不得替用户作求职决策。
- 线程合并：同一公司、岗位、候选人和时间窗口的邮件合并。
- 原始证据：保留邮件哈希、主题、发件人和时间，不默认长期保存完整敏感正文。
- 值冲突：邮件新信息不得静默覆盖用户在 Excel 或 Web 中的手工值。

## 5. JD、公司与笔试面试情报

| 项目 | 适用场景 | 使用建议 |
|---|---|---|
| [unclecode/crawl4ai](https://github.com/unclecode/crawl4ai) | 把招聘页、公司技术博客和公开面经转为 LLM 友好的 Markdown | MVP 首选抓取器；限制域名、页数、深度和缓存 |
| [firecrawl/firecrawl](https://github.com/firecrawl/firecrawl) | 搜索、抓取、结构化抽取和 Webhook | 适合后续服务化；注意 AGPL/云服务边界 |
| [browser-use/browser-use](https://github.com/browser-use/browser-use) | 动态网页、登录态、复杂页面操作和表单填报 | 仅在普通 HTTP/抓取失败时使用；自动提交必须人工批准 |
| [browser-use/web-ui](https://github.com/browser-use/web-ui) | 浏览器 Agent 调试界面 | 后期自动填报 Demo 参考 |
| [career-ops](https://github.com/career-ops-hq/career-ops) | 公司研究、岗位匹配、面试故事库 | 借鉴报告模板和人工决策点 |

### 情报输出应携带

- 来源 URL、标题、抓取时间。
- 来源类型：官方招聘页、公司官网、技术博客、公开社区、题库。
- 可信度等级。
- 与当前岗位/JD 的关联理由。
- 推断与事实分开。
- 过期时间或重新抓取条件。

### 分阶段输出

- `APPLIED`：岗位摘要、公司摘要、技能差距、待办。
- `OA/WRITTEN_TEST`：笔试形式、常见考点、练习清单、限时模拟。
- `INTERVIEW`：面试轮次、技术/行为问题、STAR 素材、公司针对性问题。
- `OFFER`：Offer 对比项、谈薪准备、截止日期。
- `REJECTED`：证据化复盘，不凭空猜测拒绝原因。

## 6. 简历与个性化分析参考

| 项目 | 可借鉴内容 | 注意点 |
|---|---|---|
| [Gsync/jobsync](https://github.com/Gsync/jobsync) | 简历管理、AI Review、JD 匹配与 Tracker 联动 | UI/产品参考 |
| [jananthan30/Resume-Builder](https://github.com/jananthan30/Resume-Builder) | ATS/HR 双视角、JD 匹配、定制简历 | 核验许可证和输出质量 |
| [phoinixi/resuml](https://github.com/phoinixi/resuml) | Resume-as-code、ATS 匹配、MCP 接口 | 可作为后期简历渲染/工具接口参考 |
| [YomnaWaleed/job-recommendation-system-ai](https://github.com/YomnaWaleed/job-recommendation-system-ai) | Sentence Transformers、FAISS、Streamlit 的简历-JD 匹配 Demo | 数据集和简单相似度不能替代真实评估 |
| [KunjShah95/job-snipper](https://github.com/KunjShah95/job-snipper) | Python/Streamlit 的简历分析和面试准备 | 适合功能 Demo，不直接视为生产实现 |

模型层不要在规划阶段锁死。MVP 只要求：

- 支持结构化输出。
- 可替换模型供应商。
- 保存模型名、提示词版本和解析版本。
- 失败时能回退到人工编辑。

### 开源/开放权重模型候选

| 模型 | 适用任务 | 采用时机 |
|---|---|---|
| [Qwen3](https://github.com/QwenLM/Qwen3) | 中文/英文邮件抽取、摘要、题目生成和后期工具调用；官方开放权重采用 Apache 2.0 | 有本地部署或数据不出机需求时做评测候选 |
| [DeepSeek-V3](https://github.com/deepseek-ai/DeepSeek-V3) | 复杂摘要、分析和生成；提供开放权重及兼容 API | 作为云 API/自建推理候选，不能默认本机可轻量运行 |
| [BAAI/bge-m3](https://huggingface.co/BAAI/bge-m3) | 中英文/多语种 JD、面经和简历检索；支持长文档和多种检索方式 | Phase 3 出现实际检索规模后再加入 |
| [BAAI/bge-reranker-v2-m3](https://huggingface.co/BAAI/bge-reranker-v2-m3) | 对召回的岗位资料和题目来源重排 | 只有当简单关键词/全文检索质量不足时加入 |

模型必须用本项目的脱敏邮件、JD 和阶段路由样本实测。参数规模、中文能力或排行榜不能替代任务级准确率、延迟、显存和成本评估。

## 7. 后期 Agent、工具协议与持久化

这些组件不进入 MVP，只在主流程稳定后评估。

| 项目 | 能力 | 建议 |
|---|---|---|
| [pydantic/pydantic-ai](https://github.com/pydantic/pydantic-ai) | Python、类型安全、工具调用、MCP、图、人工审批、持久执行 | 与 FastAPI/Pydantic 栈一致，后期优先做小型 PoC |
| [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) | 有状态图、检查点、中断恢复、人工介入、多 Agent | 需要复杂状态机时评估 |
| [crewAIInc/crewAI](https://github.com/crewAIInc/crewAI) | Crew/Flow、角色协作、工具和记忆 | 适合演示角色协作，不应先于确定性流程 |
| [microsoft/autogen](https://github.com/microsoft/autogen) | 多 Agent、事件驱动、MCP | 当前已进入维护模式；新项目应关注其官方后继 Microsoft Agent Framework |
| [temporalio/sdk-python](https://github.com/temporalio/sdk-python) | 长任务、重试、持久工作流、故障恢复 | 真正出现长任务和多 Worker 后再引入 |
| [Model Context Protocol servers](https://github.com/modelcontextprotocol/servers) | 标准化工具加载 | 内部 Python 函数稳定后再包装 MCP，避免过早协议化 |

## 8. 后期记忆

先区分四种数据，不能都塞进“向量记忆”：

1. 业务事实：Application、邮件、阶段、JD，进入关系数据库。
2. 原始文档：简历、JD、报告，进入文件/对象存储。
3. 可检索知识：面经、公司研究、历史问答，可建立全文或向量索引。
4. 个性化记忆：用户偏好、掌握程度、常见错误，才考虑记忆框架。

参考：

- [mem0ai/mem0](https://github.com/mem0ai/mem0)：用户、会话和 Agent 多层长期记忆。
- [letta-ai/letta](https://github.com/letta-ai/letta)：有状态、可持续学习的 Agent。
- [getzep/graphiti](https://github.com/getzep/graphiti)：带来源和时间有效性的上下文图，适合岗位和技能关系随时间变化的场景。

MVP 不需要以上框架。关系数据库和可追溯事件表足够。

## 9. 后期安全、评测和可观测性

| 项目 | 用途 |
|---|---|
| [protectai/llm-guard](https://github.com/protectai/llm-guard) | Prompt Injection、敏感信息和不安全输出扫描 |
| [promptfoo/promptfoo](https://github.com/promptfoo/promptfoo) | 提示词评测、红队、安全回归测试 |
| [Arize-ai/phoenix](https://github.com/Arize-ai/phoenix) | OpenTelemetry Trace、数据集、实验和 LLM 评测 |
| [langfuse/langfuse](https://github.com/langfuse/langfuse) | 自托管 Trace、提示词、评测和成本分析 |

最低安全原则：

- 邮箱只读、最小权限。
- 密钥不进入数据库明文字段、日志、Prompt 或 Git。
- 外部网页、邮件和附件一律视为不可信输入。
- 抓取内容不能直接改变系统指令或调用高风险工具。
- 自动填报默认 dry-run；提交、发信、删除和覆盖状态需要人工确认。
- Excel 导出防止公式注入：以 `=`, `+`, `-`, `@` 开头的外部文本必须转义。

## 10. 推荐组合

### MVP

- Python 3.12+
- FastAPI + Pydantic
- SQLAlchemy + SQLite
- 本地 Web（具体框架在 Stage 4 选型）
- `imaplib` + `email`
- openpyxl
- 一个支持结构化输出的 LLM
- Crawl4AI（仅在进入岗位研究阶段时加入）
- pytest

### MVP 后

- PostgreSQL
- 面向普通用户的正式前端与托管形态（后续再决策）
- APScheduler → 任务队列
- Pydantic AI 或 LangGraph
- Browser Use（自动填报）
- Phoenix/Langfuse（可观测性）
- Mem0/Graphiti（确有跨任务个性化需求时）
- Temporal（确有长任务、断点恢复和多 Worker 时）

## 已确认的 career-ops 取用策略（2026-09-05）

当初规划没有锁定上游 commit/tag，只能比较本地已选范围与当前上游能力，不能把所有额外功能都称作规划之后新增。上游当前描述 A–H，CareerPilot 仍采用既有 A–G 与五维综合判断/1–5 分。

| 取用层级 | 内容 | 本项目处理 |
|---|---|---|
| 近期：B 增强 | JD 要求重要性、证据依据、先 JD 后简历的判断顺序 | 纳入 Stage 5 第一/二组；推断不得成为明确高要求，重要性不进入总分 |
| 近期：研究与面试 | 公司业务/文化/市场研究、准备计划、故事、练习反馈 | 纳入原 Stage 5，复用内容与流程，不新建相同产品 |
| 近期：模型对比 | 冻结案例、候选模型与参考输出比较 | 补充统一评测，不以参考模型一致替代正确性或 Excel 验收 |
| 后续材料候选 | H 申请回答、求职信、申请邮件 | Stage 7 后续可选，用户主动请求；不照搬 H 的 4.5 分条件 |
| 后续候选 | 谈薪/Offer、复盘与漏斗、独立格式检查 | 不加入近期验收，见长期候选 |
| 不整体搬入 | 扫描/发现、PDF 生成、插件、CLI 批处理和 Markdown Tracker | 不符合当前范围或会重复运行/数据体系 |

上游 golden-set 文档当前描述 10 个合成案例，主要检查候选模型与参考模型的一致性，岗位类型为门槛、分数为辅助；不是本项目的端到端质量保证。
正式移植步骤：固定上游提交 → 列出具体文件和依赖 → 区分内容规则/可独立工具/上游专属运行时 → 保留 MIT 许可与署名 → 适配当前数据边界 → 用本项目样本验收。未进行该步骤前，不声称已经直接集成或完整复制上游。

来源：[评估规则](https://github.com/career-ops-hq/career-ops/blob/main/modes/oferta.md)、[功能说明](https://github.com/career-ops-hq/career-ops/tree/main)、[评测说明](https://github.com/career-ops-hq/career-ops/tree/main/evals)、[许可证](https://github.com/career-ops-hq/career-ops/blob/main/LICENSE)。
