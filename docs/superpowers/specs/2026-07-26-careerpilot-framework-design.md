# CareerPilot 首发框架设计总纲

> 历史记录（2026-09-05 统一标记）：正文保留当时的设计、任务和验收假设，不是当前执行指令。冲突内容已由[当前规则](../../../plan/CURRENT-POLICY.md)替代；按总体规划与新验收核对差距，不重做已完成阶段。

日期：2026-07-26

状态：已批准（用户于 2026-07-26 确认）

## 1. 产品定位

CareerPilot 是辅助求职 Agent，不是替用户完成求职的全权 Agent。

优先顺序：

1. 服务项目作者本人。
2. 服务同专业、懂 AI、能本地部署的技术用户。
3. 同时形成 AI/Agent 作品集与研究案例。
4. 核心成熟后演进为面向普通用户的云端 Web/SaaS。

默认用户会自行查看和理解全部求职邮件，并负责所有决定。CareerPilot 只负责第三方记录、信息整理和辅助。

## 2. 首发闭环

```text
本地 Web 配置
  → 用户手动同步 163/本地邮件样本
  → 提取客观求职信息
  → 保存数据库、来源、证据和必要附件
  → 双向同步 Excel Tracker
  → 查看每个 Application 详情
  → 用户手动生成公司/JD/笔试/面试 Summary
  → Web 或 Markdown 查看
```

首发不包含岗位发现、职位推荐、提醒、模拟训练、自动填表、Multi-Agent 和 SaaS 商业能力。

## 3. 技术与部署

- Backend：Python、FastAPI、Pydantic。
- Frontend：React、TypeScript、Vite。
- Persistence：SQLAlchemy、SQLite、Alembic。
- Excel：openpyxl。
- 首要环境：Windows 原生。
- 第二环境：Docker。
- 用户模型：单用户，多简历，多邮箱账户。
- 数据目录：`data/`。
- 开源策略：Apache-2.0 Open Core。

Windows 和 Docker 使用相同业务逻辑与 Schema。核心代码不得依赖 Windows 专属路径或 GUI 能力。

## 4. 架构

```text
React/Vite
    ↓ /api/v1
FastAPI
    ├─ Application Core
    ├─ Mail + Extraction
    ├─ Excel Sync
    ├─ Documents + Attachments
    ├─ Summary
    ├─ ModelGateway
    ├─ Agent Tools
    ├─ SecretStore
    ├─ Job/Checkpoint
    └─ Versioned Extensions
          ↓
SQLite + data/ + Excel + Markdown
```

### 4.1 核心边界

- API 只调用应用服务，不直接操作数据库。
- Application Core 保存事实、来源、用户值和历史。
- Extraction 只输出客观字段和证据，不作求职决策。
- Excel 只负责映射和同步，不拥有业务规则。
- Agent 组合工具，不复制业务逻辑。
- 前端不直接访问 SQLite、文件系统和凭证。
- 商业模块只能通过版本化接口连接核心。

### 4.2 扩展

从首版定义 MailAdapter、ModelGateway、Summary Provider、Attachment Parser 和未来表单适配器接口。

首发只加载内置适配器，不开放任意第三方插件。未来插件生态需要权限声明、最小授权、签名、可信来源、沙箱、兼容和撤销机制。

### 4.3 Open Core

开源：

- Application Core 与数据契约。
- Excel、邮箱、模型和 Summary 接口。
- 本地 Web。
- Agent 工具接口。
- 扩展规范、安全测试和迁移机制。

只留接口、不实现：

- 支付。
- 配额。
- 运营系统。
- 托管凭证。
- 商业专属集成。
- Backup/Restore/Delete 的完整功能。

## 5. 首发功能

### 5.1 设置

- 配置 163 邮箱和本地样本。
- 选择本地或云端模型。
- 配置数据、Excel 和文档路径。
- 显示数据是否离开本机。

### 5.2 Tracker

- 本地 Web 查看。
- Excel 双向同步。
- 用户修改优先。
- 新邮件信息不得静默覆盖用户值。
- 阶段单元格使用“日期 + 结果/安排”。

### 5.3 邮件

- 默认手动同步。
- 可选定时同步，默认关闭。
- 读取收件箱指定时间范围。
- 保存元数据、结构化结果、证据片段和哈希。
- 默认不长期保存完整 MIME 和正文。
- 必要附件经用户同意后下载。

### 5.4 文档与 Summary

- 每个 Application 独立 Markdown。
- 用户手动触发公司、JD、笔试和面试公开资料整理。
- 保存来源、抓取时间、版本和不确定性。
- 禁止登录第三方内容账号、绕过反爬和付费墙。

## 6. 数据与版本

- 项目遵循语义化版本。
- API 从 `/api/v1` 开始。
- 数据库从首版使用 Alembic。
- Excel 包含 Schema 版本和稳定 Application ID。
- 扩展协议独立版本化。
- 破坏性升级必须提供迁移，不要求删除 `data/`。

## 7. 凭证

- Windows 使用 Credential Manager。
- Docker 使用环境变量或 secret 文件。
- `.env` 仅用于开发并被 Git 忽略。
- SQLite、Excel、Markdown、日志、前端和构建产物不得保存明文秘密。
- React 只调用 FastAPI，不持有邮箱或模型密钥。
- SaaS 托管凭证只保留 SecretStore 接口。

## 8. Job 与 Checkpoint

邮箱、Excel、附件、Summary 和迁移任务统一生成 `job_id`。

任务保存：

- 类型和状态。
- 当前步骤和已完成步骤。
- 检查点。
- 输入引用和处理范围。
- 脱敏错误码与说明。
- 是否可重试和恢复建议。
- 重试次数。
- 处理器和 Schema 版本。

恢复规则：

- 只有成功提交的事务推进检查点。
- 邮件按成功处理的单封邮件恢复。
- Excel 先计算差异，再以事务写入。
- 附件按文件隔离。
- Summary 按获取、提取、来源整理和 Markdown 生成分步恢复。
- 迁移失败立即停止。
- 恢复与重新开始均复用幂等键。
- 用户任务记录与开发日志分离。

## 9. 安全

- 邮箱只读。
- 本地 Web 默认监听 `127.0.0.1`。
- CORS 仅允许本地前端。
- 邮件、附件、网页、模型输出、插件和依赖均为不可信输入。
- HTML 不加载远程资源。
- Prompt Injection 不能改变指令或触发工具。
- 附件限制类型、大小、数量、路径和时间；不执行宏、脚本和压缩包。
- 文件必须位于授权 `data/` 子目录。
- Excel 防公式注入。
- 云模型调用前裁剪非必要个人信息。
- 日志脱敏。
- 外部任务具备成本、大小、超时和并发限制。
- Hugging Face 模型优先安全权重格式，默认禁止远程自定义代码。
- 依赖锁定并执行漏洞、许可证和 secret scanning。

## 10. 失败处理

- 邮箱失败不推进游标。
- 单封邮件失败不阻塞批次。
- 模型失败或 Schema 错误时字段留空。
- Excel 失败不覆盖原文件。
- 数据库失败事务回滚。
- 附件失败保留引用和失败状态。
- Summary 失败保留旧版本。
- 迁移失败保留原数据库并停止启动。
- Web 显示进度、停止位置、原因和恢复操作。

## 11. 最低质量门槛

- 单元测试：模型、来源、冲突、安全规则。
- 集成测试：SQLite、Excel、MailAdapter、ModelGateway。
- 端到端冒烟：FastAPI、React、样本邮件、Excel。
- 安全回归：公式注入、路径穿越、恶意附件名、Prompt Injection、敏感日志。
- 固定脱敏 fixtures 和模型桩。
- Python/TypeScript 静态和格式检查。
- 依赖漏洞扫描与 secret scanning。
- Windows CI/验收优先，Docker 构建验证其次。

## 12. 后续边界

后续可加入笔试训练、模拟面试、自动填表、复盘、提醒、更多邮箱和 Orchestrator Multi-Agent。具体顺序、产品形态和实现细节进入对应 Stage 时再讨论。

面向普通用户时演进为云端 Web/SaaS。本地版届时继续维护、成为社区版或被 SaaS 替代，暂不决定。
