# Agent Interview

面向 Agent 工程学习与面试实践的示例仓库，通过可运行代码理解协议、工具调用和程序之间的协作。

当前已收录一个模块：**Java 编写的模拟 Google 查询 MCP**。它展示真实的 MCP 进程通信，搜索结果来自固定的本地模拟数据。

## 当前模块

| 模块 | 学习内容 | 入口 |
| --- | --- | --- |
| 模拟 Google 查询 MCP | Host / Client / Server 分工、初始化、工具发现、参数描述、工具调用与错误处理 | [模块 README](mcp/mcp%20demo%E5%AE%9E%E8%B7%B5/README.md) |

## 目录导航

以下链接均指向仓库中已有的文件或目录。

| 路径 | 内容与用途 |
| --- | --- |
| [mcp/mcp demo实践/](mcp/mcp%20demo%E5%AE%9E%E8%B7%B5/) | MCP 教学模块根目录，包含源码、讲义、构建产物和验证记录 |
| [README.md](mcp/mcp%20demo%E5%AE%9E%E8%B7%B5/README.md) | 模块说明、运行方法、教学解释与实践入口 |
| [docs/tutorial.md](mcp/mcp%20demo%E5%AE%9E%E8%B7%B5/docs/tutorial.md) | 完整讲义：原理、消息结构、代码阅读、断点与练习 |
| [src/demo/](mcp/mcp%20demo%E5%AE%9E%E8%B7%B5/src/demo/) | 四个 Java 类，职责见下表 |
| [dist/](mcp/mcp%20demo%E5%AE%9E%E8%B7%B5/dist/) | 已编译的 `mock-google-mcp.jar`，可用于运行教学客户端或服务端 |
| [verification/](mcp/mcp%20demo%E5%AE%9E%E8%B7%B5/verification/) | 现有构建记录、进程交互日志、黑盒报告与 SDK 互操作报告 |
| [build.ps1](mcp/mcp%20demo%E5%AE%9E%E8%B7%B5/build.ps1) | Windows PowerShell 构建脚本 |
| [build.sh](mcp/mcp%20demo%E5%AE%9E%E8%B7%B5/build.sh) | Linux / macOS 构建脚本 |
| [codex-config.example.toml](mcp/mcp%20demo%E5%AE%9E%E8%B7%B5/codex-config.example.toml) | 本机 Codex 接入示例，使用前需修改 JAR 的绝对路径 |
| [verify.py](mcp/mcp%20demo%E5%AE%9E%E8%B7%B5/verify.py) | 使用 Python 标准库启动 Java 服务端，对协议行为执行黑盒检查 |
| [verify_sdk.py](mcp/mcp%20demo%E5%AE%9E%E8%B7%B5/verify_sdk.py) | 使用官方 Python MCP SDK 检查与 Java 服务端的互操作 |
| [docs/design.md](mcp/mcp%20demo%E5%AE%9E%E8%B7%B5/docs/design.md) | 教学范围、输入输出、文件职责与实现边界 |

## 四个源码文件分别做什么

| 文件 | 职责 |
| --- | --- |
| [MockSearch.java](mcp/mcp%20demo%E5%AE%9E%E8%B7%B5/src/demo/MockSearch.java) | 普通搜索业务函数：匹配内存中的固定语料，并返回标记为 `mock` 的结果 |
| [McpServer.java](mcp/mcp%20demo%E5%AE%9E%E8%B7%B5/src/demo/McpServer.java) | 从标准输入读取请求，处理初始化、`tools/list`、`tools/call`，再将结果写入标准输出 |
| [McpClientDemo.java](mcp/mcp%20demo%E5%AE%9E%E8%B7%B5/src/demo/McpClientDemo.java) | 启动服务端子进程，完成初始化、发现和调用，并打印实际消息 |
| [Json.java](mcp/mcp%20demo%E5%AE%9E%E8%B7%B5/src/demo/Json.java) | 提供 JSON 编解码，让本例无需外部依赖；它是配套工具，不属于 MCP 协议 |

## 推荐阅读路径

1. 先读[模块 README](mcp/mcp%20demo%E5%AE%9E%E8%B7%B5/README.md)，运行一次客户端，观察消息顺序。
2. 阅读[完整讲义](mcp/mcp%20demo%E5%AE%9E%E8%B7%B5/docs/tutorial.md)，区分宿主、客户端、服务端和模型的职责。
3. 从 `MockSearch.java` 的普通方法入手，再读 `McpServer.java`，看业务方法如何变成可发现、可调用的工具。
4. 阅读 `McpClientDemo.java`，对照[实际交互日志](mcp/mcp%20demo%E5%AE%9E%E8%B7%B5/verification/demo-client.stdout.txt)检查初始化、发现和调用过程。
5. 运行空结果、非法参数和模拟超时的例子，再对照[验证记录](mcp/mcp%20demo%E5%AE%9E%E8%B7%B5/verification/)理解两类错误。

## 从仓库根目录运行

在 Windows PowerShell 中，从仓库根目录进入模块，使用包内 JAR 运行：

```powershell
Set-Location ".\mcp\mcp demo实践"
java -version
java -cp .\dist\mock-google-mcp.jar demo.McpClientDemo "Java 虚拟线程" 2
```

客户端会自行启动服务端，无需另外打开一个终端启动服务端。

源码目标为 **Java 17+**。如需重新编译，在模块目录中使用完整 JDK 执行：

```powershell
.\build.ps1
java -cp .\dist\mock-google-mcp.jar demo.McpClientDemo "MCP" 3
```

更多运行参数、错误示例和 Codex 配置方法见[模块 README](mcp/mcp%20demo%E5%AE%9E%E8%B7%B5/README.md)。

## 实现范围与已有验证

本例锁定 MCP **2025-06-18** 的 `stdio` 与工具调用教学子集，不代表当前最新版本或完整协议实现。

搜索仅使用 6 条固定模拟语料，不请求真实 Google，也不调用 LLM。教学客户端通过固定代码选择 `google_search`；`tools/list` 读取的是已连接服务的工具清单，不承担网络服务注册与地址发现。

以下数字来自仓库已保存的历史验证记录：

| 项目 | 现有记录 | 可核对文件 |
| --- | --- | --- |
| 已记录的运行环境 | Linux，OpenJDK 21.0.13；未在 Windows 或 Java 17 运行时实测 | [模块验证范围](mcp/mcp%20demo%E5%AE%9E%E8%B7%B5/README.md#13-验证记录与适用范围) |
| 源码编译目标 | Java 17 语法与目标字节码 | [build.log](mcp/mcp%20demo%E5%AE%9E%E8%B7%B5/verification/build.log) |
| Python 标准库黑盒检查 | 32 / 32 通过 | [verification-report.json](mcp/mcp%20demo%E5%AE%9E%E8%B7%B5/verification/verification-report.json) |
| 官方 Python MCP SDK 互操作 | `mcp==1.29.0`，7 / 7 通过 | [sdk-report.json](mcp/mcp%20demo%E5%AE%9E%E8%B7%B5/verification/sdk-report.json) |
| 协议消息记录 | 真实子进程 stdin / stdout 请求与响应 | [wire-transcript.jsonl](mcp/mcp%20demo%E5%AE%9E%E8%B7%B5/verification/wire-transcript.jsonl) |

这些记录验证的是本教学子集，不等于完整 MCP 规范认证，也不等于用户本机 Codex 的接入验收。
