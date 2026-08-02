# Stage 7：外部系统与自动化扩展

## 定位

本 Stage 保留首发核心闭环完成后的外部能力扩展。163 只读邮箱已前移到 Stage 3，不再属于后期能力。

## 已确认的候选扩展

### 更多邮箱适配器

- Gmail
- Outlook
- 其他 IMAP 邮箱

新增适配器不得修改 Application Core 和邮件提取主流程。

### 邮箱监控与提醒

- 未读邮件监控。
- 主动提醒。
- 截止时间紧急通知。
- 多渠道通知与升级。

这些不是首发职责；首发默认用户会自行查看和理解全部邮件。

### 公开信息访问扩展

- 验证码处理可以作为独立模块研究。
- 仍禁止登录第三方内容账号、绕过反爬和付费墙。
- 具体合法性、安全性和站点条款在进入本 Stage 时评估。

### 自动填表

- 优先评估并模块化接入成熟 GitHub 项目。
- 不在核心内容完成前自行重造。
- 自动提交、审批和失败恢复规则进入本 Stage 时再设计。

## 保留但尚未讨论

- 通知渠道。
- 浏览器隔离方式。
- 自动填表项目选择。
- 验证码模块边界。
- 后台任务和长期运行方式。
- 普通用户的凭证托管。

进入本 Stage 时再访谈和形成详细设计，不提前锁死实现方案。

## 自动填表与浏览器参考

- [Abhinav-Reddy-k/workday-copilot](https://github.com/Abhinav-Reddy-k/workday-copilot)：Workday 表单识别、本地 LLM、资料管理和错误恢复参考。
- [browser-use/browser-use](https://github.com/browser-use/browser-use)：通用浏览器 Agent、表单填写和工具封装参考；CareerPilot 不采用其代理、反检测或绕过站点控制能力。
- [Azoo92i/EasyApplyMax](https://github.com/Azoo92i/EasyApplyMax)：浏览器扩展中的字段映射、申请记录和本地浏览器存储参考；其高频自动申请目标不属于 CareerPilot 的产品原则。

采用任何参考前必须复核许可证、维护状态、数据流和目标网站条款。优先复用表单识别与字段映射模块，不复用自动海投和规避控制逻辑。

## 进入阶段后的详细设计（2026-08-02）

- Gmail 固定使用 Gmail API `gmail.readonly`；Outlook 固定使用 Microsoft Graph `Mail.Read`。两者使用 Authorization Code + PKCE，刷新令牌只进入 SecretStore，业务数据库仅记录连接状态和权限清单。
- 两个适配器实现现有唯一 `MailAdapter v1`，原始 MIME 继续进入现有解析、事实提取、Application Core、附件元数据与人工下载流程，不建立第二套邮件业务链。
- 提醒使用本地 SQLite 与 RFC 5545 ICS。页面读取提醒时确定性扫描未来 3 天并生成幂等站内通知；浏览器系统通知只在用户主动授权后显示。后台常驻 Worker 留在 Stage 8。
- 自动填表不接入高频投递项目，改为最小权限 Manifest V3 本地扩展：仅 `activeTab`、`scripting` 和本机 API 权限。扩展在当前标签页本地识别允许字段、展示差异，确认后只设置字段值。
- CAPTCHA 由独立检测边界处理：发现 reCAPTCHA、hCaptcha 或常见 CAPTCHA 标记即停止填值并要求用户接管；不识别、求解、绕过或上报验证码内容。
- 扩展不读取密码、隐藏字段、文件、复选框或单选框，不调用 `submit()` / `requestSubmit()`，不点击提交按钮。最终检查、验证码和提交始终属于用户。
- 不登录第三方内容账号，不绕过反爬、付费墙或站点控制，不实现自动海投、多渠道营销通知或后台长期运行。

## Exit Gate

- `0009` 迁移前自动备份，旧数据库和 Stage 0–6 数据可恢复。
- Gmail/Outlook 适配器契约、OAuth state/PKCE、令牌不落库、刷新与断开均有集成测试。
- 提醒、ICS 转义、通知幂等、HTTPS 目标限制、字段白名单、CAPTCHA 停机和禁止提交均有安全测试。
- Windows/前端检查、Linux 锁定依赖、全量后端测试、浏览器 E2E、Docker 迁移/健康/API 冒烟全部通过。
- 真实供应商验收使用用户自有测试账户；没有客户端凭证时只允许通过模拟供应商测试，不声称完成真实授权。
