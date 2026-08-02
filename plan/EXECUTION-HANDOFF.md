# CareerPilot 新对话执行交接

更新时间：2026-08-02

## 任务目标

维护已完成到 Stage 7 的 CareerPilot 本地发布候选，并在开始 Stage 8 前先完成生产化详细设计。

CareerPilot 是辅助求职 Agent，不替用户查看邮件、作求职决定或完成自动投递。首发版本服务本人及能够本地部署的 AI 技术用户，后续再演进为云端 Web/SaaS。

## 首发闭环

```text
本地 Web 配置
  → 用户手动同步 163/本地邮件样本
  → 提取客观求职信息
  → 保存 SQLite、来源、证据和必要附件
  → 双向同步 Excel Tracker
  → 查看每个岗位的详情 Markdown
  → 用户手动生成公司/JD/笔试/面试 Summary
  → Web 或 Markdown 查看
```

## 已批准技术基线

- Backend：Python、FastAPI、Pydantic。
- Frontend：React、TypeScript、Vite。
- Persistence：SQLAlchemy、SQLite、Alembic。
- Excel：openpyxl。
- 首要运行与验收环境：Windows。
- 第二运行环境：Docker。
- 单用户，可管理多份简历和多个邮箱账户。
- 运行数据统一位于 `data/`。
- Apache-2.0 Open Core。
- 首发使用单一主辅助 Agent；后续 Multi-Agent 使用 Orchestrator。
- Windows 凭证使用 Credential Manager；Docker 使用环境变量或 secret 文件。
- API 从 `/api/v1` 开始，项目采用语义化版本。

## 已执行顺序

1. Stage 0：契约、安全与工程骨架。
2. Stage 1：Excel Schema、解析、写出与差异计算。
3. Stage 2：Application Core、SQLite、Alembic 和实际双向写入。
4. Stage 3：MailAdapter、163、客观信息提取、附件和断点。
5. Stage 4：本地 Web、岗位 Markdown、手动 Summary 和 Docker 发布闭环。
6. P0.5：统一 MailAdapter、多邮箱、本地 `.eml`、附件批准和多简历。
7. Stage 5：JD、公司研究、Resume–JD 证据映射、缺口和人工复盘。
8. Stage 6：受控单 Agent、工具、预算、检查点和写入审批。
9. Stage 7：Gmail/Outlook、提醒、ICS、通知和受控网页预填。

不得跳过 Stage Gate。每个 Stage 的 Entry、任务、测试、Exit Gate 和 Demo 见详细计划。

## 新对话必须先阅读

1. [批准的框架设计](../docs/superpowers/specs/2026-07-26-careerpilot-framework-design.md)
2. [P0–P3 当前交付说明](../docs/DELIVERY_P0_P3.md)
3. [接口与安全标准](stages/stage-api-standards.md)
4. [Stage 5–7 当前设计](stages/)

维护既有 Stage 时，再读取对应的实施文档：

- [Stage 1](implementation/stage-01-implementation.md)
- [Stage 2](implementation/stage-02-implementation.md)
- [Stage 3](implementation/stage-03-implementation.md)
- [Stage 4](implementation/stage-04-implementation.md)
- [P0.5 使用与安全](../docs/P05_MVP.md)
- [Stage 5 证据智能](../docs/STAGE5_EVIDENCE.md)
- [Stage 6 Agent](../docs/STAGE6_AGENT.md)
- [Stage 7 外部集成](../docs/STAGE7_INTEGRATIONS.md)

## 当前状态与下一步

- Stage 0–7、P0.5、统一工作台 UI、Docker 和本地发布门禁已完成。
- 当前数据库版本为 Alembic `0009`；迁移前备份、重启恢复和数据持久化已验证。
- Stage 5 的 JD/公司研究/证据映射/缺口/复盘、Stage 6 的受控单 Agent、
  Stage 7 的只读 OAuth/提醒/ICS/通知/安全预填均有后端和浏览器测试。
- Stage 6 真实模型评测决定不引入 Multi-Agent。
- Gmail/Outlook 代码与模拟供应商测试已通过；真实授权仍需要使用者自己的
  Google Cloud / Microsoft Entra 应用和测试账户。
- 下一步是 Stage 8 详细设计，不得在未设计租户、认证、备份、删除权和合规前公网部署。
- 运行数据继续保留在 `data/`，不得提交真实邮件、数据库、Tracker 或凭证。

## 不可违反的边界

- 用户始终负责理解邮件和作求职决定。
- 邮件提取只保存客观信息、来源和证据。
- 用户在 Excel/Web 中的修改优先，不得被静默覆盖。
- 邮箱只读。
- Summary 只由用户手动触发。
- 不做岗位发现、职位推荐、候选人评分、录用概率或 Multi-Agent 空壳。
- 首发不加载任意第三方插件。
- 不登录第三方内容账号，不绕过反爬、验证码或付费墙。
- 浏览器能力只预填白名单字段并展示差异，不自动提交；验证码始终人工处理。
- 密钥不得进入 SQLite、Excel、Markdown、日志、前端、Git 或构建产物。
- 真实邮件、简历、附件和运行数据不得提交到 Git。
- 所有长任务必须有 Job、Checkpoint、幂等和安全恢复说明。

## 实施工作方式

- 先检查现有文件和工作树，保留用户已有改动。
- 按 Stage 计划逐项实施，不自行扩展范围。
- 每个功能先建立失败测试或契约测试。
- API、Excel、邮箱、Agent 和前端不得绕过 Application Service。
- 每完成一个 Work Package 就运行相关测试。
- Stage 结束时运行全量检查，完成 Demo，并逐条验证 Exit Gate。
- 未通过 Exit Gate，不进入下一 Stage。

## 可复制到新对话的提示词

```text
请先审查 CareerPilot P0–P3 本地发布候选，然后提交 Stage 8 详细设计，不要直接实现。

项目路径：E:\鸡哥项目\Careerpilot

先完整阅读：
1. plan/EXECUTION-HANDOFF.md
2. docs/DELIVERY_P0_P3.md
3. docs/superpowers/specs/2026-07-26-careerpilot-framework-design.md
4. plan/stages/stage-api-standards.md
5. plan/stages/stage-08-deployment-and-commercialization.md

先检查仓库、环境、现有改动和适用的 AGENTS.md/技能说明。详细设计必须覆盖
PostgreSQL、Worker、对象存储、备份恢复、导出删除、身份/租户隔离、审计、
凭证、迁移兼容和 SaaS 合规；设计批准前不修改 Stage 8 代码。
```
