# Stage 6 受控 Agent 使用与恢复指南

Stage 6 为 CareerPilot 增加一个由用户手动发起、绑定单个岗位、预算受限的辅助 Agent。它复用 Stage 0–5 的确定性 Service，不替代证据分析、岗位管理或 Summary，也不替用户决定是否投递、接受 Offer 或修改求职结果。

## 1. 已实现范围

- 岗位级 Agent Run、工具调用、审批和预算审计。
- 三个只读工具：`application.read`、`stage5.read_context`、`summary.read_latest`。
- 一个写入候选：`application.append_note`，只能追加岗位备注，必须人工批准。
- 严格结构化模型动作、工具白名单、单岗位作用域和来源校验。
- 步骤、模型调用、工具调用、写入审批和活跃时间硬上限。
- 待审批暂停、刷新恢复、服务重启恢复、取消、超时和预算耗尽。
- 乐观锁、稳定幂等键和审批后再次校验，避免陈旧或重复写入。

本阶段不包含 Multi-Agent、长期记忆、任意插件、Shell/SQL/代码执行、主动运行、后台 Worker、Gmail/Outlook、通知、浏览器自动提交或 Stage 8 的多租户能力。

## 2. 启动与访问

按项目根目录的 Docker 或 Windows 开发方式启动前后端。默认地址：

- Web：`http://127.0.0.1:9999`
- API：`http://127.0.0.1:9998`

进入任意岗位详情，点击 **Agent 协助**，或打开：

```text
http://127.0.0.1:9999/#/applications/{application_id}/agent
```

填写任务，确认本 Run 的最小必要数据可以发送给已配置的模型，再启动。这个确认只对当前 Run 生效，不会成为永久授权。

## 3. 运行与审批

默认预算为：

| 项目 | 默认值 | 服务端上限 |
|---|---:|---:|
| Agent 步骤 | 8 | 12 |
| 模型调用 | 6 | 8 |
| 工具调用 | 8 | 12 |
| 写入审批候选 | 2 | 3 |
| 活跃运行时间 | 180 秒 | 300 秒 |

用户可以降低预算，但不能突破服务端上限。调用预算会在外部动作前持久化预扣，进程中断不会获得重复的免费重放。

只读工具在预算内自动执行。若模型提出追加备注，Run 会进入 `waiting_approval`，页面显示目标岗位、当前版本、完整追加文本、原因和来源：

- **批准**：服务端重新检查岗位版本、来源、文本、幂等键和工具范围，再通过 `ApplicationService` 追加一次备注。
- **拒绝**：业务数据保持不变，拒绝结果返回 Agent 生成最终说明。
- 页面刷新或服务重启：待审批记录仍存在，可继续批准或拒绝。
- 审批期间岗位被其他操作修改：审批过期并返回冲突，必须重新生成预览。

## 4. API

```text
POST /api/v1/applications/{application_id}/agent-runs
GET  /api/v1/applications/{application_id}/agent-runs
GET  /api/v1/agent-runs/{run_id}
POST /api/v1/agent-runs/{run_id}/approvals/{approval_id}
POST /api/v1/agent-runs/{run_id}/resume
POST /api/v1/agent-runs/{run_id}/cancel
```

创建 Run 必须提交 `data_leaving_confirmed: true`。`resume` 只恢复可恢复的中断 Run，不能绕过审批；`cancel` 不会执行待审批工具。

## 5. 数据、迁移与回滚

Alembic `0008_agent_runs` 新增：

- `agent_runs`
- `agent_tool_calls`
- `agent_approvals`

任务状态和检查点继续复用 `background_jobs` 与 `job_checkpoints`。检查点只保存 ID、预算、步骤和安全摘要，不保存 API Key、完整 Prompt、完整网页、邮件或简历。

升级前由既有流程保存 `data/careerpilot.db.pre-0008.bak`。迁移只向前执行，不清空 `data/`。若迁移失败，应先停止服务，保留失败数据库，再使用迁移前备份恢复；不要执行破坏性清库或手工降级。

## 6. 安全边界

- Run 永远绑定创建时的单个 `application_id`；模型不能切换岗位。
- 模型只能选择代码内置工具和严格参数，不能生成并执行任意函数、URL、Shell 或 SQL。
- 网页、邮件、JD、简历、用户文本和模型输出一律视为不可信数据。
- 最终事实必须引用本 Run 成功工具返回的 `source_id`；不能定位的内容只能列为未知项。
- 授权码、模型 Key、Tavily Key、Bearer Token 等 Secret 形态文本会在进入审计前被拒绝。
- Stage 6 唯一业务写入是追加备注，批准前不改变任何岗位业务字段。

## 7. 验证命令

Windows 隔离环境：

```powershell
E:\鸡哥项目\.careerpilot-py311\Scripts\python.exe -m pip check
E:\鸡哥项目\.careerpilot-py311\Scripts\python.exe -m pytest .\backend\tests -q
E:\鸡哥项目\.careerpilot-py311\Scripts\python.exe -m ruff check .\backend
```

前端：

```powershell
cd frontend
npm run check
npm run build
npm run e2e
```

## 8. 故障处理

| 状态或错误 | 含义 | 处理 |
|---|---|---|
| `waiting_approval` | 写工具等待人工决定 | 检查准确 diff 后批准或拒绝 |
| `agent.approval_expired` | 岗位版本已变化 | 重新发起任务，生成新预览 |
| `agent.budget_exhausted` | 某项硬预算已耗尽 | 缩小任务；必要时在服务端上限内增加预算后新建 Run |
| `agent.interrupted` | 进程在运行中中断 | 使用恢复按钮；待审批 Run 不需要恢复 |
| `agent.application_scope_violation` | 工具尝试访问其他岗位 | 保留审计记录并重新表述任务；不要扩大权限 |
| `agent.invalid_action` | 模型动作不符合结构契约 | 重试一次；持续出现时检查模型兼容性和日志中的安全错误码 |
| `agent.model_failed` | 模型端点、凭证或网络失败 | 在设置页检查模型配置，不把 Key 粘贴到任务输入 |

完整验收数据见 [Stage 6 评测与 Multi-Agent 决策](STAGE6_EVALUATION.md)。
