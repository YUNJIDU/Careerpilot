# Changelog

本项目使用 [Keep a Changelog](https://keepachangelog.com/) 的结构，并以语义化版本为目标。当前条目是尚未推送或打标签的本地发布候选。

## [Unreleased]

### Added

- Stage 4C：多阶段 Docker 镜像、Windows/Linux CI、浏览器 E2E、依赖/许可证/Secret/镜像扫描和发布冒烟。
- P0.5：唯一 `MailAdapter v1`、多邮箱账户、本地 `.eml` 导入、附件批准下载、多简历版本和岗位关联。
- Stage 5：JD 版本与结构化、公司研究版本、Resume–JD 证据映射、确定性缺口分析和人工复盘。
- Stage 6：受控单 Agent、内置工具白名单、预算、检查点、写入审批、审计和恢复。
- Stage 7：Gmail API、Microsoft Graph 只读 OAuth、提醒、ICS、站内/浏览器通知和受控表单预填扩展。
- 全新欢迎页和统一工作台 UI，包括响应式布局、统一设计令牌和 Stage 5–7 页面。
- Alembic `0003`–`0009` 数据迁移及逐次迁移前备份。
- Windows/Linux 锁定依赖和独立的运行、开发、安全依赖集合。

### Changed

- 邮件、Web、Excel 和任务继续通过同一 Application Service 写入，保留人工修改优先级和来源链。
- Summary 搜索入口统一为可注入搜索客户端；模型输出和来源验证更严格，失败任务可从检查点恢复。
- SecretStore 支持多邮箱、模型、搜索和 OAuth 命名凭证；API 只暴露“是否已保存”。
- Docker 运行用户改为非 root，运行数据集中到 `/app/data`，前端由同一发布镜像提供。

### Security

- 上传文件执行大小、扩展名、MIME、签名、路径穿越、压缩炸弹、宏和恶意文件名校验。
- OAuth 使用 Authorization Code + PKCE、一次性短时 state 和最小只读 scope；令牌不进入 SQLite。
- Agent 不能执行任意代码、Shell、SQL 或插件，所有业务写入必须展示准确预览并由用户批准。
- 浏览器扩展只处理允许字段，检测 CAPTCHA 后停止，且不存在自动提交代码。
- CI 对 Python/npm 依赖、Secret 和 Docker HIGH/CRITICAL 漏洞执行门禁。

### Known limitations

- 当前仍是单用户、本地优先版本，没有 PostgreSQL、Worker、对象存储、租户隔离、账户系统或 SaaS 合规能力。
- Gmail/Outlook 代码和模拟集成测试已完成；真实供应商授权需要使用者自己的 OAuth 应用与测试账号。
- 不提供岗位发现、招聘推荐、候选人评分、录用概率、验证码绕过或自动投递。

[Unreleased]: https://github.com/YUNJIDU/Careerpilot/compare/main...HEAD
