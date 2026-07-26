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
