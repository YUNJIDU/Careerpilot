# Stage 5：求职智能功能扩展

## 定位

Stage 5 在首发的信息提取、Tracker 和 Summary 闭环稳定后，将辅助能力扩展为可独立测试的 Python 模块。具体功能进入本 Stage 时再访谈和形成详细设计。

## 已确认不属于产品方向

- 岗位发现。
- 职位推荐。
- 招聘网站聚合。
- 替用户判断是否投递、参加、接受或拒绝。

## 保留的候选扩展

### JD Intelligence

- 职责、技能、经验和学历整理。
- 必备项、加分项和关键词。
- 岗位 Summary。

### Company Research

- 官方业务、产品和技术方向。
- 公开招聘流程。
- 来源、时间和可信度。

### Resume Match

- JD 与简历证据映射。
- 技能缺口。
- 应突出项目。
- 禁止编造经历。

### OA / Interview 辅助

首发只整理公开信息。后续可以讨论：

- 练习主题。
- 模拟题。
- 模拟面试。
- 评分和训练计划。

### Review 与复盘

- 来源和事实检查。
- 用户主动记录的练习结果。
- 求职过程复盘。

## 共同边界

- 所有能力仍是辅助，不替用户决策。
- 输入输出使用明确 Schema。
- 本地/外部模型可切换。
- 外部事实保存来源和抓取时间。
- 不登录第三方内容账号，不绕过反爬和付费墙。
- 具体功能、API、评测和 UI 在进入本 Stage 时再确定。

## 开源与 Hugging Face 参考

### 笔试与面试训练

- [pipecat-ai/pipecat](https://github.com/pipecat-ai/pipecat)：实时语音和多模态对话管线，可作为后续语音模拟面试的框架参考。
- [ocbyram/Interview_Prep_Help](https://huggingface.co/ocbyram/Interview_Prep_Help)：基于 JD 和用户资料生成面试问题/示例答案的模型参考；其训练数据含合成内容，只能作为实验基线，不能视为真实面试事实。
- [anuj6316/Interview_Questions](https://huggingface.co/datasets/anuj6316/Interview_Questions)：带领域、级别和题型元数据的合成面试问题数据集，可用于问题生成与评测原型。
- [Suchi-30/job-aptitude](https://huggingface.co/datasets/Suchi-30/job-aptitude)：岗位技能到选择题的 aptitude 数据集，可用于笔试题生成 Schema 和离线评测参考。
- [AI4A-lab/RecruitView](https://huggingface.co/datasets/AI4A-lab/RecruitView)：多模态面试回答数据与心理学标注研究参考；涉及视频、声音和行为数据，必须单独审查同意、偏见、身份泄漏和适用许可。

### 简历与 JD 证据映射

- [interviewstreet/hiring-agent](https://github.com/interviewstreet/hiring-agent)：简历 PDF 到结构化 Markdown/JSON、证据化输出和本地/托管模型切换参考；CareerPilot 不采用其招聘方候选人评分目标。
- [netsol/resume-score-details](https://huggingface.co/datasets/netsol/resume-score-details)：简历—JD 匹配字段和评价维度参考；数据由模型生成，不能作为无偏真实标签。
- [med2425/resume-job-fit-merged-v1](https://huggingface.co/datasets/med2425/resume-job-fit-merged-v1)：大规模简历—JD 匹配实验数据参考；进入本 Stage 时必须复核其数据来源、合成比例和许可链。

### 明确排除

- 不采用实时隐身答题、规避录屏、规避监考或面试中秘密生成答案的开源项目。
- 模拟训练必须明确标识为练习环境，并由用户主动开始和结束。
- 评分只能基于透明量表，不得声称预测招聘结果或人格真实性。
