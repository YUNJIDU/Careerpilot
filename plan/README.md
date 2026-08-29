# CareerPilot 规划索引

更新时间：2026-08-29

新对话开始实施时，先阅读：[执行交接](EXECUTION-HANDOFF.md)。

## 已确认的产品定位

CareerPilot 是辅助求职 Agent，不是替用户完成求职的全权 Agent。先服务项目作者本人和能够本地部署的 AI 技术用户，开发过程同时满足作品集与研究展示需求，核心闭环稳定后再考虑普通用户产品化。

开源策略采用 Open Core：本地核心框架开源，未来 SaaS 商业能力只保留接口边界，当前不实现。

首发框架基线：

- Windows 原生优先跑通；Docker、安装包和自动更新在核心功能完善后处理。
- 单用户，可管理多份简历和多个邮箱账户。
- Python/FastAPI + React/TypeScript/Vite + SQLite。
- Apache License 2.0。
- 内置适配器优先；第三方插件生态后置。

首发闭环：

```text
本地 Web 配置邮箱
  → 用户手动同步
  → 提取客观求职信息
  → 保存数据库和邮件证据
  → 双向同步 Excel Tracker
  → 查看岗位详情
  → 用户手动生成公司/JD/笔试/面试 Summary
  → Web 页面或 Markdown 查看结果
```

## 总体文档

1. [开源项目、框架与模型参考](总规划/01-open-source-reference.md)
2. [长期产品愿景](总规划/02-long-term-vision.md)
3. [首发版本计划](总规划/03-mvp-plan.md)
4. [Stage、服务与 API 分布标准](stages/stage-api-standards.md)
5. [首发框架设计总纲](../docs/superpowers/specs/2026-07-26-careerpilot-framework-design.md)

## 阶段拆分

1. [Stage 0：标准、数据契约与安全基线](stages/stage-00-standards-and-security.md)
2. [Stage 1：本地数据底座与 Excel 双向同步](stages/stage-01-excel-bootstrap.md)
3. [Stage 2：Application 核心数据库](stages/stage-02-application-core.md)
4. [Stage 3：邮箱同步与客观信息提取](stages/stage-03-core-processing-pipeline.md)
5. [Stage 4：本地 Web、岗位文档与 Summary](stages/stage-04-mvp-output-and-debug-ui.md)
6. [Stage 5：求职智能、A–G 评估、简历建议与面试准备](stages/stage-05-career-intelligence-modules.md)
7. [Stage 6：统一 Career Assistant](stages/stage-06-agent-orchestration.md)
8. [Stage 7：外部自动化与人工确认辅助](stages/stage-07-external-integrations.md)
9. [Stage 8：生产部署与商业化](stages/stage-08-deployment-and-commercialization.md)

## Sprint

1. [首发 Sprint 路线](mvp-sprint-roadmap.md)
2. [Sprint 1：标准、Excel 与 Application Core](sprint-01-foundation-and-core.md)
3. [Stage 0–4 详细实施计划](implementation/README.md)

## 流程图

1. [WBS 开发顺序](map/flow-00-wbs-development-order.md)
2. [整体系统框架](map/flow-01-overall.md)
3. [邮件到 Tracker](map/flow-02-mail-to-tracker.md)
4. [阶段 Summary 路由](map/flow-03-stage-routing.md)
5. [统一 Career Assistant 时序](map/flow-04-multi-agent-sequence.md)

## 当前明确不做

- 岗位发现、职位推荐或招聘网站聚合。
- 替用户执行申请、参加、接受或拒绝；系统可以给出有证据的评分和建议。
- 首发版本中的模拟题、模拟面试、自动评分和训练计划。
- 首发版本中的未读监控、主动提醒和紧急通知。
- 登录第三方账号、绕过反爬或付费墙。
- 首发版本中的自动填表、自动投递和自动提交。
- 在单一 Career Assistant 已能完成任务时引入 Multi-Agent。

## 推荐阅读顺序

先以 Stage 0–4 为稳定基线，再完成 Stage 4B+ Summary 考点情报、Stage 5
四组求职智能和 Stage 6 单一 Career Assistant。Stage 7 接入外部辅助，Stage
8 在核心功能完善后再做部署与产品化；不提前搭建 Multi-Agent 或云基础设施。
