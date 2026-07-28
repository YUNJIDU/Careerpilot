# Stage 4：本地 Web、Markdown 与 Summary

## Goal

完成首发用户闭环、Windows 验收和 Docker 验证。

## Entry

- Stage 3 Exit Gate 全部通过。
- Application、Excel、Mail、Job 和 ModelGateway API 稳定。

## Progress

- Stage 4A complete: S4.1 Web shell, S4.2 local settings/secret status,
  S4.3 editable Tracker/Application Detail, and S4.7 Jobs UI.
- Next: Stage 4B Markdown and manual Summary, then Stage 4C Docker acceptance.

## Work Packages

### S4.1 React 应用壳

页面：

- Setup
- Tracker
- Application Detail
- Mail Sync
- Excel Sync
- Jobs
- Summary

要求：

- 类型化 API client。
- 清晰的 loading/error/empty 状态。
- 显示网络调用和数据离机提示。
- 不在 localStorage 保存秘密。

具体视觉设计在本 Stage 开始时单独确认。

### S4.2 Setup

- 163 账户配置和连接测试。
- 本地/云模型选择。
- data、Excel、Markdown 路径。
- 定时同步开关默认关闭。
- SecretStore 状态，不回显秘密。

### S4.3 Tracker 与 Detail

- 列表、筛选和最近更新时间。
- Application 时间线、证据、附件、JD、Artifact。
- Excel 同步入口和冲突说明。
- 打开对应 Markdown。

### S4.4 Markdown Service

- 安全稳定文件名使用 application_id，显示名可读。
- 原子写入和版本历史。
- 公司/JD、时间线、证据、附件、Summary 分节。
- 外部内容转义，不执行嵌入 HTML/脚本。

### S4.5 Summary Pipeline

步骤：

1. 收集最小 Application 上下文。
2. 获取无需登录的公开页面。
3. 提取内容和来源。
4. ModelGateway 生成结构化 Summary。
5. 验证引用、抓取时间和不确定性。
6. 生成新 Artifact 与 Markdown 版本。

边界：

- 仅用户手动触发。
- 不登录、不绕过反爬、验证码和付费墙。
- 不生成训练题或替用户决策。

### S4.6 Summary Job/Checkpoint

- fetch、extract、normalize、generate、render。
- 复用未过期成功结果。
- 失败保留旧 Summary。
- resume/restart 幂等。

### S4.7 Jobs UI

- 任务列表、进度、当前步骤和计数。
- 脱敏错误、恢复建议。
- Resume/Restart。
- 技术日志仅提供安全摘要入口。

### S4.8 Agent

- 一个主辅助 Agent，只组合稳定工具。
- 工具输入输出均为 Schema。
- Agent 不直接访问 ORM、文件系统或秘密。
- 非 Agent API 仍可完成全部核心流程。

### S4.9 Docker

- 多阶段构建。
- 非 root 运行。
- data volume 和 secret 注入。
- healthcheck。
- 与 Windows 使用同一 Alembic 和契约。

### S4.10 首发验收

- 完整 E2E。
- Windows 原生启动文档。
- Docker 启动文档。
- 安全回归和依赖扫描。
- 脱敏演示数据。
- 已知限制和故障恢复手册。

## Exit Gate

1. 用户能在 Web 完成首发闭环。
2. Summary 事实带来源、时间和不确定性。
3. 所有任务失败可见且可恢复。
4. Windows 全量测试通过。
5. Docker 构建、迁移、启动和冒烟通过。
6. 无首发范围外功能成为必要依赖。
7. 安全、许可证、secret 和依赖扫描通过。

## Demo

从全新 Windows 环境启动，配置样本/163、同步、查看 Tracker、修改 Excel、查看详情、生成 Summary、模拟中断恢复，再用同一 fixtures 完成 Docker 冒烟。
