# 流程图 4：后续 Orchestrator Multi-Agent 时序

> 2026-08-01 的 Stage 6 评测结论是不引入 Multi-Agent。本图仅保留为长期条件候选；只有单 Agent 真实出现三个以上独立分支且确定性工具无法解决时才重新设计。

```mermaid
sequenceDiagram
    participant U as "用户"
    participant O as "Orchestrator"
    participant D as "Application Data Agent"
    participant R as "Company/JD Research Agent"
    participant P as "OA/Interview Information Agent"
    participant V as "Review Agent"
    participant A as "Application Service"

    U->>O: "手动发起资料整理任务"
    O->>D: "读取最小必要的岗位事实"
    D->>A: "通过受控服务查询"
    A-->>D: "Application、阶段、来源"
    D-->>O: "结构化任务上下文"
    O->>R: "检索公司与 JD 公开信息"
    O->>P: "检索当前阶段公开笔面信息"
    R-->>O: "来源化结果"
    P-->>O: "来源化结果"
    O->>V: "检查事实、来源和阶段一致性"
    V-->>O: "通过或返回问题"
    O-->>U: "展示 Summary，不替用户决策"
```

## Agent 边界

- Orchestrator 负责任务分配、权限、预算、超时和汇总。
- Agent 使用受控工具，不直接任意修改数据库。
- Agent 只提供记录和辅助，不替用户完成求职决策。
- Agent 之间只传最小必要的 Schema 化上下文。
