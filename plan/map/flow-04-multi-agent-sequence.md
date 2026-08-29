# 流程图 4：统一 Career Assistant 时序

> 本图属于 Stage 6。第一版使用一个受控 Assistant 调用稳定 Service 和 LangGraph 子图，不预建 Multi-Agent。

```mermaid
sequenceDiagram
    participant U as 用户
    participant A as Career Assistant
    participant C as Application Core
    participant G as Stage 5 LangGraph/工具

    U->>A: 指定岗位并提出任务
    A->>C: 读取最小必要岗位、当前简历和时间线
    C-->>A: Schema 化事实与版本 ID
    A->>G: 调用 Summary、A-G 评估、简历建议或面试准备
    G-->>A: 结构化结果/interrupt/安全错误
    A-->>U: 展示来源、预算、不确定性或确认请求
    U->>A: 批准、修改或拒绝
    A->>G: 使用同一 thread_id 恢复
    G-->>A: 最终结构化结果
    A-->>U: 汇总建议，不执行投递或文件修改
```

## 边界

- Assistant 只路由已注册工具和子图。
- Application Core 是唯一业务写入口。
- Graph 状态不保存 Secret 或无关个人数据。
- 写入报告或记录必须人工确认且保持幂等。
- 只有出现可测量瓶颈时才评估 Multi-Agent。
