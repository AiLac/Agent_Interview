# 模拟 Google 查询 MCP：Java 教学项目

这是一个可以离线运行的 MCP 教学例子。搜索查询只匹配内存中的6条固定语料，所有结果均标为模拟。MCP协议消息和两个进程之间的通信是真实执行的。

## 你能学到什么

- Host、Client、Server和大模型分别做什么。
- `initialize`、`notifications/initialized`、`tools/list`、`tools/call`的具体顺序。
- 工具描述和JSON Schema如何让客户端知道服务端能做什么。
- 一次Java方法调用怎样包装成MCP请求和返回结果。
- JSON-RPC错误与工具执行错误的区别。
- 在Codex中连接本例时，需要配置哪个进程。

本例锁定MCP **2025-06-18** 的stdio和tools教学子集；该日期是版本标识，不代表当前最新标准。没有实现HTTP、分页、并发、取消、动态工具变化、resources、prompts、sampling。

## 1. 立即运行

包内提供编译好的`dist/mock-google-mcp.jar`。Java源码面向Java17+；本次实际执行环境为Linux上的OpenJDK21.0.13，未在Windows或Java17运行时实测。

在Windows PowerShell进入解压后的项目根目录，运行：

```powershell
java -version
java -cp .\dist\mock-google-mcp.jar demo.McpClientDemo "Java 虚拟线程" 2
```

客户端会自行启动服务端，并打印真实发送/收到的消息。无需提前另开一个终端运行服务端。

本客户端用固定代码选择`google_search`；`tools/list`用于读取已连接服务的工具清单，没有调用大模型。

可以观察到：

```text
C→S initialize
S→C protocolVersion=2025-06-18, capabilities.tools={}
C→S notifications/initialized
C→S tools/list
S→C tools=[google_search及其inputSchema]
C→S tools/call
S→C result.isError=false, structuredContent.mock=true
```

上面是方便阅读的摘要，不是原始协议消息。真实消息保存在`verification/demo-client.stdout.txt`和`verification/wire-transcript.jsonl`。

默认查询匹配3条模拟语料，limit=2返回前2条。`totalMatches`是模拟语料的匹配数，不是Google全网结果数量。

更多实验：

```powershell
java -cp .\dist\mock-google-mcp.jar demo.McpClientDemo "MCP" 3
java -cp .\dist\mock-google-mcp.jar demo.McpClientDemo "肯定没有这个关键词XYZ" 3
java -cp .\dist\mock-google-mcp.jar demo.McpClientDemo "Java" 0
java -cp .\dist\mock-google-mcp.jar demo.McpClientDemo "__timeout__" 3
```

后两条故意失败，客户端进程退出码为1：分别演示参数错误与模拟业务超时。`__timeout__`会立即返回错误，不会真的等待网络超时。

## 2. 从源码编译

需要完整JDK17+；无需Maven、Gradle或第三方依赖。

Windows PowerShell：

```powershell
.\build.ps1
java -cp .\dist\mock-google-mcp.jar demo.McpClientDemo "Java 虚拟线程" 2
```

也可直接执行相同的编译命令，无需运行脚本：

```powershell
javac --release 17 -encoding UTF-8 -d out src/demo/*.java
jar --create --file dist/mock-google-mcp.jar --main-class demo.McpServer -C out .
```

Linux/macOS（完整JDK17+）：

```bash
sh build.sh
java -cp dist/mock-google-mcp.jar demo.McpClientDemo 'Java 虚拟线程' 2
```

## 3. 按这个顺序读源码

| 文件 | 读什么 |
|---|---|
| `src/demo/MockSearch.java` | 普通业务函数：不认识MCP，只接收搜索参数并返回模拟数据 |
| `src/demo/McpServer.java` | 入口`run`、协议分发`dispatch`、工具分发`callTool` |
| `src/demo/McpClientDemo.java` | `run`中的初始化/发现/调用，以及`RpcSession.request`的收发 |
| `src/demo/Json.java` | 配套JSON编解码器，理解MCP时可以先跳过 |
| `docs/tutorial.md` | 完整讲义：原理、消息、代码、断点和练习 |

`Json.java`用于让下载包无外部依赖。它是教学辅助代码，不是MCP的一部分；实际项目可用成熟JSON库和官方MCP SDK。

## 4. 接入本机Codex

先确认JAR实际路径，例如`D:/mcp-demo/google-search-mcp-java/dist/mock-google-mcp.jar`。

把`codex-config.example.toml`中的示例路径改为实际绝对路径，再将对应配置合并到`~/.codex/config.toml`：

```toml
[mcp_servers.mock_google]
command = "java"
args = ["-jar", "D:/mcp-demo/google-search-mcp-java/dist/mock-google-mcp.jar"]
```

重新启动Codex后用`/mcp`检查服务，再要求模型：

```text
调用mock_google服务的google_search工具，query为Java 虚拟线程，limit为2。
结果属于模拟数据，请原样说明这一点。
```

这里由Codex承担Host与MCP Client的工作。不要把`McpClientDemo`配置成服务器：它会向控制台输出讲解文字，这些不是服务端协议消息。

本次没有修改你的Codex配置，也没有在你的Codex会话里实测加载。已验证范围见下一节。

## 5. 验证记录

本次实际执行结果：Python标准库黑盒检查32/32通过；官方Python MCP SDK 1.29.0互操作检查7/7通过。两者调用的都是包内同一个JAR，验证范围是本教学子集，不是完整规范认证或用户端Codex验收。

- `verification/build.log`：实际编译命令及输出。
- `verification/demo-client.stdout.txt`：Java教学客户端完整运行日志。
- `verification/demo-server.stderr.txt`：隔离后的服务端日志。
- `verification/verification-report.json`：独立Python标准库客户端的黑盒检查结果。
- `verification/sdk-report.json`：官方Python MCP SDK互操作结果。
- `verification/wire-transcript.jsonl`：黑盒验证真实请求/响应记录。

重新运行黑盒检查需要Python3.10+：

```powershell
python verify.py
```

重新运行可选SDK互操作检查还需要`mcp` Python包；交付环境使用的是`mcp==1.29.0`：

```powershell
python verify_sdk.py
```

## 官方参考

- [MCP架构](https://modelcontextprotocol.io/specification/2025-06-18/architecture)
- [生命周期](https://modelcontextprotocol.io/specification/2025-06-18/basic/lifecycle)
- [stdio传输](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports)
- [工具与错误](https://modelcontextprotocol.io/specification/2025-06-18/server/tools)
- [Java SDK](https://github.com/modelcontextprotocol/java-sdk)
- [Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [Codex MCP配置](https://developers.openai.com/codex/mcp)
