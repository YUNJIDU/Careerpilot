# CareerPilot 新对话执行交接

更新时间：2026-07-26

## 任务目标

从 Stage 0 开始实施 CareerPilot。

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

## 执行顺序

1. Stage 0：契约、安全与工程骨架。
2. Stage 1：Excel Schema、解析、写出与差异计算。
3. Stage 2：Application Core、SQLite、Alembic 和实际双向写入。
4. Stage 3：MailAdapter、163、客观信息提取、附件和断点。
5. Stage 4：本地 Web、岗位 Markdown、手动 Summary 和 Docker。

不得跳过 Stage Gate。每个 Stage 的 Entry、任务、测试、Exit Gate 和 Demo 见详细计划。

## 新对话必须先阅读

1. [批准的框架设计](../docs/superpowers/specs/2026-07-26-careerpilot-framework-design.md)
2. [Stage 0–4 实施总计划](implementation/README.md)
3. [Stage 0 详细计划](implementation/stage-00-implementation.md)
4. [接口与安全标准](stages/stage-api-standards.md)

执行后续 Stage 时，再读取对应的实施文档：

- [Stage 1](implementation/stage-01-implementation.md)
- [Stage 2](implementation/stage-02-implementation.md)
- [Stage 3](implementation/stage-03-implementation.md)
- [Stage 4](implementation/stage-04-implementation.md)

## 当前第一步

只执行 Stage 0：

- 检查仓库和环境现状。
- 建立 Apache-2.0、Git 忽略和依赖许可证基线。
- 建立 Backend/Frontend 工程骨架。
- 建立 `/api/v1/health`。
- 定义契约、扩展接口、SecretStore 与 Job/Checkpoint。
- 建立安全工具和最低质量流水线。
- 在 Windows 完成 Stage 0 Demo 和 Exit Gate。

不要提前实现 Excel、SQLite 业务表、真实邮箱或 Summary。

## 不可违反的边界

- 用户始终负责理解邮件和作求职决定。
- 邮件提取只保存客观信息、来源和证据。
- 用户在 Excel/Web 中的修改优先，不得被静默覆盖。
- 邮箱只读。
- Summary 只由用户手动触发。
- 首发不做岗位发现、职位推荐、提醒、模拟训练、自动填表和 Multi-Agent。
- 首发不加载任意第三方插件。
- 不登录第三方内容账号，不绕过反爬、验证码或付费墙。
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
请开始执行 CareerPilot Stage 0。

项目路径：E:\Master\CareerPilot

先完整阅读：
1. plan/EXECUTION-HANDOFF.md
2. docs/superpowers/specs/2026-07-26-careerpilot-framework-design.md
3. plan/implementation/README.md
4. plan/implementation/stage-00-implementation.md
5. plan/stages/stage-api-standards.md

严格按已批准范围实施，只执行 Stage 0，不提前实现 Stage 1–4。
先检查仓库、环境、现有改动和适用的 AGENTS.md/技能说明，再开始修改。
实施时持续运行对应测试；最后完成 Stage 0 Demo，逐条报告 Exit Gate 是否通过、修改了哪些文件、测试结果和剩余风险。
```
