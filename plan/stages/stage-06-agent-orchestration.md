# P2 Stage 6：受控单 Agent 与编排评测详细设计

状态：2026-08-01 本地实现与验收已完成；P2-6 结论为继续单 Agent，不引入 Multi-Agent

设计日期：2026-08-01

## 1. 阶段定位

Stage 6 在 Stage 5 的 JD、公司研究、简历证据映射、缺口分析和人工复盘都能脱离 Agent 独立运行后，引入一个由用户手动发起的辅助 Agent。

首版 Agent 只负责：

1. 围绕一个明确的 Application 理解用户的资料整理请求。
2. 通过白名单工具读取该岗位的现有事实和 Stage 5 证据。
3. 生成带来源的结构化汇总、未知项和待核实问题。
4. 当用户明确要求把内容写入岗位备注时，先展示变更预览并暂停，只有人工批准后才调用现有 `ApplicationService` 写入。
5. 记录运行、工具调用、预算、检查点、审批和失败，页面刷新或进程重启后仍可审计。

Agent 是已有 Service 的编排入口，不是第二套业务实现。Stage 0–5 的按钮、API 和测试必须继续能够在没有 Agent 的情况下工作。

## 2. 本阶段完成目标

- 一个主辅助 Agent，限定在单个 Application 上下文内运行。
- 内置、版本化、白名单式工具注册，不加载任意插件。
- 只读工具可在预算内自动执行；所有业务写入必须人工批准。
- 模型调用次数、工具调用次数、步骤数和总运行时间均有硬上限。
- Agent Run、工具调用、人工审批和恢复检查点持久化。
- 模型输出、网页、JD、简历和工具返回全部按不可信输入处理。
- 固定离线评测与一条 Docker 页面真实验收，用数据决定是否需要 Multi-Agent。

## 3. 明确不做

- 不默认引入 Multi-Agent，也不预建专用 Agent 类。
- 不引入 Pydantic AI、LangGraph、CrewAI 或新的队列框架。
- 不实现长期记忆、向量数据库、RAG、跨岗位聊天或无限会话历史。
- 不实现主动运行、定时运行、后台 Worker、并行工具执行或 WebSocket 流式输出。
- 不实现 Gmail、Outlook、ICS、通知、浏览器表单预填、验证码或自动投递；这些属于 Stage 7。
- 不实现 PostgreSQL、对象存储、多租户、RBAC 或 SaaS 配额；这些属于 Stage 8。
- 不让 Agent 登录第三方网站、绕过反爬或付费墙。
- 不输出候选人总分、录用概率、岗位推荐、是否投递或是否接受 Offer 的决策。
- 不让 Agent 直接导入 ORM、创建数据库 Session 或执行任意 SQL。
- 不把 MCP 当作内部工具运行的前置条件；只有稳定工具确需跨进程复用时再包装。

## 4. 首版用户闭环

### 4.1 只读资料整理

1. 用户从岗位详情进入“Agent 协助”。
2. 输入请求，例如“整理这个岗位已有证据，列出已经确认和仍需核实的内容”。
3. 页面明确提示本次模型调用会让最小必要数据离开本机；用户勾选后启动。
4. Agent 读取当前 Application 和最新 Stage 5 证据。
5. 页面展示带 `source_id` 与定位信息的事实、未知项和待核实问题。

### 4.2 审批后写入

1. 用户请求“把待核实问题追加到岗位备注”。
2. Agent 只能提出 `application.append_note` 工具候选，不得直接执行。
3. 页面展示目标岗位、当前版本、将追加的完整文本、原因和引用来源。
4. 用户选择“批准”或“拒绝”。
5. 批准后，服务端重新校验 Application 版本和参数，再通过 `ApplicationService.apply_field_change()` 写入；拒绝后不修改业务数据。
6. Agent 使用审批结果生成最终说明。审批页面刷新后仍存在，重复点击不会重复写入。

这一条闭环同时验证工具注册、审批、幂等、审计和恢复，不为了演示 Agent 而复制 Stage 5 页面已有的生成按钮。

## 5. 最小架构

```text
React Agent 页面
      ↓
Stage 6 API
      ↓
AgentService.run_until_pause()
      ├── ModelClient.generate_structured()
      ├── ToolRegistry（白名单、Schema、风险等级）
      │     ├── ApplicationService
      │     ├── Stage5Repository / gap_analysis
      │     └── SummaryRepository
      ├── JobService（状态与唯一检查点）
      └── AgentRepository（Run、Tool Call、Approval 审计）
```

关键约束：

- Agent 循环只接收结构化动作，不执行模型生成的代码、Shell、SQL、URL 或任意函数名。
- `ToolRegistry` 只注册代码内置工具，工具名与参数使用严格 Pydantic Schema。
- 工具处理器只调用现有 Service/Repository；Agent 层不接触 ORM。
- Agent Run 始终绑定一个 `application_id`，工具参数不能切换到其他岗位。
- 先同步运行到“完成、等待审批或失败”。首版本地应用无需消息队列和流式传输。

## 6. 单 Agent 循环

模型每一步只能返回以下两类动作之一：

```json
{
  "action": "tool",
  "tool_name": "stage5.read_context",
  "arguments": {},
  "reason": "需要读取该岗位已经保存的证据"
}
```

```json
{
  "action": "final",
  "summary": "仅基于已读取资料的简短汇总",
  "facts": [
    {
      "statement": "事实陈述",
      "source_id": "本次工具返回的稳定来源 ID",
      "locator": "原文或记录定位"
    }
  ],
  "unknowns": ["当前材料无法确认的内容"],
  "next_questions": ["建议由用户核实的问题"]
}
```

执行顺序：

1. 读取 Run、预算和最近检查点。
2. 在调用模型前预扣一次模型调用预算。
3. 使用严格 Schema 校验模型动作；未知字段、未知工具或越权参数立即安全失败。
4. 只读工具在预扣工具预算后执行，结果裁剪并写入工具调用记录，再推进检查点。
5. 写工具只创建待审批记录并将 Run 置为 `waiting_approval`；本次请求在此返回。
6. 审批时重新校验参数、岗位范围、幂等键和 `expected_version`，然后调用业务 Service。
7. 工具结果或拒绝结果进入下一步，直到生成 `final` 或触发预算、超时、取消、失败。
8. `final.facts[*].source_id` 必须来自本次成功工具调用；无法定位的内容只能进入 `unknowns`。

## 7. Tool Registry v1

| 工具 | 风险 | 输入 | 输出 | 执行规则 |
|---|---|---|---|---|
| `application.read` | `read` | 无；使用 Run 绑定的岗位 | 公司、岗位、Tracker 字段、版本、来源引用 | 自动执行；只返回当前岗位 |
| `stage5.read_context` | `read` | 无；使用 Run 绑定的岗位 | 最新 JD、公司研究、证据映射、缺口、人工复盘的裁剪视图与稳定 ID | 自动执行；不返回完整简历、完整网页或 Secret |
| `summary.read_latest` | `read` | 无；使用 Run 绑定的岗位 | 最新 Summary 的结构化内容与来源 ID；不存在时返回明确空结果 | 自动执行 |
| `application.append_note` | `write_approval` | `text`、`expected_version`、`source_ids` | 更新后的岗位版本和 Provenance ID | 必须批准；只追加“备注”，不得覆盖其他字段 |

`application.append_note` 的服务包装器先读取当前备注，在批准页面展示准确 diff；批准后通过 `ApplicationService.apply_field_change()` 写入，`source="user"`，幂等键使用 `agent:{run_id}:{tool_call_id}`。空文本、超长文本、Secret 形态文本和不属于本 Run 的来源 ID 均拒绝。

Stage 5 的结构化、研究和证据映射继续由现有页面手动触发。本版本不把它们再次包装为 Agent 写工具；只有评测或真实使用证明跨步骤编排确有价值时再单独增加。

## 8. 数据与迁移

新增 Alembic `0008_agent_runs`，只增加三张表；检查点复用现有 `background_jobs` 与 `job_checkpoints`，不建立第二套任务表。

### 8.1 `agent_runs`

- `run_id`：UUID，同时外键关联 `background_jobs.job_id`。
- `application_id`：Run 锁定的岗位。
- `request_text`：用户本次请求，限制长度，不允许凭证。
- `model_name`、`prompt_version`、`processor_version`。
- `max_steps`、`steps_used`。
- `max_model_calls`、`model_calls_used`。
- `max_tool_calls`、`tool_calls_used`。
- `max_write_approvals`、`write_approvals_used`。
- `max_elapsed_seconds`。
- `elapsed_ms`：累计活跃运行时间；等待人工审批的时间不计入。
- `final_output`：通过 Schema 校验的最终结构化结果，可空。
- `created_at`、`finished_at`。

Run 的状态、当前步骤、错误码和更新时间继续以 `background_jobs` 为准。新增状态：

- `waiting_approval`
- `cancelled`
- `budget_exhausted`
- `timed_out`

已有 `JobService.recover_interrupted()` 只把 `pending/running` 标为中断失败，不触碰 `waiting_approval`，因此待审批记录可以跨重启保留。

### 8.2 `agent_tool_calls`

- `tool_call_id`、`run_id`、`sequence`。
- `tool_name`、`tool_version`、`risk_level`。
- `arguments`：校验后的参数；不得含 Secret 或原始大文本。
- `status`：`proposed / waiting_approval / rejected / running / succeeded / failed`。
- `reason`、`result_refs`、`result_summary_safe`、`error_code`。
- `idempotency_key`。
- `created_at`、`finished_at`。

唯一约束：`(run_id, sequence)` 和 `idempotency_key`。

### 8.3 `agent_approvals`

- `approval_id`、`tool_call_id`（一对一）。
- `status`：`pending / approved / rejected / expired`。
- `request_summary`：用户可见的准确变更预览。
- `application_version`：提出写入时的版本。
- `decision_note`。
- `requested_at`、`decided_at`。

本地版是单用户，因此本阶段不伪造 `user_id`、角色或 RBAC；Stage 8 引入账户后再迁移审批主体。

### 8.4 检查点内容

`job_checkpoints.payload` 只保存：

- `run_id`
- `next_sequence`
- 已成功工具调用的 ID 和稳定 `result_refs`
- `pending_tool_call_id`
- 当前预算计数
- 最近模型动作类型

不得保存 API Key、完整 Prompt、完整网页、完整邮件、完整简历或模型供应商原始响应。

### 8.5 迁移与回滚

- 执行 `0008` 前由现有升级机制创建 `data/careerpilot.db.pre-0008.bak`。
- 只执行 Alembic 前向迁移，不清库、不删除 `data/`、不自动降级。
- 迁移失败时停止服务并从 `pre-0008` 备份恢复。
- 旧版本程序会忽略新增表；在未产生必须保留的 Agent Run 时，可使用迁移前备份回到 Stage 5。

## 9. API 设计

### 9.1 创建与查询

```text
POST /api/v1/applications/{application_id}/agent-runs
GET  /api/v1/applications/{application_id}/agent-runs
GET  /api/v1/agent-runs/{run_id}
```

创建请求：

```json
{
  "request_text": "整理现有证据并列出待核实问题",
  "idempotency_key": "客户端生成的稳定键",
  "data_leaving_confirmed": true,
  "limits": {
    "max_steps": 8,
    "max_model_calls": 6,
    "max_tool_calls": 8,
    "max_write_approvals": 2,
    "max_elapsed_seconds": 180
  }
}
```

服务端还设置不可突破的上限；客户端只能降低预算，不能超过服务端上限。创建接口同步执行到完成、失败或等待审批后返回 Run、工具时间线、预算使用量、待审批项和最终结果。

### 9.2 审批、恢复与取消

```text
POST /api/v1/agent-runs/{run_id}/approvals/{approval_id}
POST /api/v1/agent-runs/{run_id}/resume
POST /api/v1/agent-runs/{run_id}/cancel
```

审批请求：

```json
{
  "decision": "approved",
  "decision_note": null
}
```

- 同一审批重复提交必须返回相同结果，不重复写业务数据。
- `rejected` 不执行工具，并把拒绝作为结构化结果交回 Agent 生成最终说明。
- Application 版本变化时审批标为 `expired`，返回 `409`，要求重新生成变更预览。
- `resume` 只用于可恢复的中断 Run；不能绕过待审批状态。
- `cancel` 永不执行待审批工具，且不可把已取消 Run 恢复为运行中。

## 10. 预算、超时与失败语义

默认预算：

- 最多 8 个 Agent 步骤。
- 最多 6 次模型调用。
- 最多 8 次工具调用。
- 最多 2 次写入审批候选。
- 单次 Run 墙钟时间最多 180 秒；用户等待审批的时间不计入运行时间。

本阶段以可准确执行的“调用次数 + 墙钟时间”作为预算。不承诺 token 或金额预算，因为当前 `ModelClient` 没有稳定返回供应商 usage；当 ModelGateway 能提供统一 usage 后再追加，不伪造成本数字。

规则：

- 预算在外部调用前持久化预扣，避免进程中断后重复免费重放。
- 触发任何上限后状态为 `budget_exhausted`，不再调用模型或工具，也不执行待审批写入。
- 模型 HTTP 超时、工具失败、Schema 失败、未知工具、越权参数使用稳定错误码和脱敏错误文本。
- 页面展示已完成步骤和恢复建议；开发日志与用户审计记录分离。

建议错误码：

```text
agent.invalid_action
agent.unknown_tool
agent.tool_arguments_invalid
agent.application_scope_violation
agent.approval_required
agent.approval_expired
agent.budget_exhausted
agent.timed_out
agent.interrupted
agent.model_failed
agent.tool_failed
```

## 11. 前端设计

新增岗位级路由：

```text
#/applications/{application_id}/agent
```

页面包含：

1. 任务输入框和几个纯文本示例，不做复杂模板系统。
2. 数据离开本机确认；未确认时启动按钮禁用。
3. 可折叠预算设置，默认值即服务端默认值。
4. Run 状态与预算使用量。
5. 工具时间线：工具名、风险、原因、状态和安全结果摘要。
6. 审批卡：准确 diff、来源、岗位版本、批准与拒绝按钮。
7. 最终结果：带来源事实、未知项和待核实问题。

页面刷新后通过 `GET /agent-runs/{run_id}` 恢复，不依赖前端内存。首版不实现聊天气泡、打字动画、SSE、WebSocket 或跨 Run 对话。

## 12. 安全与隐私

- 每个 Run 创建时必须 `data_leaving_confirmed=true`；同意只覆盖本 Run，不写成永久设置。
- 发送给模型的内容按工具按需裁剪，不默认发送完整简历、完整网页、完整邮件或全部岗位库。
- Secret 由服务端配置读取，不进入模型输入、工具参数、检查点、数据库审计、响应或日志。
- 用户请求、模型动作和工具结果中的“忽略规则”“调用某工具”等文本都只是数据，不能改变系统工具白名单。
- 工具名、参数、来源 ID、Application 归属和字段范围由本地代码重新校验。
- `application.append_note` 只能追加备注；不能修改阶段、公司、岗位、流程结果或删除数据。
- 所有写入要求待审批记录、Application 乐观锁和幂等键同时成立。
- Agent 最终事实必须引用本次工具结果；无来源内容只能标为未知，不得写成事实。
- 日志、错误和评测快照检查邮箱授权码、模型 Key、Tavily Key 和常见 Bearer 形态泄漏。

## 13. 工作包与顺序门禁

### P2-1：Run 数据与迁移

- 新增 `0008_agent_runs`、ORM 记录和 `AgentRepository`。
- 扩展 `JobService` 的暂停、取消和安全恢复状态。
- 验证迁移前备份、前向升级、重启持久化和重复迁移。

门禁：临时数据库迁移、完整性检查、幂等和恢复测试通过。

### P2-2：只读工具与单 Agent

- 实现严格动作 Schema、`ToolRegistry` 和三个只读工具。
- 实现有限步 `AgentService.run_until_pause()`。
- 增加创建/查询 API，不实现业务写入。

门禁：确定性 Service 脱离 Agent 的原测试仍通过；Agent 能在固定模型桩下生成带有效来源的最终结果。

### P2-3：人工审批写入

- 增加 `application.append_note`、审批 API、乐观锁、幂等和拒绝路径。
- 增加岗位级 Agent 页面与审批卡。

门禁：批准前业务表零变化；批准后只追加一次备注；拒绝、重复批准和版本冲突均不误写。

### P2-4：预算、超时与检查点

- 持久化预扣计数、硬上限、等待审批暂停、取消和中断恢复。
- 覆盖进程重启、模型超时、工具失败和预算耗尽。

门禁：所有运行均在预算内终止；重启不丢待审批项，不重复执行工具。

### P2-5：评测与真实页面验收

- 固定脱敏离线评测集、模型桩和 Agent E2E。
- Docker 中用一个现有或合成岗位完成只读汇总、拒绝写入、批准写入和刷新恢复。
- 真实模型验收单独由用户勾选数据离开确认后进行。

门禁：第 14 节指标、全量回归和安全扫描全部通过。

### P2-6：Multi-Agent 决策

- 汇总离线评测与真实运行的成功率、工具错误、调用数和时延。
- 形成一页决策记录：继续单 Agent，或提交新的 Multi-Agent 设计；不得在本工作包直接加入多个 Agent。

门禁：有可复现数据支持结论。默认结论是继续单 Agent。

## 14. 评测与完成门禁

固定评测至少覆盖：

- 读取岗位事实并正确引用。
- 读取 JD、研究、证据映射、缺口和人工复盘。
- 材料缺失时明确输出 `unknowns`。
- Prompt Injection 要求调用未知工具或跨岗位读取时被拒绝。
- 用户要求写备注时必须暂停审批。
- 审批拒绝、批准、重复批准和 Application 版本冲突。
- 模型 Schema 错误、超时、工具失败、预算耗尽和进程中断。
- Secret、完整简历和完整邮件不进入审计与错误响应。

Stage 6 完成指标：

- 未批准业务写入：`0`。
- 跨 Application 数据访问：`0`。
- 无有效 `source_id` 的最终事实：`0`。
- Secret 泄漏：`0`。
- 固定评测任务在预算内终止：`100%`。
- 等待审批跨重启恢复：`100%`。
- 重复审批或恢复导致的重复写入：`0`。
- 后端全量测试、Ruff、Windows 锁定依赖 `pip check` 通过。
- 前端 TypeScript、生产构建和浏览器 E2E 通过。
- Alembic 迁移/备份、Docker 健康/API、依赖审计、Secret 扫描和镜像漏洞扫描通过。

## 15. 何时才设计 Multi-Agent

完成 P2-5 前不设计 Multi-Agent。只有真实数据同时证明以下情况时才进入新的详细设计：

1. 单个任务稳定存在三个以上相互独立、可并行的专业分支；并且
2. 单 Agent 在增加合理预算后仍因上下文、路由或时延达不到 Stage 6 指标；并且
3. 确定性工作流或增加一个普通工具不能更简单地解决问题。

若单 Agent 达标，Stage 6 的正式结论就是“不引入 Multi-Agent”。原有 Mail、Research、Resume、OA、Interview、Review Agent 名称继续作为长期候选，不生成空壳类、Prompt 或 UI。

## 16. 阶段交付物

- `0008_agent_runs` 前向迁移与备份验证。
- Agent/Tool/Approval 数据契约和本地 API。
- 单 Agent、白名单工具、人工审批、预算、检查点与恢复。
- 岗位级 Agent 页面和浏览器 E2E。
- 固定评测报告与 Multi-Agent 决策记录。
- `docs/STAGE6_AGENT.md` 安装、使用、安全、故障和恢复说明。

## 17. 完成记录

2026-08-01 已按 P2-1 至 P2-6 顺序完成本地实现与门禁：

- Alembic `0008_agent_runs`、Agent Run、工具调用、审批与检查点均已落库，并验证迁移前备份和恢复路径。
- 后端全量测试 `75 passed`，Ruff、Windows/Docker `pip check`、前端检查和生产构建均通过。
- 浏览器 E2E `3 passed`，其中 Stage 6 覆盖数据离机确认、待审批、刷新恢复和批准结果。
- Docker 真实模型验收完成只读资料整理、Stage 5 证据读取、写入拒绝和批准；未批准写入、重复写入、越权访问、无来源事实和 Secret 泄漏均为 `0`。
- 依赖审计、源代码 Secret 扫描和镜像 HIGH/CRITICAL 漏洞扫描均通过。
- 实测任务仅需 1–2 个串行工具、2–3 次模型调用，未出现三个以上独立编排分支；增加 Multi-Agent 只会扩大权限面和恢复复杂度，因此当前不引入。

使用与恢复说明见 [`docs/STAGE6_AGENT.md`](../../docs/STAGE6_AGENT.md)，完整验收数据与 Multi-Agent 决策见 [`docs/STAGE6_EVALUATION.md`](../../docs/STAGE6_EVALUATION.md)。任何范围扩大到新框架、新外部集成、Multi-Agent、长期记忆或自动投递，都必须重新提交设计。
