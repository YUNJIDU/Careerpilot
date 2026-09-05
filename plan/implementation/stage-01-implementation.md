# Stage 1：Excel Schema 与同步引擎

> 历史记录（2026-09-05 统一标记）：正文保留当时的设计、任务和验收假设，不是当前执行指令。冲突内容已由[当前规则](../CURRENT-POLICY.md)替代；按总体规划与新验收核对差距，不重做已完成阶段。

## Goal

完成 Tracker 模板、解析、校验、差异计算和安全写出；暂不绕过 Application Service 直接修改业务数据库。

## Entry

- Stage 0 Exit Gate 全部通过。
- Excel 契约与错误码已冻结。

## Work Packages

### S1.1 Tracker 模板

列：

`投递时间、公司名称、岗位、简历通过、测评、笔试、一面、二面、三面、HR 面、终面、当前阶段、截止时间、JD 链接、最近更新时间、备注`

隐藏元数据：

- workbook schema version
- stable application_id
- row version

输出示例工作簿和脱敏 fixtures。

### S1.2 Reader 与 Validator

- 只支持 `.xlsx`。
- 校验 Sheet、列、日期、长度、稳定 ID 和版本。
- 禁止宏、公式求值和外部链接执行。
- 错误精确到 Sheet/行/列。

测试：

- 正常、缺列、重复列、错误日期、超长值、重复 ID、未知版本。
- 公式单元格、损坏文件、超大文件和路径逃逸。

### S1.3 Normalizer

- Excel 行转 `TrackerRowDTO`。
- 明确空值、用户清空和未提供的区别。
- 阶段单元格保留“日期 + 结果/安排”自由文本。
- 不在 Excel 层推断求职决策。

### S1.4 Diff Engine

输入：

- Excel 快照。
- Application 统计快照。
- 上次同步基线。

输出：

- create/update/clear/noop/conflict 命令。
- 字段旧值、新值、来源、行版本。

规则：

- 用户手工修改优先。
- 系统新值不能静默覆盖用户值。
- 冲突保留双方，不在 Excel 层自行裁决。

### S1.5 Writer

- 从标准 Tracker DTO 生成工作簿。
- 冻结首行、筛选、列宽、日期格式。
- 外部文本公式注入转义。
- 使用临时文件和原子替换；文件占用时不破坏原件。
- 写出后重新读取验证。

### S1.6 Excel Job

- 定义分析、校验、差异、写入、验证检查点。
- 失败记录安全错误和恢复动作。
- Stage 1 使用内存 JobStore；Stage 2 替换为持久化实现。

## Exit Gate

1. 模板能往返读取和写出。
2. 所有单元格级错误可定位。
3. Diff Engine 覆盖 create/update/clear/conflict/noop。
4. 公式注入、路径和损坏文件测试通过。
5. 写入失败不损坏原工作簿。
6. Excel 模块不直接依赖 ORM。

## Demo

读取示例 Tracker，显示差异；修改一行后生成新工作簿；模拟占用和冲突并展示可恢复错误。
