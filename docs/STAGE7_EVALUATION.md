# Stage 7 本地验收记录

日期：2026-08-02

## 结论

P3 Stage 7 的代码、数据库迁移、前端、最小权限浏览器扩展、安全门禁和 Docker 本地部署已完成。Gmail 与 Outlook 的供应商调用由模拟 OAuth/HTTP 集成测试覆盖；由于本机未配置 Google/Microsoft OAuth Client ID 和测试账户，本次不声称完成真实供应商账号授权。

## 自动化结果

| 门禁 | 结果 |
|---|---|
| 后端全量测试 | `81 passed` |
| Ruff | `All checks passed` |
| Linux 锁定依赖 `pip check` | 无损坏依赖 |
| Python `pip-audit` | 无已知漏洞 |
| 前端 TypeScript / 生产构建 | 通过 |
| 浏览器 E2E | `4 passed`，含提醒与受控预填会话 |
| npm audit | `0 vulnerabilities` |
| Gitleaks 工作区扫描 | `no leaks found` |
| Trivy CRITICAL | `0` |
| Trivy 有修复版本的 HIGH | `0` |

## 数据库与容器

- 生产镜像：`careerpilot:stage7-external-integrations`
- 运行容器：`careerpilot-stage7-external-integrations-v3`（前两版容器已停止并保留作回滚）
- Web：`http://127.0.0.1:9999/#/integrations`
- API：`http://127.0.0.1:9998/api/v1`
- Alembic：`0009`
- SQLite `PRAGMA integrity_check`：`ok`
- 新表：`oauth_connections`、`reminders`、`notification_events`、`prefill_sessions`
- 迁移备份：`data/careerpilot.db.pre-0009.bak`

## 已验证的安全边界

- OAuth state 一次性且 10 分钟失效；Authorization Code + PKCE；Gmail/Outlook 只读 scope。
- access token、refresh token、Client ID 和 Client Secret 不进入 SQLite、API 响应、浏览器存储或日志。
- Gmail/Outlook 原始 MIME 复用 `MailAdapter v1` 和既有邮件/附件链路。
- 预填目标仅允许 HTTPS origin；字段固定白名单；第三方网页内容不发送给模型。
- 扩展权限仅为 `activeTab`、`scripting` 和本机 API；没有 `<all_urls>`。
- CAPTCHA 出现即停止；扩展不读取密码或文件，不调用 `submit()` / `requestSubmit()`，不点击提交按钮。

## 真实供应商最终验收

要关闭真实 OAuth 门禁，需要主人提供自有 Google Cloud / Microsoft Entra 测试应用和测试邮箱，在供应商控制台登记文档中的回调地址，然后分别完成授权、连接测试、只读同步、令牌刷新和断开。没有这些外部凭证时，项目保持安全的“未连接”状态。
