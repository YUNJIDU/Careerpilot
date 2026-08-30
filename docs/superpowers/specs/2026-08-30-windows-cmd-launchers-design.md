# CareerPilot Windows CMD 启停设计

日期：2026-08-30

## 目标

在项目根目录提供 `启动CareerPilot.cmd` 和 `关闭CareerPilot.cmd`，供 Windows 用户双击启动或关闭 CareerPilot。

## 设计

- 启动 CMD 只调用现有 `start-careerpilot.ps1`，继续复用依赖、端口、健康检查、日志和欢迎页逻辑。
- `start-careerpilot.ps1` 在前后端就绪后，将实际监听 `9998`、`9999` 的 PID 写入 `data/careerpilot-processes.json`。
- 关闭 CMD 只读取该 PID 文件并终止对应进程树，然后删除 PID 文件。
- PID 缺失、进程已退出或重复关闭时给出中文提示并安全结束。
- 不按端口盲目终止进程，不关闭浏览器，不增加常驻服务或第三方依赖。

## 验收

1. 双击启动文件后，前后端就绪并打开欢迎页。
2. 重复启动不会产生第二组服务。
3. 双击关闭文件后，`9998` 和 `9999` 不再监听。
4. 重复关闭不会报破坏性错误。
5. 无 PID 文件时不会终止其他程序。
