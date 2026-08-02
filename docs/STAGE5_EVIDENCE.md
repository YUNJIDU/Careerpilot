# P1 Stage 5 证据智能说明

## 完成范围

Stage 5 保持确定性 Service 架构，不引入 Agent。工作流依次为：

1. 保存不可变 JD 版本，并从人工正文或受 SSRF 保护的公开 URL 获取原文。
2. 结构化职责、必备条件、加分项、待遇、流程和其他条目。
3. 使用 Tavily 与公共网页获取完成公司研究。
4. 从岗位已关联的 TXT、DOCX 或 PDF 简历版本提取文本，生成 Resume–JD 证据映射。
5. 根据映射确定性生成缺口，再由用户逐项确认、要求修正或拒绝。

所有模型结果先经过本地验证，验证失败不会写入业务版本。

## 证据与决策边界

- JD 条目的引用必须逐字存在于对应 JD 原文。
- 公司事实必须引用本次实际抓取的 URL，且引文必须存在于该网页正文。
- `matched` 与 `partial` 必须引用简历原文；`missing` 禁止附带简历证据。
- 每个 JD 条目必须且只能映射一次；状态只允许 `matched / partial / missing / unknown`。
- 缺口文字只描述“当前简历是否找到证据”，不推断用户实际能力。
- 不输出候选人总分、录用概率、排名或自动决策；人工复盘记录追加保存，不覆盖 AI 版本。
- JD、网页和简历内容都视为不可信证据，内容中的 Prompt Injection 不作为指令执行。

## 数据、迁移与恢复

- `0005`：`jd_versions`，保存 JD 原文哈希、来源与结构化结果。
- `0006`：`company_research_versions`，保存公开来源、事实引文和未知项。
- `0007`：`evidence_map_versions` 与 `review_records`，保存映射版本和人工复盘。
- 每次前向迁移分别创建 `careerpilot.db.pre-0005.bak`、`pre-0006.bak` 和 `pre-0007.bak`。
- 失败恢复依赖对应迁移前备份；程序不自动降级、不删除数据库、不清空 `data/`。

## API

- `GET/POST /api/v1/applications/{id}/jd-versions`
- `POST /api/v1/jd-versions/{id}/structure-jobs`
- `GET /api/v1/applications/{id}/company-research`
- `POST /api/v1/applications/{id}/company-research-jobs`
- `GET /api/v1/applications/{id}/evidence-maps`
- `POST /api/v1/applications/{id}/evidence-map-jobs`
- `GET /api/v1/evidence-maps/{id}/gaps`
- `GET/POST /api/v1/applications/{id}/reviews`

三个模型入口都要求 `data_leaving_confirmed=true`。任务检查点只记录资源 ID、来源数量和条目数量，不保存 JD、网页、简历正文或 Secret。

## 验收门禁

- Alembic 前向迁移、逐迁移备份与重启持久化通过。
- 后端全量测试、Ruff、Windows 锁定依赖 `pip check` 通过。
- 前端 TypeScript 检查、生产构建、浏览器 E2E 通过。
- Python/npm 依赖审计、Secret 扫描和 Docker 镜像扫描通过。
- Docker 真实服务完成 JD、公司研究、证据映射、缺口分析和人工复盘的用户可见验收。

## 明确延期

- Agent Run、工具注册、预算、审批点和检查点编排属于 Stage 6。
- Gmail、Outlook、ICS、通知和表单预填属于 Stage 7。
- PostgreSQL、Worker、对象存储、租户隔离和 SaaS 属于 Stage 8。
