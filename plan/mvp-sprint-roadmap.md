# Stage 0–4：首发 Sprint 路线

## 首发闭环

```text
本地 Web
  → 手动同步 163/本地样本
  → 客观求职信息提取
  → 本地数据库与证据
  → Excel Tracker 双向同步
  → Application 详情 Markdown
  → 用户手动生成 Summary
  → Web/Markdown 查看
```

## Sprint 1：标准、本地数据与 Excel

覆盖 Stage 0–2 的基础部分：

- 产品边界、安全和数据契约。
- Excel Tracker Schema。
- SQLite Schema。
- Application、邮件事件、证据和来源。
- Excel 到数据库、数据库到 Excel。
- 用户修改优先和冲突历史。
- 核心测试。

交付演示：

```text
Excel → SQLite → 修改数据库 → Excel → 用户修改 Excel → SQLite
```

## Sprint 2：邮箱同步与信息提取

覆盖 Stage 3：

- 统一 MailAdapter。
- 本地邮件样本。
- 163 IMAP 只读同步。
- 手动同步和默认关闭的定时同步。
- 客观求职信息提取。
- 邮件来源、证据片段和必要附件。
- 数据库与 Excel 更新。

交付演示：

```text
163/样本邮件 → 提取 → Application 时间线 → Excel
```

## Sprint 3：本地 Web 与岗位文档

覆盖 Stage 4 的本地使用闭环：

- 本地 Web 配置与手动同步。
- Tracker 和 Application 详情。
- 每个岗位一份 Markdown。
- Excel 双向同步操作。
- 证据和附件查看。

## Sprint 4：手动 Summary 与首发验收

- 用户手动触发公司/JD/笔试/面试 Summary。
- 本地/云模型切换和数据离机提示。
- 公开来源、抓取时间和不确定性。
- 完整端到端测试。
- 首批技术用户部署说明。

## 首发完成门槛

- 四个 Sprint 全部通过。
- 用户能从本地 Web 完成整个闭环。
- 邮件、网络、模型和 Excel 失败不破坏已有数据。
- 重复邮件不产生重复记录。
- Excel 用户值不被静默覆盖。
- 所有提取信息和 Summary 事实可回溯来源。
- 本地数据与外部调用边界对用户可见。
- 不依赖提醒、模拟训练、自动填表或 Multi-Agent 才能交付。
