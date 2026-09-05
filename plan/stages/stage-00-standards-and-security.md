# Stage 0：标准、数据契约与安全基线

## 目标

固定首发模块共同依赖的数据、Excel、邮箱、模型、文件和安全标准。进入尚未讨论的后期 Stage 时，再补充该 Stage 的详细契约。

## WBS

### 0.1 领域数据契约

- UserProfile
- Experience
- Skill
- ResumeVersion
- Application
- ApplicationEvent
- EmailRecord
- JobDescription
- ResearchSource
- Artifact
- ReviewItem
- FieldProvenance
- ExcelSyncBatch
- MailSyncBatch
- BackgroundJob
- JobCheckpoint

### 0.2 状态和事件

状态：

```text
DRAFT → APPLIED → OA → INTERVIEW → OFFER → ACCEPTED
```

旁路/终止状态：

```text
REJECTED · WITHDRAWN · GHOSTED · ARCHIVED
```

ApplicationEvent 是不可变历史，Application 的统计字段是当前快照。邮件提取只记录客观信息，不替用户做求职决策；用户在 Excel 或 Web 中的手工修改优先。

### 0.3 API 契约

- `/api/v1`。
- `snake_case`。
- UUID。
- 带时区 ISO 8601。
- 标准成功/错误响应。
- Idempotency-Key。
- 分页、筛选、request_id 和审计字段。

### 0.4 ModelGateway

```text
Python/规则 → 本地模型或外部模型 → Schema/业务规则校验 → 保存值、来源与证据
```

业务模块不得直接绑定某个模型 SDK。

支持本地模型与云模型切换。外部调用前裁剪非必要个人信息，并在本地 Web 明确显示数据是否会离开本机。

### 0.5 首发产品边界

- 本地 Web 是主要操作入口。
- Excel 是岗位字段唯一事实源，Web 修改安全回写 Excel。
- Markdown 是每个 Application 的详情和 Summary。
- 163 是首个真实邮箱适配器，业务层使用统一 MailAdapter。
- Summary 只由用户手动触发。
- 首发使用单一主辅助 Agent；Multi-Agent 后置。
- 首发严格单用户，163 和多简历；多邮箱后置。
- Windows 原生优先，随后提供 Docker。
- 核心采用 Apache-2.0 Open Core。

### 0.6 安全基线

- 密钥不进入代码、Git、Excel、Prompt 和日志。
- 外部网页、邮件和附件均是不可信输入。
- LLM 输出必须经过 Schema 和业务规则验证。
- Excel 公式注入防护。
- 文件路径限制在授权目录。
- 写入使用事务和幂等约束。
- 邮箱只读，手动同步为默认方式。
- 邮件和附件均视为不可信输入。
- 用户值不被邮件提取结果静默覆盖。
- Agent 通过受控服务写入，不拥有任意数据库写权限。
- 普通配置与秘密分离。
- Windows 秘密进入 Credential Manager；Docker 使用环境变量或 secret 文件。
- React 前端、SQLite、Excel、Markdown、日志和构建产物不得保存明文密钥。
- 首发只加载内置适配器，不执行任意第三方插件。

## 输出

- 数据模型说明。
- 状态转换表。
- API 和错误码标准。
- ModelGateway 契约。
- 安全检查清单。
- input.xlsx Schema。
- MailAdapter、Excel 双向同步和文件存储契约。
- SecretStore、扩展协议版本、Backup/Restore/Delete 接口。
- JobStore、CheckpointStore 和可恢复任务契约。
- Apache-2.0 LICENSE 和第三方依赖许可证清单。

## 完成标准

- 后续 Stage 能引用同一套字段和枚举。
- API、CLI、数据库和 Artifact 命名一致。
- 没有未定义的外部访问、数据覆盖或高风险写入路径。
- Schema、API 和扩展接口具备版本与迁移策略。
