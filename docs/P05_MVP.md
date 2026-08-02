# P0.5 MVP 补齐说明

## 已完成范围

- `MailAdapter v1` 是唯一邮件协议；运行时只加载内置 `imap163` 与本地 `.eml` 适配器。
- 多个 163 邮箱账户分别保存凭证，支持启停、测试、单独同步和顺序同步。
- 原始 `.eml` 通过 Web/API 上传，以 SHA-256 命名保存，并复用既有解析、去重、任务恢复与 Tracker 同步流程。
- 邮件同步只自动保存附件元数据。PDF、DOCX、TXT、PNG、JPEG 由用户逐个批准后才读取和保存。
- 多份简历支持 PDF、DOCX、TXT 的内容寻址存储、版本管理和具体版本—岗位关联。

## 安全边界

- 邮件最大 2 MiB、附件最大 10 MiB、简历最大 5 MiB。
- 文件扩展名、MIME 与文件签名必须一致；DOCX 会检查结构、路径穿越、解压上限和宏文件。
- 宏、脚本、压缩包、恶意文件名、二进制伪装 TXT 和超限文件均拒绝。
- 保存路径只使用 SHA-256，不使用用户提供的文件名；下载名称只作为响应展示。
- `.eml`、附件和简历上传不会调用搜索、网页获取或模型服务。文件中的 Prompt Injection 只按不可信原始内容保存。
- 邮箱授权码和 API 密钥不写入数据库、任务检查点或 API 响应。

## 数据与 API

Alembic `0004` 新增：

- `attachments`：附件来源、元数据、批准状态和内容哈希。
- `resume_versions`：简历文档 ID、版本、文件元数据和内容哈希。
- `application_resumes`：具体简历版本与申请岗位的关联。

主要接口：

- `GET /api/v1/attachments?application_id=...`
- `POST /api/v1/attachments/{id}/approve`
- `GET /api/v1/attachments/{id}/content`
- `GET /api/v1/resumes`
- `POST /api/v1/resumes`
- `PUT /api/v1/resume-versions/{version_id}/applications/{application_id}`
- `GET /api/v1/resume-versions/{version_id}/content`

## 迁移、恢复与回滚

- 启动时仅执行 Alembic 前向迁移；已有 `0003` 数据库会先生成 `careerpilot.db.pre-0004.bak`。
- 内容文件使用哈希去重并原子替换，重复上传不会覆盖现有内容。
- 容器的数据目录继续绑定宿主机 `data/`，重启或换镜像不会丢失邮箱、样本、附件、简历与关联。
- 如新镜像验收失败，停止新容器并重新启动保留的旧容器；数据库可由迁移前备份恢复。项目不会自动降级或清库。

## 明确延期

- 简历解析、JD 结构化、证据映射与缺口分析属于 Stage 5。
- Agent 编排、工具调用与人工审批记录属于 Stage 6。
- Gmail、Outlook、提醒、表单预填和验证码人工接管属于 Stage 7。
- 本阶段不评分、不预测录用率、不自动投递、不执行附件内容。
