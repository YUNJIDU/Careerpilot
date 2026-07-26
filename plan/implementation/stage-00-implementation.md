# Stage 0：契约、安全与工程骨架

## Goal

建立可运行但尚无业务功能的 Windows 工程骨架，冻结 Stage 1–4 共同依赖的契约、安全规则和质量门槛。

## Entry

- 框架设计总纲已批准。
- Python、Node.js、包管理器和 Windows 开发环境可用。

## Work Packages

### S0.1 仓库与许可证

计划文件：

- `LICENSE`
- `NOTICE`
- `THIRD_PARTY_LICENSES.md`
- `.gitignore`
- `.env.example`
- `README.md`

任务：

- 加入 Apache-2.0。
- 区分源码、fixtures 与运行数据；真实 `data/`、`.env`、密钥和导出物不得提交。
- 写明 Windows 原生和未来 Docker 边界。

验证：

- secret scan 不发现样例密钥。
- 许可证清单能覆盖直接依赖。

### S0.2 Backend/Frontend 骨架

计划目录：

- `backend/src/careerpilot/`
- `backend/tests/`
- `frontend/src/`
- `tests/fixtures/`
- `data/.gitkeep`

任务：

- 建立 FastAPI 应用工厂和 `/api/v1/health`。
- 建立 React/Vite 页面和类型化 API client 边界。
- 后端只监听 `127.0.0.1`，CORS 只允许本地前端。
- 建立统一配置加载，普通配置与 SecretStore 分离。

验证：

- 后端和前端可分别启动。
- 前端能显示 health 状态。
- 前端 bundle 不含秘密。

### S0.3 契约包

计划模块：

- `contracts/common.py`
- `contracts/application.py`
- `contracts/mail.py`
- `contracts/excel.py`
- `contracts/artifact.py`
- `contracts/jobs.py`
- `contracts/errors.py`

冻结：

- UUID、时区时间、枚举、分页、错误响应和 request_id。
- Application、Event、Email、Evidence、FieldProvenance、Attachment、Artifact。
- Job、Checkpoint、幂等键。
- Excel DTO、差异命令和 Schema 版本。

验证：

- JSON Schema 快照测试。
- 不兼容变更必须显式更新契约版本。

### S0.4 扩展接口

定义 Protocol/ABC：

- `MailAdapter`
- `ModelGateway`
- `SummaryProvider`
- `AttachmentParser`
- `SecretStore`
- `BackupService`
- `RestoreService`
- `DeleteService`

首发只注册内置实现；后三项只提供接口和明确的 Not Implemented 行为。

### S0.5 安全工具

计划模块：

- 路径授权与规范化。
- 日志脱敏。
- Excel 公式字符识别。
- 外部文本标记。
- 敏感字段裁剪。
- 文件类型、大小和超时策略。

测试：

- `../`、绝对路径和符号链接逃逸。
- `= + - @` 公式注入。
- 邮箱、授权码、API Key 日志泄漏。
- Prompt Injection 文本不能触发工具注册。

### S0.6 质量流水线

- Python lint、format、type check、pytest。
- TypeScript lint、type check、unit test、build。
- 依赖漏洞、许可证和 secret scanning。
- Windows 为首要 CI。

## Exit Gate

1. 空框架可在 Windows 启动。
2. health 链路通过。
3. 契约快照、扩展接口和安全测试通过。
4. 没有业务模块直接依赖具体模型或邮箱 SDK。
5. `data/`、秘密和真实用户资料不进入 Git。
6. Stage 1–4 可以引用稳定契约。

## Demo

启动 FastAPI 与 React，展示 health、配置加载、SecretStore 假实现、错误响应和安全测试。
