# Stage 3：邮箱同步与客观信息提取

## Goal

实现本地样本与 163 IMAP 的统一只读同步，将客观求职信息、证据和必要附件安全写入 Application Core，并可断点恢复。

## Entry

- Stage 2 Exit Gate 全部通过。
- MailAdapter、SecretStore、Job 和 Extraction 契约稳定。

## Work Packages

### S3.1 标准邮件模型

- message_id、account_id、folder、sender、subject、sent_at。
- sanitized_text、attachment metadata、raw_hash。
- 不默认持久化完整 MIME/正文。

### S3.2 FixtureMailAdapter

- 支持 `.eml` 和 JSON。
- 固定排序、分页、游标、失败注入。
- fixtures 全部脱敏。

先用该适配器完成全部集成和安全测试。

### S3.3 WindowsSecretStore 与 163 Adapter

- Windows Credential Manager 存取授权码。
- IMAP SSL、只读文件夹、时间窗口、分页、超时、重试和限速。
- 不发送、删除、移动或标记服务器邮件。
- 连接测试不泄露授权码。

### S3.4 MIME 与 HTML 安全清洗

- text/plain 优先，HTML 转安全文本。
- 不加载远程图片、CSS、脚本和链接。
- 解码异常隔离。
- 大小、嵌套和解析时间限制。

### S3.5 求职邮件筛选与提取

流水线：

1. 邮件头/规则初筛。
2. 结构化提取公司、岗位、阶段、日期、截止时间、链接和明确要求。
3. Schema 与业务规则验证。
4. 保存 evidence span 和处理器版本。

规则优先；模型通过 ModelGateway。失败或不明确字段留空。

### S3.6 Application 关联

- 使用明确公司、岗位、线程、时间和链接信息关联。
- 不确定时不得覆盖其他岗位。
- 新建或更新都通过 Application Service。
- 用户值优先。

### S3.7 附件

- 只读取 metadata 并识别疑似必要附件。
- Web/API 明确授权后下载。
- 白名单、大小、哈希、路径和超时。
- 不执行宏、脚本和压缩包。
- 解析器失败不阻塞邮件批次。

### S3.8 Mail Sync Job

检查点：

- account
- folder
- time window
- page/cursor
- last committed message_id
- processed/failed counts

单封事务成功后推进；失败隔离并继续，连接级失败停止并可恢复。

### S3.9 API 与测试

- mail accounts
- connection test
- mail sync jobs
- attachment approval/download
- job resume/restart

测试：

- 重复邮件、Message-ID 缺失哈希。
- 连接中断、超时、错误编码和恶意 HTML。
- Prompt Injection、跟踪像素、恶意附件名。
- 进程重启后恢复。

## Exit Gate

1. Fixture 与 163 适配器通过同一契约测试。
2. 同一邮件重复同步不重复写入。
3. 客观字段、来源和证据可回溯。
4. 用户值不被覆盖。
5. 邮箱、单封邮件和附件失败均可解释和恢复。
6. 未发生服务器写操作。

## Demo

在 Windows Web/API 手动同步样本和 163；展示 Excel 更新、证据、必要附件授权，以及连接中断后的断点继续。
