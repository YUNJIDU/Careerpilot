# Stage 2：Application 核心数据库

## 目标

建立产品的本地完整事实存储和稳定业务服务。Excel 是岗位字段唯一事实源；数据库保存来源、运行状态和派生关系，Markdown 是岗位详情和 Summary。

## 技术范围

- Python
- Pydantic
- SQLAlchemy
- SQLite
- openpyxl
- pytest

## WBS

### 2.1 数据库

实现 Application、ApplicationEvent、EmailRecord、ResumeVersion、JobDescription、Artifact、Attachment、FieldProvenance、ImportBatch、MailSyncBatch 和 ExcelSyncBatch。

### 2.2 Application Service

- 创建、读取、修改和确认后永久删除。
- 添加邮件提取事件和用户编辑事件。
- 维护 Tracker 当前统计快照。
- 保存字段来源、证据和修改历史。
- 维护每个 Application 的 Markdown 路径。
- 事务和幂等。

### 2.3 Excel Sync Service

- 数据库更新同步到 Tracker。
- Excel 用户修改同步回数据库。
- 人工 Excel 基线只按明确的新事件作字段增量更新；冲突先后不明时保留人工值。
- 邮件新信息追加历史，不静默覆盖用户值。
- 处理工作簿版本、并发冲突和恢复。

### 2.4 审计

记录来源、时间、操作者、旧值、新值和 request_id。

## CLI 与 API

```text
jobtracker export tracker.xlsx

GET   /api/v1/applications
POST  /api/v1/applications
GET   /api/v1/applications/{application_id}
PATCH /api/v1/applications/{application_id}
POST  /api/v1/applications/{application_id}/events
GET   /api/v1/applications/{application_id}/events
POST  /api/v1/exports
```

## 安全

- 数据库唯一约束。
- 写操作事务回滚。
- 乐观锁避免覆盖用户修改。
- 岗位永久删除并清理专属派生成果；原始邮件解除关联，独立简历保留。
- Excel 公式注入转义。
- 敏感字段不进入 Tracker。

## 输出

- SQLite 数据库。
- Application Service。
- State Machine。
- Excel Sync Service。
- 核心测试。

## 完成标准

- Excel 导入记录能够持久化。
- 重启后数据不丢失。
- 状态变化保留事件历史。
- Excel 与数据库双向修改可追溯，用户值不被静默覆盖。
