# Stage 6：统一 Career Assistant

## 定位

Stage 6 是第五组能力：在 Stage 5 四组 Service、Graph 和 Agent 已稳定后，提供一个统一用户入口。第一版是受控单 Assistant/Orchestrator，不构建多个角色互相对话的 Multi-Agent 系统。

## 职责

- 识别请求属于 Summary/岗位评估、简历优化建议或面试准备。
- 将任务路由到稳定 Service、LangGraph 子图或受控工具。
- 只读取当前岗位所需的最小上下文。
- 汇总结构化结果，保留来源、不确定性和各子图状态。
- 管理模型、工具权限、预算、超时、取消、失败恢复和人工确认。
- 可以提出明确建议，但不替用户投递、发送邮件、修改简历或接受/拒绝岗位。

## LangGraph 结构

```text
用户请求
  → 意图和岗位范围校验
  → 选择一个已注册工具或子图
  → 执行/恢复
  → 必要时 interrupt 等待用户
  → 结果复核
  → 汇总展示
```

Graph 状态只保存任务 ID、Application ID、Resume Version ID、结构化中间结果、来源引用、预算和审批状态，不保存凭证或不必要的邮件正文。

## 初始工具

- 读取岗位事实、时间线和当前简历事实；
- 读取/生成 Summary；
- 运行 A–G 岗位评估；
- 生成简历优化建议；
- 生成面试准备材料；
- 查询任务状态和安全错误。

Assistant 不执行任意 Shell、SQL、Python、浏览器脚本或文件路径，不直接操作 ORM。

## 人工确认

数据将发送给外部模型、开始新的高成本研究、保存报告/准备计划/复盘，或将生成文本写入业务记录时必须 interrupt。只读查询和已批准任务恢复可以继续。所有副作用必须幂等。

## 明确暂不做

- Multi-Agent、角色会议或自由委派；
- 长期自主运行或后台主动唤醒；
- 任意插件、Shell、SQL、代码执行；
- 自动修改岗位、Excel 或简历文件；
- 自动投递、发信或提交表单；
- 跨岗位读取未经用户指定的数据。

只有单 Assistant 出现可测量的上下文、成本、并发或专业评测瓶颈时，才评估拆分独立 Agent。

## Multi-Agent 演进路线

以下专用 Agent 都属于允许建设的正式方向，不是被排除的功能：

- `Research Agent`：公司、岗位、市场、招聘流程和考点研究；
- `Evaluation Agent`：A–G 分析、证据映射、1–5 分评分和建议；
- `Resume Agent`：简历修改建议和可复制文本，不修改简历文件；
- `Interview Agent`：准备主题、故事映射、文字模拟和透明反馈；
- `Reviewer Agent`：事实、引用、证据等级、安全和输出一致性复核；
- `Career Assistant`：顶层 Orchestrator，负责路由、权限、预算、恢复、人工确认和结果汇总。

Stage 5 的 Service、Schema 和 LangGraph 子图必须保持可独立运行，使它们以后可以直接成为专用 Agent 的工具或子图，无需重写业务核心。升级可以逐个发生，不要求一次拆出全部 Agent。

## 接手开发决策门槛

本计划描述技术路线和候选能力，不是看到条目后立即编码的任务清单。接手者在新增或拆分 Agent 前必须先记录：

1. 真实用户需求和具体使用场景；
2. 当前 Service、LangGraph 子图或单 Assistant 为什么不能满足；
3. 独立 Agent 能带来的可验证收益；
4. 输入、输出、数据权限、人工确认点和失败边界；
5. 能证明功能可用的端到端验收场景。

没有上述证据时继续使用单 Orchestrator 调用模块。禁止只完成页面、接口、Agent 名称或演示流程，却没有可用的核心业务闭环。

[`santifer/career-ops`](https://github.com/santifer/career-ops) 可作为 A–G 分析、评分规则、Prompt 约束和事实边界参考。CareerPilot 选择性复用这些业务思路，不机械复制其 CLI、Markdown 数据源、Node 运行时或完整工程结构；复用实质性内容时保留 MIT 许可证和署名。

## 完成门槛

- 固定任务集覆盖正确/错误路由、未知请求、预算耗尽、取消、恢复和审批。
- 验证工具最小权限、跨岗位隔离、Secret 拒绝和 Prompt Injection。
- 所有 Stage 5 能力仍可脱离 Assistant 独立运行。
