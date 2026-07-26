# Sprint 1：标准、本地数据与 Excel

## Sprint Goal

建立可追溯的本地数据底座，让用户的 Excel Tracker 与 SQLite 安全双向同步，并确保用户手工修改不会被系统静默覆盖。

## 范围

### 包含

- Stage 0 首发数据与安全契约。
- Excel Tracker 模板。
- SQLite 和 SQLAlchemy。
- Application、ApplicationEvent、EmailRecord、FieldProvenance。
- Excel 导入、更新、回写和冲突历史。
- 每个 Application 的 Markdown 路径约定。
- 最小本地服务接口和测试。

### 不包含

- 真实邮箱和邮件解析。
- 外部搜索和 Summary。
- 本地 Web 页面。
- 模拟训练、提醒、自动填表。
- Multi-Agent、MCP 和长期记忆。

## Tracker Schema

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
备注
```

阶段单元格保存“日期 + 结果/安排”。长内容进入岗位 Markdown。

## WBS

1. 固定首发数据、来源和同步契约。
2. 建立 Python 项目、配置、日志和 pytest。
3. 建立 Excel 模板、校验和稳定内部标识。
4. 建立 SQLite Schema、唯一约束和事务。
5. 实现 Application Core。
6. 实现数据库到 Excel 更新。
7. 实现 Excel 用户修改回写。
8. 实现用户值优先、清空语义和冲突历史。
9. 实现公式注入、路径和敏感日志防护。
10. 完成双向同步端到端测试。

## Definition of Done

1. 示例 Tracker 能导入 SQLite。
2. 重启后数据仍存在。
3. 数据库新增或修改可更新 Excel。
4. 用户修改 Excel 后可回写数据库。
5. 用户值不会被后续系统值静默覆盖。
6. 同一工作簿重复同步不重复创建 Application。
7. 错误可定位到 Sheet、行和列。
8. 同步失败可回滚，原 Excel 不损坏。
9. 所有字段修改保留来源和时间。
10. 最小测试在本地一次运行通过。
