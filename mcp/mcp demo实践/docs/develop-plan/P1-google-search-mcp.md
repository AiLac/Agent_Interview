# Google Search MCP Teaching Demo Implementation Plan

**Goal:** 交付可运行的Java模拟搜索MCP及客户端，展示初始化、工具发现、调用和错误。

**Architecture:** 服务端通过stdio接收一行一条JSON-RPC消息，完成生命周期检查后分发工具请求。客户端启动服务端子进程，通过实际tools/list读取工具定义后调用；业务查询是确定性的本地假数据。

**Tech Stack:** Java 17+、Java标准库、Python标准库黑盒验证。

**Spec:** docs/design.md

## Global Constraints

- 明确锁定MCP 2025-06-18的单工具教学子集。
- 所有协议消息为UTF-8，每条消息一行；服务端stdout仅输出协议消息。
- 工具google_search(query, limit)，limit默认3、范围1至5，搜索结果明确mock。
- 不访问外网，不需要密钥或模型；不声明未实现的可选能力。

## Review Focus

- 通知没有响应，不能让客户端等待通知回复。
- 初始化完成前不能执行搜索；不同版本返回服务端支持的版本。
- 参数缺失/类型错误与业务__timeout__错误的层级必须可区分。
- 中文、引号、换行转义不破坏一行一消息。
- 客户端有超时，关闭stdin后服务端正确退出。

## Task 1: JSON与确定性模拟搜索

**Files:** src/demo/Json.java, src/demo/MockSearch.java

**Interfaces:** Json.parse(String): Object; Json.stringify(Object): String; MockSearch.search(String,int): Map<String,Object>。

- [x] 编写零依赖JSON辅助类，支持object/array/string/number/boolean/null，拒绝非法输入。
- [x] 编写标明模拟数据的固定语料，逐词包含匹配，保留输入query，limit限制返回数量。
- [x] 以独立Python json解析服务端消息，验证转义与数据类型。

## Task 2: MCP服务端与教学客户端

**Files:** src/demo/McpServer.java, src/demo/McpClientDemo.java

**Interfaces:** 主类demo.McpServer；客户端demo.McpClientDemo [query] [limit]。

- [x] 服务端实现initialize、notifications/initialized、ping、tools/list、tools/call及错误。
- [x] 客户端启动子进程，打印发送/收到的实际消息，发现后调用，检查id与版本，限制等待时间。
- [x] 运行客户端成功查询，保存可核对的交互记录。

## Task 3: 验证与交付

**Files:** verify.py, README.md, docs/tutorial.md, verification/*, build scripts。

- [x] 使用黑盒脚本覆盖Review Focus及正常/空结果/错误分支，保留实际结果。
- [x] 如果可用，使用官方MCP客户端完成一次互操作检查。
- [x] 编写Java类比、请求响应示例、Windows运行步骤、Codex接入配置与练习。
- [x] 检查README命令与源码一致，打包源码、JAR与验证记录，保存可下载文件。

## Self-review

范围为用户直接要求的教学示例，不修改已有项目、不接入真实搜索、不部署外部服务。实现与交付无需额外权限。测试用于验证协议对端可观察的行为，不为文件数量或实现细节写测试。

## Actual verification

Java客户端完整查询通过；独立黑盒32/32通过，官方Python MCP SDK 1.29.0互操作7/7通过。环境为Linux / Java21.0.13，编译为Java17目标字节码；Windows和Java17运行时未实测。
