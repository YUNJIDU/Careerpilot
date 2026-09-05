# CareerPilot Stage 0–1 执行设计

> 历史记录（2026-09-05 统一标记）：正文保留当时的设计、任务和验收假设，不是当前执行指令。冲突内容已由[当前规则](../../../plan/CURRENT-POLICY.md)替代；按总体规划与新验收核对差距，不重做已完成阶段。

日期：2026-07-26

状态：待用户审核

## 1. 目标与范围

在 `E:\Master\CareerPilot\careerpilot` 建立 CareerPilot 的最小可运行工程，并在同一执行循环中按 Gate 顺序完成：

1. Stage 0：契约、安全与工程骨架。
2. Stage 1：Excel Schema、解析、校验、标准化、差异计算、安全写出和内存 Job。

Stage 0 的 Exit Gate 未全部通过时，不进入 Stage 1。Stage 1 不实现 ORM、SQLite 业务表或数据库写入，也不实现真实邮箱、信息提取、Summary、Docker 和后续业务页面。

## 2. 实施方式

采用单一项目目录和逐 Work Package 验证：

```text
创建项目目录
  → Stage 0 失败测试/契约测试
  → 最小实现
  → Stage 0 全量检查与 Demo
  → 验证 Exit Gate
  → Stage 1 失败测试
  → 最小实现
  → Stage 1 全量检查与 Demo
  → 验证 Exit Gate
```

任一检查失败时，只修复当前 Stage 的失败，不提前铺设后续 Stage。

## 3. 工程结构

```text
careerpilot/
├─ backend/
│  ├─ src/careerpilot/
│  │  ├─ api/
│  │  ├─ contracts/
│  │  ├─ excel/
│  │  ├─ extensions/
│  │  └─ security/
│  ├─ tests/
│  └─ pyproject.toml
├─ frontend/
│  ├─ src/
│  └─ package.json
├─ tests/fixtures/
├─ data/.gitkeep
├─ .env.example
├─ .gitignore
├─ LICENSE
├─ NOTICE
├─ THIRD_PARTY_LICENSES.md
└─ README.md
```

只创建当前 Stage 实际使用的文件；目录可以按实现需要合并，避免单实现接口和空占位文件。

## 4. Stage 0 设计

### 4.1 Backend 与 Frontend

- FastAPI 应用工厂提供 `/api/v1/health`。
- 默认主机为 `127.0.0.1`，CORS 仅允许本地前端。
- React/Vite 页面通过类型化 client 显示 health。
- 普通配置与 `SecretStore` 分离，前端和配置对象不承载秘密。

### 4.2 契约与扩展

- 使用 Pydantic 冻结 UUID、时区时间、枚举、错误、Application、Mail、Evidence、Artifact、Excel、Job 和 Checkpoint 契约。
- 使用 Python Protocol 定义首发扩展边界。
- Backup、Restore 和 Delete 仅返回明确的未实现错误。
- JSON Schema 快照用于发现不兼容修改。

### 4.3 安全

- 路径必须解析在授权数据目录内。
- 日志输出前脱敏邮箱、授权码和 API Key。
- Excel 外部文本识别 `= + - @` 公式前缀。
- 外部文本始终作为不可信数据，不触发工具或注册行为。
- 文件策略限制类型、大小和处理时限。

### 4.4 Stage 0 验证

- 后端测试、类型检查和 lint。
- 前端类型检查、单元测试和构建。
- health、契约快照、扩展接口和安全回归测试。
- Windows 启动 Demo。
- 检查 `data/`、秘密和真实资料未进入版本控制范围。

## 5. Stage 1 设计

### 5.1 Tracker 与元数据

- 主表固定为计划中的 16 个中文列。
- 隐藏元数据保存 workbook schema version、stable application ID 和 row version。
- 仅支持 `.xlsx`，不接受宏工作簿。

### 5.2 Reader、Validator 与 Normalizer

- Reader 使用 `openpyxl` 的非公式求值模式读取。
- Validator 报告 Sheet、行、列和稳定错误码。
- 校验缺列、重复列、日期、长度、重复 ID、版本、大小、损坏文件和授权路径。
- Normalizer 明确区分未提供、空值和用户清空；阶段文本不作求职决策推断。

### 5.3 Diff Engine

输入为 Excel 快照、Application 统计快照和上次同步基线；输出 create、update、clear、noop 或 conflict 命令。

- 用户修改优先。
- 系统值不得静默覆盖用户值。
- 冲突同时保留双方值和版本信息，不在 Excel 层裁决。

### 5.4 Writer 与 Job

- Writer 设置冻结首行、筛选、列宽和日期格式。
- 外部文本写入前防公式注入。
- 写入临时文件，重新读取验证成功后原子替换目标文件。
- 失败不破坏现有工作簿。
- Stage 1 使用内存 JobStore，记录分析、校验、差异、写入和验证检查点。

### 5.5 Stage 1 验证

- 模板往返读写。
- 单元格级错误定位。
- 五类差异命令。
- 公式注入、路径逃逸、损坏文件和超大文件。
- 文件占用或替换失败时原文件保持完整。
- Excel 包不依赖 ORM。
- Windows Demo 展示读取、差异、修改写出、冲突和可恢复错误。

## 6. 错误处理与完成条件

- 测试失败：停留在当前 Work Package，修复后重跑相关测试。
- 环境依赖缺失：只安装计划已批准的直接依赖，并更新许可证清单。
- Stage Gate 失败：报告失败项，不进入下一 Stage。
- 完成时提供修改文件、命令、测试结果、Demo 结果、逐项 Exit Gate 和剩余风险。

## 7. 已知环境问题

`E:\Master\CareerPilot\.git` 当前是空目录，Git 未将该路径识别为仓库。因此本设计可以保存，但在 Git 仓库被初始化或恢复前无法提交。实施不会擅自删除或重建该 `.git` 目录。
