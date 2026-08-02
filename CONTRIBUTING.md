# Contributing to CareerPilot

感谢参与 CareerPilot。项目处理邮件、简历和求职记录等敏感数据，因此可恢复性、来源、人工控制和最小权限优先于功能数量。

## 开发基线

- Python 3.11，Node.js 22，Windows 为首要本地环境，Linux/Docker 为发布环境。
- 后端 FastAPI + SQLAlchemy + Alembic；前端 React + TypeScript + Vite。
- 依赖必须进入对应锁文件；不要只修改根 `requirements.txt` 或安装未锁定的临时依赖。
- 运行数据只放在 `data/`；真实邮件、简历、附件、Tracker、数据库、日志和凭证不得进入 Git。

完整环境与功能说明见 [P0–P3 交付文档](docs/DELIVERY_P0_P3.md)。

## GitHub Flow

1. 从最新 `main` 创建短生命周期分支：
   - `feature/<scope>`：新功能；
   - `fix/<scope>`：缺陷；
   - `security/<scope>`：安全修复；
   - `docs/<scope>`：纯文档。
2. 一个分支只解决一个可评审主题。数据库迁移、API、前端、测试和文档可以同属一个垂直功能包。
3. 提交使用祈使语气并说明结果，例如 `Add guarded Gmail OAuth integration`。不要提交调试数据或个人凭证。
4. 推送后创建 Draft PR，填写仓库 PR 模板；CI 全绿且风险、迁移和回滚说明完整后再转为 Ready for review。
5. 至少完成一次代码评审。高风险改动必须明确检查数据迁移、权限、Secret、外部请求和人工审批边界。
6. 合并使用 squash 或项目维护者指定策略；合并后更新 `CHANGELOG.md`，发布时创建带说明的语义化标签。

## 本地验证

在仓库根目录运行：

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest .\backend\tests -q
.\.venv\Scripts\python.exe -m ruff check .\backend
cd frontend
npm.cmd run check
npm.cmd run build
npm.cmd run e2e
npm.cmd audit --audit-level=high
```

涉及 Docker 时还需从仓库根目录执行构建、健康检查和 API/Web 冒烟。提交前运行 `git diff --check`，并确认 `git status --short` 中没有 `data/`、Secret、测试报告或本地截图。

## 数据库变更

- 只允许 Alembic 前向迁移；一个迁移只完成一个明确的数据结构变化。
- 升级前保留 `data/careerpilot.db.pre-<revision>.bak`；迁移失败后从备份恢复，不清库、不静默降级。
- 新表、约束、幂等行为、旧数据迁移和重启恢复必须有集成测试。
- 不在迁移或测试中读取开发者的真实 `data/`；使用临时目录和合成数据。

## API、Agent 与外部集成

- API 位于 `/api/v1`，保持现有错误结构、幂等和 Application Service 边界。
- 外部输入（邮件、网页、JD、简历、模型输出和 OAuth 响应）均是不可信数据。
- Agent 只能调用代码内置、版本化、严格 Schema 的白名单工具；Agent 不直接操作 ORM。
- 任何业务写入都必须保留人工审批；不得实现自动投递、验证码绕过或隐藏式第三方登录。
- 新的外部数据传输必须在 UI 中说明目的、字段和接收方，并要求用户当次确认。

## Pull Request 完成定义

- 行为、API、迁移和安全边界有对应测试。
- 用户可见功能有一条浏览器或手工验收路径。
- 文档、变更记录、配置示例和回滚说明同步更新。
- Windows/Linux 测试、浏览器 E2E、安全扫描和 Docker 门禁全部通过。
- PR 不含真实个人数据、Secret、无关大文件或生成目录。

安全问题不要提交公开 Issue，按 [SECURITY.md](SECURITY.md) 私下报告。
