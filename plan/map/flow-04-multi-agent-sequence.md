# 流程图 4：Orchestrator Harness

依据：[Harness](../stages/stage-06-agent-orchestration.md)。角色为职责边界，可先以模块实现，再按收益升级独立 Agent。

```mermaid
sequenceDiagram
    participant U as 用户
    participant O as Orchestrator
    participant C as 受控事实与成果工具
    participant R as Research
    participant E as Evaluation
    participant P as Resume/Interview
    participant V as Reviewer
    U->>O: 指定岗位与任务并授权范围
    O->>C: 读取Excel基线、投递简历和已有成果
    C-->>O: 最小上下文、版本与缺口
    O->>R: 复用或补齐完整公开背景
    R-->>O: 公司/文化/市场/薪资/JD/考点与来源、未知项
    O->>E: 复用或生成既有A–G分析
    E-->>O: 有据判断与直观分数
    O->>P: 用户需要的建议或全面准备
    P-->>O: 建议/清单/故事/文字模拟结果
    O->>V: 检查证据、范围和一致性
    V-->>O: 通过或定位问题
    O-->>U: 完整结果或明确标注的部分结果
```

只调度本次请求所需模块，不因图中顺序强制运行全部能力；面试准备复用完整背景，缺少资料明确未知。共享研究不重复生成，权限和预算由 Orchestrator 限制；扩大授权范围时等待用户。失败恢复保留有效成果，不重复写入。
