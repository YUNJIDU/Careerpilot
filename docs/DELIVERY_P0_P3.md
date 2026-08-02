# CareerPilot P0–P3 本地交付与 GitHub 工程说明

| 项目 | 内容 |
|---|---|
| 文档状态 | 本地发布候选，未推送、未打标签 |
| 交付日期 | 2026-08-02 |
| 上游基线 | `010ca92`（`origin/main`，Recognize resume rejection emails） |
| 当前开发分支 | `stage-4c/release-closure` |
| 完成范围 | P0 Stage 4C、P0.5、P1 Stage 5、P2 Stage 6、P3 Stage 7、统一工作台 UI |
| 未完成范围 | P4 Stage 8 产品化、真实 Gmail/Outlook 供应商账号验收 |

本文档是相对原 GitHub 仓库基线的总交付说明。阶段文档保留每个功能的详细契约；本文统一回答“增加了什么、怎样安装、怎样使用、数据去哪里、怎样测试、怎样评审和发布”。

## 1. 产品定位与工程原则

CareerPilot 是本地优先的求职信息操作系统，不是自动投递机器人或招聘决策系统。它把邮件、Tracker、简历、JD、公开来源、证据、申请阶段和人工审批组织为可恢复、可追溯的工作流。

当前版本遵循以下硬边界：

- 用户始终负责阅读原始材料并作出投递、面试和 Offer 决策。
- 邮箱只读；网页和模型输出不被当作可信指令。
- 用户在 Web/Excel 中的明确修改优先，不被后台同步静默覆盖。
- 外部模型调用和业务写入必须有清楚的当次确认或审批。
- 不计算候选人总分、排名、录用概率或人格判断。
- 不登录招聘网站、不绕过验证码/反爬/付费墙、不自动提交申请。
- Secret 不进入 SQLite、Excel、Markdown、前端存储、日志、Git 或 Docker 镜像。

## 2. 相对原仓库新增和改进

### 2.1 P0 Stage 4C：发布闭环

- 新增多阶段 `Dockerfile`：构建 React、安装锁定 Python 依赖、以 UID 10001 非 root 用户运行，提供健康检查和 `/app/data` 持久卷。
- 新增 Windows/Linux 锁定依赖，分离 runtime、dev 和 security 依赖集合。
- GitHub Actions 同时执行 Windows/Linux 后端测试、Ruff、TypeScript、生产构建、Windows Playwright E2E、Python/npm 审计、许可证报告、Gitleaks、Docker 构建、Trivy 和服务冒烟。
- API 启动时执行 Alembic 前向迁移并在每个结构版本前创建 SQLite 备份；容器替换不改变宿主机 `data/`。
- 修复 Windows 路径、配置加载、任务崩溃恢复和真实模型兼容性问题。

### 2.2 P0.5：MVP 承诺补齐

- 将邮件接入统一为唯一 `MailAdapter v1`，只加载代码内置适配器，不开放任意插件。
- 从单个 163 邮箱扩展为多个独立邮箱账户，分别测试、启停、同步和保存命名凭证。
- Web/API 支持上传原始 `.eml`；内容按 SHA-256 保存，并复用邮件解析、去重、Application Service、Job/Checkpoint 和 Tracker 同步链路。
- 附件默认只保存元数据，用户逐个批准后才读取内容。白名单为 PDF、DOCX、TXT、PNG、JPEG。
- 支持多份 PDF/DOCX/TXT 简历的内容寻址、版本和岗位关联；匹配分析留给 Stage 5。
- 新增文件安全验证：大小、扩展名、MIME、文件签名、路径穿越、恶意名称、DOCX 宏、压缩结构和解压上限。

数据迁移：

- `0003`：多邮箱账户；
- `0004`：附件、简历版本、岗位—简历关联。

### 2.3 P1 Stage 5：证据智能

- 保存不可变 JD 版本，可从人工正文或受 SSRF 防护的公开 URL 获取，并生成结构化职责、必备、加分、待遇、流程和其他条目。
- 公司研究保存公开页面 URL、抓取时间、逐条事实和原文引文；无法确认的内容显式标记未知。
- Resume–JD 映射只读取与当前岗位关联的具体简历版本；状态固定为 `matched / partial / missing / unknown`。
- `matched/partial` 必须引用简历原文，`missing` 不得伪造简历证据，每个 JD 条目恰好出现一次。
- 缺口分析由映射确定性生成；人工复盘以追加记录保存，不覆盖模型版本。
- JD、简历、网页和模型输出中的 Prompt Injection 都只作为不可信文本处理。

数据迁移：

- `0005`：JD 版本；
- `0006`：公司研究版本；
- `0007`：证据映射版本和人工复盘。

### 2.4 P2 Stage 6：受控单 Agent

- 增加绑定单个 Application 的手动 Agent Run，复用既有 ModelClient 和确定性 Service。
- 内置 Tool Registry v1：`application.read`、`stage5.read_context`、`summary.read_latest` 和 `application.append_note`。
- Agent 只能返回严格结构化动作，不能生成并执行任意 Python、Shell、SQL、URL 或插件。
- 只读工具在预算内自动执行；唯一写工具只能追加备注，并在准确 diff、来源和目标版本展示后暂停等待批准。
- 步骤、模型调用、工具调用、写审批和活跃时间都有服务端硬上限。
- Run、工具调用、审批、检查点和幂等键持久化，页面刷新和进程重启后可恢复；陈旧版本和重复审批不会产生重复写入。
- 真实模型评测证明当前任务只需要 1–2 个串行工具，因此明确不引入 Multi-Agent。

数据迁移：`0008` 新增 Agent Run、工具调用和审批审计表。

### 2.5 P3 Stage 7：外部集成

- Gmail 使用 Gmail API，Outlook 使用 Microsoft Graph；都通过 Authorization Code + PKCE 和最小只读 scope 接入 `MailAdapter v1`。
- OAuth state 10 分钟失效且只能使用一次；访问/刷新令牌进入 SecretStore，不进入数据库或 API 响应。
- 增加本地提醒、未来三天幂等通知扫描、浏览器通知授权和 RFC 5545 ICS 导出。
- 增加 Manifest V3 浏览器扩展，只在用户当前活动 HTTPS 标签页映射姓名、邮箱、电话、地点、个人网站和 LinkedIn。
- 扩展显示当前值与目标值的差异，用户确认后才填写；检测 CAPTCHA 立即停止，不读取密码/文件，不调用 `submit()`、`requestSubmit()` 或点击提交按钮。

数据迁移：`0009` 新增 OAuth 连接、提醒、通知和预填会话表。

### 2.6 UI 与可用性

- 新增产品欢迎页，说明邮件信号、简历版本、JD 证据、申请阶段和人工审批等核心能力。
- 统一工作台顶部栏、侧边导航、设计令牌、卡片、表格、表单、状态和焦点样式。
- 新增证据分析、Agent 协助和外部集成页面，并在岗位详情中保持相同信息层级。
- 桌面超宽屏不再缩成内容岛；移动端提供平衡标题换行、可触控导航和无页面级横向溢出布局。
- 正式发布只包含产品所需的 `frontend/src/assets/careerpilot-data-layers.png`，不包含本机设计对比截图和绝对路径 QA 文件。

## 3. 当前架构

```text
React/Vite Web (9999 dev；发布镜像由 API 提供)
        ↓ /api/v1
FastAPI
        ├── ApplicationService（唯一业务写入入口）
        ├── Excel / Mail / Summary / Stage 5 Services
        ├── Stage 6 AgentService → 内置 Tool Registry → 既有 Service
        ├── Stage 7 OAuth / Reminder / Prefill Services
        ├── Job + Checkpoint + Idempotency
        └── SQLAlchemy + Alembic → SQLite

外部可选依赖：163 IMAP、Gmail API、Microsoft Graph、Tavily、
              OpenAI-compatible 模型、公开 HTTP(S) 页面、用户日历
```

关键目录：

| 路径 | 作用 |
|---|---|
| `backend/src/careerpilot/` | API、Service、Repository、适配器和安全边界 |
| `backend/migrations/` | `0001`–`0009` 前向迁移 |
| `backend/requirements/` | Windows/Linux 锁定依赖 |
| `backend/tests/` | 单元、集成、迁移、安全和恢复测试 |
| `frontend/src/` | React 工作台和阶段页面 |
| `frontend/e2e/` | Playwright 用户闭环 |
| `browser-extension/` | 受控表单预填扩展 |
| `docs/` | 使用、验收、隐私和发布文档 |
| `plan/` | 阶段范围、决策和后续路线 |
| `data/` | 运行数据；除 `.gitkeep` 外全部忽略 |

## 4. 安装与启动

### 4.1 Windows 原生开发

前置条件：Python 3.11、Node.js 22、npm、Git。所有命令从仓库根目录执行：

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes --only-binary=:all: -r .\backend\requirements\windows-dev.lock
.\.venv\Scripts\python.exe -m pip install --no-deps --no-build-isolation -e .\backend
cd frontend
npm.cmd ci
cd ..
```

启动后端：

```powershell
.\.venv\Scripts\python.exe -m uvicorn careerpilot.api:create_app --factory --app-dir .\backend\src --host 127.0.0.1 --port 9998
```

在另一个终端启动前端：

```powershell
cd frontend
npm.cmd run dev
```

- Web：`http://127.0.0.1:9999`
- API 文档：`http://127.0.0.1:9998/docs`
- 健康检查：`http://127.0.0.1:9998/api/v1/health`

不要在 `frontend/` 中创建 Python 虚拟环境；如果出现 `requirements.txt not found`，先回到仓库根目录。

### 4.2 Docker 本地发布

```powershell
docker build --tag careerpilot:local .
New-Item -ItemType Directory -Force .\data
$careerData = (Resolve-Path .\data).Path
docker run --detach --name careerpilot `
  --publish 127.0.0.1:9998:9998 `
  --publish 127.0.0.1:9999:9998 `
  --mount "type=bind,source=$careerData,target=/app/data" `
  --env CAREERPILOT_PUBLIC_API_ORIGIN=http://127.0.0.1:9998 `
  careerpilot:local
```

发布镜像把前端和 API 放在同一容器中。宿主机 `data/` 是唯一持久数据卷；镜像升级时不要换成空目录。容器内 SecretStore 为只读，Secret 应通过只读文件挂载和 `*_FILE` 环境变量注入，详见 [Stage 4C 发布指南](STAGE4C_RELEASE.md)。

检查：

```powershell
docker ps --filter "name=careerpilot"
docker inspect --format "{{json .State.Health}}" careerpilot
Invoke-RestMethod http://127.0.0.1:9998/api/v1/health
```

## 5. 功能使用指南

### 5.1 基本 Tracker 和 Excel

1. 在“设置”保存非敏感配置；Secret 输入写入系统凭证库且之后只显示保存状态。
2. 在“申请追踪”新增公司和职位；每次变更保存来源、版本和时间线。
3. 在“Excel 同步”导出 `data/tracker.xlsx`；人工编辑后导入，冲突时保留明确的人工优先级。
4. 在“任务”查看后台任务、失败代码和检查点；可恢复失败只重试未完成步骤。

### 5.2 邮箱、本地样本和附件

- 163 授权码建议使用命令写入 Credential Manager，避免进入 shell 历史：

```powershell
.\.venv\Scripts\python.exe -m careerpilot.secrets personal your-address@163.com
```

- 在“邮件同步”添加/测试账户后手动同步；系统不会定时读取邮箱。
- 本地 `.eml` 通过页面上传，适合离线验收，不需要先把邮件发送到真实邮箱。
- 附件先显示元数据。确认来源、类型、大小和岗位后再逐个批准下载；不要批准不认识或不需要的附件。
- 在“简历管理”保存版本并把具体版本关联到岗位；后续证据映射不会自动猜测简历。

### 5.3 Summary 与 Stage 5 证据

1. 在设置中配置 Tavily 和 OpenAI-compatible 模型端点。
2. 在岗位详情手动确认数据离开本机后生成 Summary。
3. 在“证据分析”保存 JD，生成结构化版本和公司研究，再选择已关联简历生成证据映射。
4. 检查每条引文和 locator；`missing` 表示当前简历没找到证据，不等于用户没有能力。
5. 查看确定性缺口并逐项人工复盘；不要把模型结果当作投递决策。

### 5.4 Stage 6 Agent

1. 从岗位详情进入“Agent 协助”，用一个明确、只涉及当前岗位的任务开始 Run。
2. 勾选本次数据离开设备确认；模型只能选择内置工具。
3. 只读结果必须带本 Run 工具返回的 `source_id`；无法定位的内容进入未知项。
4. 写备注时核对目标岗位、旧值、追加文本、来源和版本，然后批准或拒绝。
5. 页面刷新或服务重启后继续处理待审批 Run；不要通过数据库手工修改审批状态。

### 5.5 Gmail/Outlook、提醒与 ICS

- 原生 Windows：在“设置”写入 OAuth Client ID/可选 Client Secret，再到“外部集成”授权。
- 回调地址：

```text
Gmail:   http://127.0.0.1:9998/api/v1/oauth/gmail/callback
Outlook: http://127.0.0.1:9998/api/v1/oauth/outlook/callback
```

- OAuth 应用必须使用测试账户和最小只读 scope；不要申请发送、删除或修改邮件权限。
- 提醒保存在本地 SQLite。页面显式扫描会生成未来三天通知；没有常驻 Worker。
- `GET /api/v1/reminders.ics` 导出 ICS，用户自行导入日历。导入后的副本由日历服务管理。

### 5.6 浏览器安全预填

1. 在 Chrome/Edge 扩展管理页启用开发者模式，选择“加载已解压的扩展程序”，指向 `browser-extension/`。
2. 在 CareerPilot“外部集成”创建 HTTPS 目标的预填会话。
3. 打开完全相同 origin 的申请页面，在扩展中输入会话 ID。
4. 逐项核对当前值和目标值，再确认填入。
5. 自己处理登录、验证码、最终检查和提交；扩展不会替代这些动作。

## 6. 数据、迁移、备份和恢复

`data/` 可能包含：

- `careerpilot.db` 和逐版本 `careerpilot.db.pre-<revision>.bak`；
- `tracker.xlsx`、`settings.json`；
- `mail-samples/`、`attachments/`、`resumes/`、`markdown/`；
- 本地验收或任务日志子目录。

一致备份步骤：

1. 停止产生写入的 API/容器。
2. 复制整个 `data/` 到受访问控制的带日期位置。
3. 重启并确认健康、Alembic revision、SQLite `integrity_check` 和关键记录。

迁移只向前执行。失败时停止服务、保留失败现场、从对应 `.pre-<revision>.bak` 恢复，再修复迁移；不要清空 `data/`、手改 `alembic_version` 或自动降级。

注意：本地 Playwright 配置允许复用已经运行的 `9998/9999` 服务，因此 E2E 可能在当前 `data/` 创建合成申请、提醒和预填会话。需要完全隔离时先停止现有服务，让 Playwright 使用 `data/e2e`，或显式启动指向临时数据目录的测试服务。

## 7. 安全与隐私

### 7.1 信任边界

| 边界 | 控制 |
|---|---|
| 文件上传 | 白名单、大小、MIME/签名、路径、宏和压缩限制；内容哈希命名 |
| 邮箱 | 只读协议/API；按账户命名 Secret；附件二次批准 |
| 网页 | 仅公开 HTTP(S)、SSRF/重定向/大小约束；正文不作为指令 |
| 模型 | 明确数据离开确认；严格结构化输出；来源验证；Secret 拒绝 |
| Agent | 单岗位范围、内置工具、硬预算、写审批、幂等和审计 |
| OAuth | PKCE、一次性 state、只读 scope、令牌进入 SecretStore |
| 浏览器扩展 | `activeTab`、字段白名单、diff、CAPTCHA 停止、禁止提交 |
| Git/CI | 真实数据忽略、Gitleaks、依赖审计、镜像扫描、只读 Actions 权限 |

### 7.2 第三方数据流

- Tavily 接收公司/岗位搜索查询。
- 用户配置的模型端点只在当次确认后接收任务所需内容。
- 163/Gmail/Microsoft 在用户手动同步时处理邮件请求。
- 公开网站接收普通页面请求；不要用项目绕过站点控制。
- ICS 只有用户导出并导入后才进入日历提供商。

详细说明见 [PRIVACY.md](../PRIVACY.md) 和 [SECURITY.md](../SECURITY.md)。使用前应确认第三方服务商的数据保留、训练、地域和合规政策。

## 8. API 和兼容性

所有业务 API 使用 `/api/v1`。主要资源组：

- Applications、Jobs、Excel、Settings、Summary；
- Mail Accounts、Mail Samples、Attachments、Resumes；
- JD Versions、Company Research、Evidence Maps、Reviews；
- Agent Runs、Approvals、Resume/Cancel；
- OAuth Connections、Reminders、Notifications、Prefill Sessions。

精确请求/响应 Schema 以运行时 `http://127.0.0.1:9998/docs` 和后端 Pydantic 模型为准。扩展 API 时必须保持：稳定错误代码、请求验证、幂等键、来源字段、乐观锁、Job/Checkpoint 和 Application Service 写入边界。

## 9. 质量门禁与已测结果

2026-08-02 本地交付验收：

| 门禁 | 结果 |
|---|---|
| 后端全量测试 | `81 passed` |
| Ruff | 通过 |
| 前端 TypeScript / production build | 通过 |
| Playwright 浏览器 E2E | `4 passed` |
| Windows/Linux `pip check` | 无损坏依赖 |
| Python `pip-audit` | 无已知漏洞 |
| npm audit | `0 vulnerabilities` |
| Gitleaks | 未发现 Secret |
| Trivy | CRITICAL `0`；有修复版本的 HIGH `0` |
| Docker | 健康检查、迁移、API 和 Web 冒烟通过 |
| SQLite | Alembic `0009`，`integrity_check=ok` |

标准本地命令：

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest .\backend\tests -q
.\.venv\Scripts\python.exe -m ruff check .\backend
cd frontend
npm.cmd run check
npm.cmd run build
npm.cmd run e2e
npm.cmd audit --audit-level=high
```

## 10. GitHub 工作流

### 10.1 分支和提交

- `main` 保持可运行；功能使用 `feature/*`，修复使用 `fix/*`，安全修复使用 `security/*`，文档使用 `docs/*`。
- 每个提交表达一个可回滚结果；不得把真实 `data/`、Secret、本机路径 QA、大型生成文件或测试报告混入提交。
- 依赖变更必须同时更新对应 lock、许可证清单、Docker 和 CI；数据库变更必须带迁移、备份和测试。

### 10.2 Pull Request

1. 推送功能分支并创建 Draft PR。
2. 使用 `.github/pull_request_template.md` 写清目标、数据/API、迁移、测试、安全/隐私、回滚和文档。
3. CI 全绿后转 Ready for review。
4. 评审重点：业务边界是否绕过、真实数据是否误提交、权限是否扩大、迁移是否可恢复、外部调用是否最小化、测试是否覆盖失败路径。
5. 合并后更新 Changelog；发布时再创建语义化标签和 GitHub Release，不从个人工作树直接发布。

### 10.3 CI 作业

| 作业 | 目的 |
|---|---|
| `test` | Windows/Linux 后端、Ruff、前端检查和构建 |
| `browser-e2e` | Windows Chromium 用户闭环 |
| `security` | Python/npm 依赖、许可证和 Git 历史 Secret |
| `docker-smoke` | 发布镜像构建、Trivy、健康、API/Web 冒烟 |

工作流只授予 `contents: read`。Actions 和扫描镜像使用固定提交或镜像 digest，降低供应链漂移。

### 10.4 发布与回滚

发布前：

1. 从干净 checkout 按锁文件安装；
2. 完成 CI 和手工验收；
3. 停止写入并备份 `data/`；
4. 构建不可变镜像标签并记录 digest；
5. 更新 `CHANGELOG.md`、版本和 Release Notes；
6. 部署新镜像但继续挂载同一受保护数据目录。

回滚时停止新容器并重新启动保留的旧镜像；如果新版本已经执行数据库迁移，先根据迁移说明判断旧代码是否兼容。需要恢复数据库时使用迁移前备份，并在隔离环境验证，不直接覆盖唯一备份。

## 11. 已知限制与下一阶段

- 当前 API 没有账户认证、RBAC 或租户上下文，只能绑定本机回环地址使用。
- SQLite 和同步 Job 适合单用户本地负载，没有独立 Worker、并发队列或对象存储。
- Docker SecretStore 只读；交互式 OAuth 持久授权更适合原生 Windows，容器需启动时注入配置/令牌。
- Gmail/Outlook 的 OAuth/HTTP 模拟集成测试通过，但没有使用开发者自有 Cloud/Entra 应用完成真实账号最终验收。
- 提醒依赖页面扫描或导出的日历，没有后台常驻调度器。
- 浏览器扩展只预填白名单字段，不兼容所有招聘网站，且永不自动提交。
- 没有完整的账户数据导出/删除、跨租户隔离、备份服务等级或 SaaS 合规声明。

P4 Stage 8 只有在单独设计、迁移和安全评审后才能引入 PostgreSQL、Worker、对象存储、认证、租户隔离、备份恢复、导出删除和合规能力。当前代码与文档不得把这些规划描述为已交付。

## 12. 交付清单

- [x] P0–P3 源码、前端、浏览器扩展、迁移、锁定依赖和测试进入 Git 交付范围。
- [x] `README`、阶段指南、交付说明、Changelog、贡献、安全和隐私文档互相链接。
- [x] GitHub PR/Issue 模板与 CI 工作流齐备。
- [x] `data/`、Secret、构建输出、Playwright 报告和本机 UI QA 文件被排除。
- [x] 后端、前端、E2E、依赖、安全和 Docker 门禁有可复现命令与结果。
- [ ] 推送、创建 PR、远端 Actions 和发布标签：本次本地交付不执行。
