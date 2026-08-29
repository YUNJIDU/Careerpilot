# Stage 6：Agent 与 Orchestrator Multi-Agent

## 当前已确认的方向

首发版本采用一个主辅助 Agent，调用稳定的普通工具模块。核心业务能力必须能够脱离 Agent 独立运行、测试和复用。

当单 Agent 和确定性流程出现明确编排需求后，Multi-Agent 采用 Orchestrator 协作模式。

## Orchestrator 职责

- 判断任务类型并分配专用 Agent。
- 控制工具权限、预算、超时和上下文范围。
- 汇总结构化结果。
- 记录任务步骤、来源和失败。
- 确保 Agent 只提供记录和辅助，不替用户做求职决策。

## 可能的专用 Agent

以下划分仅保留为候选，进入本 Stage 时再根据已稳定模块细化：

- Mail Extraction Agent
- Application Data Agent
- Company/JD Research Agent
- OA Information Agent
- Interview Information Agent
- Review Agent

## 工具与数据边界

- Agent 通过受控 Python Service 或 Function Calling 使用工具。
- 专用 Agent 不直接任意修改业务数据库。
- Agent 之间传递最小必要的 Schema 化任务和结果。
- 业务事实仍保存在 Application Core。
- 外部内容、工具返回和 Agent 输出均视为不可信数据。
- MCP 只包装稳定且确需跨进程复用的工具。

## 后续再设计

- 最终 Agent 划分。
- 是否需要检查点、恢复和长任务队列。
- 人类介入点。
- 长短期记忆。
- Agent 评测集和成本预算。
- Multi-Agent UI。

这些问题不在首发范围内，进入本 Stage 时再单独访谈并形成详细 Markdown。

## Orchestrator 框架参考

- [pydantic/pydantic-ai](https://github.com/pydantic/pydantic-ai)：Python、类型安全结构化输出、模型无关、工具调用和评测能力，与现有 Pydantic/FastAPI 方向相容；可作为单 Agent 的优先评估对象。
- [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph)：持久化、有状态、可恢复的长任务与图编排参考，适合后期复杂 Orchestrator。
- [langchain-ai/langgraph-supervisor-py](https://github.com/langchain-ai/langgraph-supervisor-py)：中心 Supervisor/Orchestrator 管理专用 Agent 的模式参考；项目自身建议多数场景直接采用工具式 supervisor pattern，因此不能机械引入该封装库。
- [crewAIInc/crewAI](https://github.com/crewAIInc/crewAI)：Crew/Flow 协作和角色化 Agent 的对照方案。

进入本 Stage 时应基于真实编排需求做小型验证，再在 Pydantic AI、LangGraph、CrewAI 或自定义 Orchestrator 中选型，不因作品集展示而强行引入多个框架。
