# 实施文档索引

更新：2026-09-05。当前执行顺序见[总体规划](../总规划/03-mvp-plan.md)，开始任务先读[交接](../EXECUTION-HANDOFF.md)、[规则](../CURRENT-POLICY.md)与[验收](../EVALUATION.md)。

## 历史 Stage 0–4 记录

以下文档仅说明既有阶段的实现背景；不得照旧测试中的归档、真源或全字段覆盖断言覆盖当前需求，也不要从 Stage 0 重新开始。

1. [Stage 0](stage-00-implementation.md)
2. [Stage 1](stage-01-implementation.md)
3. [Stage 2](stage-02-implementation.md)
4. [Stage 3](stage-03-implementation.md)
5. [Stage 4](stage-04-implementation.md)
6. [邮件闭环](stage-02-03-mail-to-excel-loop.md)
7. [Web 工作台](stage-04a-web-workspace-plan.md)
8. [Summary](stage-04b-summary-markdown-plan.md)

## 后续步骤

先核对并局部补齐当前底座，再建立脱敏评测与固定上游取用版本。按 [Stage 5](../stages/stage-05-career-intelligence-modules.md) 原四组推进，接入 [Harness](../stages/stage-06-agent-orchestration.md)，最后分别设计 [外部辅助](../stages/stage-07-external-integrations.md) 与 [发布](../stages/stage-08-deployment-and-commercialization.md)。
每步报告已实现、已验收、未通过三个状态；同一来源研究/JD/证据映射只维护一份。上游取用不改变 Excel 真源、默认建议或人工操作边界。
