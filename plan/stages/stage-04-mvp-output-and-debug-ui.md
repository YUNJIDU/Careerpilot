# Stage 4：本地 Web、岗位文档与 Summary

## 目标

完成首发用户闭环：用户通过本地 Web 操作邮件同步、Tracker、岗位详情和手动 Summary，并在 Web 或 Markdown 中查看结果。

## WBS

### 4.1 本地 Web

- 邮箱、模型和本地路径配置。
- 手动同步和同步结果。
- Tracker 查看。
- Application 详情和邮件时间线。
- 证据与必要附件。
- Excel 双向同步。
- 手动生成或更新 Summary。
- Markdown 查看和打开。

具体页面布局在进入本 Stage 时单独设计。

### 4.2 每个岗位一份 Markdown

每个 Application 独立保存：

- 公司和岗位信息。
- JD 原文引用与摘要。
- 申请时间线。
- 邮件证据引用。
- 附件链接。
- 笔试公开信息与来源。
- 各轮面试公开信息与来源。
- Summary 时间和版本。

同一公司通用资料可以缓存复用，不同岗位不能混成同一份文档。文档更新不静默删除旧时间线。

### 4.3 手动 Summary

用户在具体 Application 上主动触发后，才允许联网检索和模型调用。

输出：

- 公司公开信息。
- 岗位与 JD 摘要。
- 与当前阶段相关的公开笔试信息。
- 与当前轮次相关的公开面试信息。
- 来源、抓取时间和不确定性。

首发不生成模拟题、模拟面试、评分或训练计划。

Summary 任务按“资料获取、内容提取、来源整理、生成 Markdown”保存检查点。失败时保留旧 Summary 和已成功且未过期的中间结果，允许从断点继续。

### 4.4 公开资料边界

- 只访问无需登录的公开信息。
- 禁止登录第三方内容账号。
- 禁止绕过反爬和付费墙。
- 验证码处理留作后续扩展。
- 具体来源、抓取和质量策略在本 Stage 开始前细化。

### 4.5 模型与隐私

- 支持本地模型与云模型切换。
- 技术用户可选择完全本地运行。
- 对外发送前裁剪非必要个人信息。
- Web 明确显示当前操作是否会让数据离开本机。
- 模型输出经过 Schema 和安全处理。

## 首发端到端验收

```text
本地 Web 配置
  → 163/样本邮件同步
  → 客观信息提取
  → 数据库与证据
  → Excel Tracker
  → Excel 用户修改回写
  → Application 详情
  → 用户手动生成 Summary
  → Markdown/Web
```

Stage 0–4 完成即形成可交付给首批技术用户的版本。

### 4.6 任务历史与恢复

- 显示邮箱、Excel、附件、Summary 和迁移任务。
- 显示进度、当前步骤、脱敏错误、是否可重试和建议操作。
- 支持从断点继续或安全重新开始。
- 普通技术日志与用户任务记录分离。

## 开源参考

- [Gsync/jobsync](https://github.com/Gsync/jobsync)：本地 Web Tracker、岗位详情、自托管和本地/云模型切换体验参考。
- [unclecode/crawl4ai](https://github.com/unclecode/crawl4ai)：公开网页转 LLM-friendly Markdown、缓存和可控抓取参考。只使用普通公开页面能力，不采用代理升级、反检测或绕过站点控制的功能。
- [microsoft/markitdown](https://github.com/microsoft/markitdown)：JD、PDF/DOCX 等本地材料转换为 Markdown 的候选工具。

这些项目是设计蓝本，不预先决定 Stage 4 的 Web 框架和最终抓取实现。
