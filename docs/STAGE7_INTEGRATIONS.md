# Stage 7 外部集成使用与安全边界

Stage 7 在不改变 Application Core 的前提下增加 Gmail、Outlook、提醒、ICS、通知和受控网页预填。所有能力保持本地优先、人工触发和可撤销。

## 1. Gmail 与 Outlook

- Gmail 使用 Gmail API，只请求 `gmail.readonly`。
- Outlook 使用 Microsoft Graph，只请求读取邮件所需的 `Mail.Read` 和核对授权邮箱所需的 `User.Read`。
- 两者使用 Authorization Code + PKCE；刷新令牌进入 Windows Credential Manager 或 Docker 启动时注入的只读 Secret 文件。
- SQLite 只保存账户、提供商、权限、状态和过期时间，不保存 access token、refresh token、Client ID 或 Client Secret。
- 邮件以原始 MIME 进入 `MailAdapter v1` 和现有解析链；附件仍然先保存元数据，用户逐个批准后才读取内容。

在原生 Windows 运行时，可在“设置”页写入 OAuth Client ID 和可选 Client Secret，再到“外部集成”页授权。回调地址固定为：

```text
Gmail:   http://127.0.0.1:9998/api/v1/oauth/gmail/callback
Outlook: http://127.0.0.1:9998/api/v1/oauth/outlook/callback
```

Docker SecretStore 是只读的，OAuth 客户端配置通过环境变量或 `_FILE` 注入：

```text
CAREERPILOT_SECRET_OAUTH_GMAIL_CLIENT_ID_FILE
CAREERPILOT_SECRET_OAUTH_GMAIL_CLIENT_SECRET_FILE
CAREERPILOT_SECRET_OAUTH_OUTLOOK_CLIENT_ID_FILE
CAREERPILOT_SECRET_OAUTH_OUTLOOK_CLIENT_SECRET_FILE
```

账户令牌也可按账户 ID 注入，例如 `gmail-work` 对应：

```text
CAREERPILOT_SECRET_OAUTH_GMAIL_GMAIL_WORK_TOKEN_FILE
```

令牌文件是 OAuth JSON，至少包含 `access_token`、`refresh_token` 和 ISO 8601 `expires_at`。不要把它放进仓库、SQLite、Excel、浏览器存储或日志。

## 2. 提醒、ICS 与通知

“外部集成”页可为任意岗位创建带时区的提醒。系统在页面读取时扫描未来 3 天，并按 upcoming、urgent、overdue 生成幂等站内通知。点击“开启浏览器通知”后才会请求浏览器权限。

`GET /api/v1/reminders.ics` 导出标准 ICS；导入 Windows 日历、Outlook、Apple Calendar 或 Google Calendar 后，由对应日历负责长期提醒。Stage 7 不加入常驻 Worker，后台队列属于 Stage 8。

## 3. 安全预填扩展

1. 在 Chrome/Edge 扩展管理页开启开发者模式。
2. 选择“加载已解压的扩展程序”，指向仓库的 `browser-extension` 文件夹。
3. 在 CareerPilot“外部集成”页创建预填会话。
4. 打开同源 HTTPS 招聘表单，点击扩展并粘贴会话 ID。
5. 核对扩展展示的当前值与目标值，确认后才填入。

扩展只拥有 `activeTab`、`scripting` 和 `http://127.0.0.1:9998/*` 权限；不申请 `<all_urls>`。它只处理姓名、邮箱、电话、所在地、个人网站和 LinkedIn，不读取密码、文件、隐藏字段、复选框或单选框。

检测到 CAPTCHA 时扩展立即停止。它没有验证码求解、反检测、自动点击、`submit()` 或 `requestSubmit()` 代码。最终检查、验证码和提交始终由用户完成。

## 4. 恢复与故障

- OAuth state 10 分钟失效且只能使用一次；授权取消不会创建令牌。
- 令牌失效时优先使用 refresh token；刷新失败返回安全错误，不回显供应商响应或凭证。
- `0009` 迁移前生成 `data/careerpilot.db.pre-0009.bak`。失败时停止服务并从该备份恢复，不清库。
- Docker 中 SecretStore 只读，不能在页面内完成令牌持久化；使用原生 Windows 授权或在容器启动时注入 Secret。
- 预填目标必须是公开 HTTPS origin；会话不能跨站使用。

## 5. 明确不做

- 不自动提交申请，不批量海投，不绕过验证码、反爬、登录或付费墙。
- 不保存第三方 Cookie、密码或浏览器会话。
- 不用 Agent 直接操作 OAuth、浏览器 DOM 或 ORM；Stage 7 服务可脱离 Agent 独立运行。
- 不在本阶段增加常驻 Worker、多租户、SaaS 凭证托管或跨设备推送。
