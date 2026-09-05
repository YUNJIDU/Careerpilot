# Stage、服务与接口分布标准

更新时间：2026-09-05

## 1. 首发开发边界

```text
本地 Web + Excel Tracker
          ↓
用户手动同步 163/本地邮件样本
          ↓
客观求职信息提取
          ↓
SQLite + 来源/证据/附件关系
          ↕
Excel Tracker 双向同步
          ↓
每岗位 Markdown + 手动 Summary
```

Stage 0–4 首发不实现（后续能力以当前 Stage 与 CURRENT-POLICY 为准）：

- 岗位发现和推荐。
- 替用户作求职决策。
- 未读监控和主动提醒。
- 模拟题、模拟面试、评分和训练计划。
- 登录第三方内容账号、绕过反爬或付费墙。
- 自动填表、自动投递和自动提交。
- Multi-Agent、长期记忆、多租户和商业化。

## 2. Stage 总表

| Stage | 名称 | 核心输入 | 核心输出 | 范围 |
|---|---|---|---|---|
| 0 | 契约与安全 | 已确认需求 | Schema、接口和安全标准 | 首发 |
| 1 | 本地数据与 Excel | Tracker | 双向同步和修改历史 | 首发 |
| 2 | Application Core | 标准化数据 | 数据库、证据、附件关系和 Markdown 路径 | 首发 |
| 3 | 邮箱与提取 | 163/邮件样本 | 客观信息、时间线和 Tracker 更新 | 首发 |
| 4 | 本地 Web 与 Summary | Application、JD、当前阶段 | Web、岗位 Markdown、公开资料 Summary | 首发 |
| 5 | 求职智能模块 | 稳定业务数据 | 个性化辅助模块 | 后续 |
| 6 | 统一 Career Assistant | 稳定工具模块 | 受控路由、调度和评测 | 后续 |
| 7 | 外部与自动化扩展 | 稳定首发产品 | 提醒、日历、通知、受控预填和回复草稿 | 后续 |
| 8 | 部署与商业化 | 完整本地产品 | 普通用户产品与运营能力 | 最后 |

## 3. 架构边界

### Open Core

- 核心业务和本地运行能力放在开源核心。
- 商业能力只能通过公开、稳定、可版本化的接口接入。
- 核心模块不得依赖支付、配额、运营、托管凭证或商业专属集成。
- 当前只定义扩展点，不实现上述商业能力。
- 扩展接口需要兼容性策略、安全边界和最小权限。
- 开源核心采用 Apache License 2.0。

### Mail Adapter

- 提供供应商无关的只读邮箱接口。
- 首发实现本地样本和 163 IMAP。
- 手动同步默认，可选定时同步默认关闭。
- 只负责读取和标准化，不替用户做决策。

### Extraction

- 从邮件提取明确的公司、岗位、阶段、日期、截止时间、链接和要求。
- 保存证据片段和来源。
- 不明确内容留空。
- 不生成行动建议。

### Application Core

- 管理 Application、邮件事件、当前 Tracker 快照、附件和来源。
- 是唯一可受控修改业务数据的服务。
- 记录系统提取值、用户值、来源和修改时间。
- 以 Excel 人工值为基线，明确较新事件按字段更新，先后不明保留人工值并提示。

### Excel Sync

- 数据库更新到 Excel。
- Excel 用户修改回数据库。
- 不把长邮件和 Summary 写入单元格。
- 不静默覆盖用户值。

### Summary

- 只在用户主动触发时联网和调用模型。
- 生成公司、JD、公开笔试和面试资料。
- 保存来源、抓取时间、不确定性和版本。
- 输出到每个 Application 独立 Markdown。

### Local Web

- 首发主要操作入口。
- 不直接复制业务逻辑，只调用同一 Service。
- 默认只监听本机。
- 明确显示外部调用和数据离机情况。

### 首发技术栈

- Backend：Python、FastAPI、Pydantic。
- Frontend：React、TypeScript、Vite。
- Persistence：SQLAlchemy、SQLite、Alembic。
- Excel：openpyxl。
- 首要环境：Windows。
- 可移植环境：Docker。

### 本地用户边界

- 首发单用户，无本地账户和 RBAC。
- 单用户、163 和多简历；多邮箱后置。
- 数据统一位于 `data/` 目录体系。
- 既有永久删除和导入备份按当前规则保留；完整恢复产品后置，不把已存在功能写成仅接口。

## 4. Tracker 标准

主表列：

```text
投递时间
公司名称
岗位
简历通过
测评
笔试
一面
二面
三面
HR 面
终面
当前阶段
截止时间
JD 链接
最近更新时间
当前简历
备注
```

阶段单元格采用“日期 + 结果/安排”。特殊轮次进入备注和岗位详情 Markdown。

## 5. 数据与来源标准

关键业务字段至少能够追溯：

- 当前显示值。
- 系统提取值。
- 用户修改值。
- 来源类型和来源 ID。
- 证据片段。
- 创建和修改时间。

邮件默认长期保存元数据、结构化结果、必要摘要、证据片段和原始哈希，不默认保存完整 MIME 与完整正文。

## 6. 接口通用标准

- HTTP 前缀：`/api/v1`
- 字段：`snake_case`
- ID：UUID 字符串
- 时间：带时区 ISO 8601
- 写入支持幂等键
- 列表支持分页和筛选
- 错误响应包含稳定错误码和 `request_id`
- 错误、日志和响应不得泄露凭证或完整邮件正文
- 项目采用语义化版本 `MAJOR.MINOR.PATCH`
- 数据库从首版使用 Alembic 迁移
- Excel 模板包含 Schema 版本和稳定 Application ID
- 扩展协议独立版本化
- 破坏性升级必须提供迁移，不要求用户删除 `data/`

示例资源：

```text
/api/v1/applications
/api/v1/applications/{application_id}/events
/api/v1/applications/{application_id}/artifacts
/api/v1/mail-accounts
/api/v1/mail-sync-jobs
/api/v1/excel-sync-jobs
/api/v1/attachments
/api/v1/summary-jobs
/api/v1/jobs
/api/v1/jobs/{job_id}
/api/v1/jobs/{job_id}/resume
/api/v1/jobs/{job_id}/restart
```

具体 endpoint 在进入对应 Stage 时细化，不在总体规划中提前锁死。

## 7. 幂等和冲突标准

需要幂等：

- 邮件同步。
- Excel 同步。
- ApplicationEvent 写入。
- 附件下载。
- Summary 生成。

数据库唯一约束是最终保护。Excel 与数据库更新必须携带版本或更新时间；发现冲突时保留用户值和双方历史，不静默覆盖。

## 7.1 Job 与 Checkpoint 标准

邮箱同步、Excel 同步、附件处理、Summary 和数据库迁移采用统一可恢复任务契约。

任务至少保存：

- `job_id`
- `job_type`
- `status`
- `current_step`
- `completed_steps`
- `checkpoint`
- `input_refs`
- `error_code`
- `error_message_safe`
- `retryable`
- `recovery_action`
- `retry_count`
- `processor_version`
- `created_at`
- `updated_at`
- `finished_at`

只有成功提交的事务才能推进检查点。恢复和重新开始都必须复用稳定来源 ID 与幂等键。用户任务记录与开发日志分离。

## 8. ModelGateway

业务模块不得直接绑定某个模型 SDK。

统一能力：

- 本地模型与云模型切换。
- Schema 化输入输出。
- 超时、成本和隐私等级。
- 模型、Prompt 和处理器版本。
- 外部调用前的敏感信息裁剪。
- Web 中的数据离机提示。

模型可提供有据判断与建议，但不得把推断写成用户事实或替用户执行求职决定。

## 9. Artifact 标准

所有生成内容统一保存为 Artifact：

- `artifact_type`
- `application_id`
- `stage`
- `content`
- `format`
- `source_ids`
- `model`
- `prompt_version`
- `created_at`
- `supersedes_id`

首发主要输出 Markdown。普通更新保留版本和时间线；用户确认永久删除岗位时按当前规则删除其专属派生成果。

## 10. 安全标准

- 邮箱只读。
- 凭证只存环境变量或系统密钥库。
- 邮件、附件、网页和模型输出均为不可信输入。
- 附件采用类型、大小和路径白名单；禁止执行宏、脚本和压缩包内容。
- Excel 外部文本做公式注入防护。
- 本地 Web 默认只监听本机。
- 外部搜索只访问无需登录的公开信息。
- 禁止登录第三方内容账号、绕过反爬和付费墙。
- 外部模型只接收完成任务所需的最小数据。
- Agent 通过受控 Service 工作，不拥有任意数据库写权限。
- 商业扩展不得绕过 Open Core 的权限、审计、数据隔离和敏感信息规则。
- Windows 凭证通过 Credential Manager 保存。
- Docker 凭证通过环境变量或 secret 文件注入。
- `.env` 只用于开发并必须被 Git 忽略。
- 前端不得直接持有邮箱或模型密钥。
- 首发禁止任意第三方插件加载；未来插件需要权限声明、签名、沙箱、兼容和撤销。

## 11. 最低测试与维护门槛

- 单元测试：模型、来源、冲突和安全规则。
- 集成测试：SQLite、Excel、MailAdapter、ModelGateway。
- 端到端冒烟：FastAPI、React、样本邮件、Excel。
- 安全回归：公式注入、路径穿越、恶意附件名、Prompt Injection、敏感日志。
- 固定脱敏测试样本和模型桩。
- Python/TypeScript 静态与格式检查。
- 依赖漏洞扫描和 secret scanning。
- Windows CI/验收优先，Docker 构建验证其次。
