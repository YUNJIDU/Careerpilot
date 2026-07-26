# Stage 0–4 详细实施计划

依据：[首发框架设计总纲](../../docs/superpowers/specs/2026-07-26-careerpilot-framework-design.md)

## 执行原则

- 按 Stage Gate 顺序执行，未通过退出条件不得进入下一 Stage。
- 每个任务先写失败测试或契约测试，再实现最小功能。
- 业务规则只存在于 Application Service，不复制到 API、Excel、前端或 Agent。
- 每个 Stage 结束必须完成 Windows 演示、测试报告、安全检查和文档更新。
- Docker 在 Stage 4 完成首发闭环后作为第二环境验证。

## Stage 依赖

```text
Stage 0 契约与骨架
   ↓
Stage 1 Excel Schema、解析与差异计算
   ↓
Stage 2 SQLite、Application Core、持久化和双向写入
   ↓
Stage 3 MailAdapter、163、提取、附件与断点
   ↓
Stage 4 React Web、Markdown、Summary、Docker 与首发验收
```

## 跨 Stage 决策

- Stage 1 不直接拥有数据库业务写入；只产出标准 DTO、差异和同步命令。
- Stage 2 的 Application Service 是唯一业务写入口。
- Stage 3 的提取器只产出带证据的候选字段，不直接操作 ORM。
- Stage 4 的 Agent、API 和 React 只组合已有服务。
- Job/Checkpoint 从 Stage 0 定义、Stage 2 持久化、Stage 3/4 使用。

## 计划文档

1. [Stage 0：契约、安全与工程骨架](stage-00-implementation.md)
2. [Stage 1：Excel Schema 与同步引擎](stage-01-implementation.md)
3. [Stage 2：Application Core 与持久化](stage-02-implementation.md)
4. [Stage 3：邮箱同步与客观提取](stage-03-implementation.md)
5. [Stage 4：本地 Web、Markdown 与 Summary](stage-04-implementation.md)

## 首发总体验收

```text
Windows 启动
  → 配置 163/样本邮箱
  → 手动同步
  → 数据库与 Excel 更新
  → Excel 用户修改回写
  → 查看岗位详情和证据
  → 手动生成 Summary
  → 中断后从检查点继续
  → Docker 使用同一数据契约启动
```
