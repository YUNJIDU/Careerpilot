# Stage 2：Application Core 与持久化

## Goal

实现 SQLite、Alembic、Application Service、字段来源、Job/Checkpoint 持久化，并把 Stage 1 Excel 引擎接入唯一业务写入口。

## Entry

- Stage 1 Exit Gate 全部通过。
- 数据实体、事件和 provenance 契约稳定。

## Work Packages

### S2.1 数据库与迁移

表：

- applications
- application_events
- field_provenance
- email_records
- attachments
- job_descriptions
- artifacts
- resumes
- sync_batches
- background_jobs
- job_checkpoints

任务：

- 建立首个 Alembic migration。
- 唯一约束、外键、索引、版本列和 UTC 时间。
- 迁移失败停止启动并保留原数据库。

### S2.2 Repository

- Repository 只处理持久化，不包含业务判断。
- 测试 SQLite 文件库和事务回滚。
- API、Excel、Agent 不直接访问 ORM Session。

### S2.3 Application Service

能力：

- create/get/list/update/archive。
- append_event。
- apply_field_change。
- record_provenance。
- attach_artifact/attachment。
- 维护 Tracker 快照和 Markdown 路径。

规则：

- 用户值优先。
- 系统值作为来源化历史追加。
- 删除默认归档。
- 幂等键和乐观锁。

### S2.4 Job/Checkpoint Service

- create/start/progress/fail/complete/resume/restart。
- 只有事务成功才推进 checkpoint。
- 用户安全错误与开发日志分离。
- restart 保留旧任务和审计。

### S2.5 Excel 双向集成

- Excel Diff 命令通过 Application Service 执行。
- 数据库快照通过 Excel Writer 输出。
- 保存同步基线、批次、工作簿版本和行版本。
- 同步中断可恢复，不重复创建 Application。

### S2.6 API

最小资源：

- applications
- events
- excel-sync-jobs
- jobs

要求：

- `/api/v1`
- request_id、统一错误、分页、幂等键。
- API 只调用 Service。

### S2.7 测试

- CRUD、归档、provenance、乐观锁、幂等。
- 事务回滚和迁移失败。
- Excel → DB → Excel → 用户修改 → DB。
- Job 失败、恢复和重新开始。

## Exit Gate

1. SQLite 重启后数据不丢失。
2. Alembic 可从空库升级并检测失败。
3. 所有业务写入通过 Application Service。
4. 用户值优先和来源历史测试通过。
5. Excel 双向端到端通过。
6. Job/Checkpoint 在进程重启后可恢复。

## Demo

导入 Excel、查询 API、修改数据库、导出 Excel、用户改表后回写，并中断一次同步后从 checkpoint 继续。
