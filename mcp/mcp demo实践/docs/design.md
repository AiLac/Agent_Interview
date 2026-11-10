# 模拟 Google 搜索 MCP：教学设计

用户目标：通过一个模拟 Google 搜索服务理解 MCP 原理、工具发现与代码。

本例选用用户熟悉的 Java，Java 17+、零外部依赖、UTF-8 stdio，明确锁定 MCP 2025-06-18 的单工具教学子集。搜索只查询程序内的固定示例数据，不访问 Google，也不调用模型；所有数据标明 mock。客户端以程序指定工具名，实际工具存在性和输入描述来自 tools/list，不把这个过程冒充模型自主选择。

输入：query 字符串、limit 整数（默认3，1至5）。输出：query、mock=true、totalMatches、results（title/url/snippet）。普通搜索为空是成功；query=__timeout__ 注入业务错误。不存在的方法/工具、非法参数与业务错误分别展示。

文件职责：Json.java 只负责 JSON 编解码，MockSearch.java 负责本地数据查询，McpServer.java 负责会话状态、方法分发和消息封装，McpClientDemo.java 负责启动子进程、初始化、工具发现与调用。客户端打印真实线上消息（此处线上指进程间管道），服务端日志只写 stderr。

验证：用独立 Python 标准库客户端做黑盒检查，核对真实进程的握手、发现、Schema、调用、空结果、错误、UTF-8、版本选择、stdout纯净和EOF退出。若环境已有官方 Python MCP SDK，额外验证一次互操作。源码和Linux验证记录一起打包，Windows提供明确编译运行命令，不把Linux验证写成Windows实测。

边界：不实现HTTP、鉴权、并发调用、取消、分页、动态工具变化、resources/prompts/sampling，也不宣称为通用SDK。JSON辅助类属于教学配套；实际项目优先采用官方SDK及成熟JSON库。
